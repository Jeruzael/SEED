"""Bounded online scheduling. No registered science or aggregate execution."""
from .contracts import ContractError, CompletedEvidence, RunRequest, RunResult
from .channel import wire_bytes


class PrequentialDriver:
    def __init__(self, *, training=0, measured=1, maintenance=False):
        if (type(training) is not int or type(measured) is not int or not 0<=training<=512
                or not 0<=measured<=1024 or not 1<=training+measured<=1024 or type(maintenance) is not bool):
            raise ContractError()
        self.training,self.measured,self.declared_maintenance=training,measured,maintenance
        self.events,self.skipped,self.maintenance=[],[],[]
        self.failures=[]
        self.failure_capture=None
        self._used=False

    def capture_completed(self, value, key, worker):
        # The durable journal already owns raw selected prediction/outcome. Keep
        # this joined update record compact instead of duplicating that evidence.
        body=wire_bytes(dict(acked=value['acked'],execution=value['status'],updates=value.get('updates',{}),
                            decision_id=value.get('capture',{}).get('selection',{}).get('decision_id')))
        if len(body)+getattr(worker,'checkpoint_bytes',0)>65536:
            raise OSError('POST_ACK_RECORD_LIMIT')
        self.events.append(CompletedEvidence(tuple(key[:3])+('update',),body))

    def capture_failure(self, value, key, attempt, result, worker):
        if self.failures:return
        # One bounded terminal detail, separately joined by a <=512-byte
        # attempt summary. Keep the real worker response, including prior
        # effects and unconfirmed updates, even when no ACK was given.
        self.failure_capture=wire_bytes(value) if value is not None else None
        summary=wire_bytes(dict(key=key,attempt=attempt,execution=result.status,reason=result.reason,
            acked=value.get('acked') if value is not None else None,
            checkpoint_bytes=getattr(worker,'checkpoint_bytes',0),
            capture_status='captured' if value is not None else 'unavailable_worker_response'))
        if len(summary)>512:raise ContractError()
        self.failures.append(summary)

    def run(self, request: RunRequest, worker):
        if self._used or type(request) is not RunRequest or request.count!=1:
            raise ContractError()
        self._used=True
        attempts=consecutive=completed=0
        key=None
        value=None
        try:
            for phase,count in (('training',self.training),('measured',self.measured)):
                ordinal=1
                while ordinal<=count:
                    if attempts>=2048 or consecutive>=8:
                        return RunResult('INCOMPLETE','LIMIT_REACHED')
                    attempts+=1
                    key=[phase,'default',ordinal,'pre']
                    value=None
                    value=worker.request({'operation':'cycle','key':key})
                    if value['status']=='skipped':
                        if value['acked'] or value['reason']!='stale_decision':raise ContractError()
                        raw=wire_bytes(dict(key=key,attempt=attempts,status='skipped',reason=value['reason'],
                                            retry_delay_seconds=value['delay_seconds']))
                        if len(raw)>512:raise ContractError()
                        self.skipped.append(raw)
                        consecutive+=1
                        if consecutive<8 and attempts<2048:
                            worker.request({'operation':'retry','interval':value['delay_seconds']})
                        continue
                    consecutive=0
                    if value.get('acked'):
                        self.capture_completed(value,key,worker)
                    if value['status']!='completed':
                        failure=getattr(worker,'last_channel_failure',None)
                        result=failure or RunResult('INCOMPLETE' if value.get('acked') else 'FAILED','CYCLE_INTERRUPTED')
                        self.capture_failure(value,key,attempts,result,worker)
                        return result
                    if not value.get('acked'):raise ContractError()
                    completed+=1
                    if self.declared_maintenance and completed%8==0:
                        maintenance=worker.request({'operation':'maintenance','key':key[:3]+['update']})
                        self.maintenance.append(dict(after_completed=completed,provenance='owner_requested',
                            annotation='declared_maintenance',**maintenance))
                        if maintenance.get('execution')=='incomplete' or maintenance['status'] in ('failed','unconfirmed'):
                            result=RunResult('INCOMPLETE','MAINTENANCE_INTERRUPTED')
                            self.capture_failure(value,key,attempts,result,worker)
                            return result
                    ordinal+=1
            return RunResult('COMPLETED',None)
        except ContractError:
            result=getattr(worker,'last_channel_failure',None) or RunResult('FAILED','INVALID_CONTRACT')
            self.capture_failure(value,key,attempts,result,worker)
            return result
        except (OSError,RuntimeError,KeyError,TypeError):
            result=RunResult('INCOMPLETE','CAPTURE_INTERRUPTED')
            self.capture_failure(value,key,attempts,result,worker)
            return result
        finally:
            # No implicit resume/automatic retry after any ambiguous completed
            # mutation; preserve journal and learner files for technical audit.
            try:
                worker.stop()
                if getattr(worker,'cleanup_status','closed')!='closed':
                    result=RunResult('INCOMPLETE','CLEANUP_UNCONFIRMED')
                    self.capture_failure(value,key,attempts,result,worker)
                    return result
            except (OSError,RuntimeError,ValueError):
                result=RunResult('INCOMPLETE','CLEANUP_FAILED')
                self.capture_failure(value,key,attempts,result,worker)
                return result
