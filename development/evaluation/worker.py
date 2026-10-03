"""Bounded spawned lifecycle and closed protocol dispatch, without science execution."""
import json
import multiprocessing
import os
import resource
import sys
import threading
import time
from .bootstrap import validate_launch, install_worker_adapters
from .contracts import ContractError, RunResult, fields, strict_json, validate_event_key, MESSAGE_BYTES
from .paths import worker_environment
from .registry import ACTIONS
from .channel import LearnerClient, validate_request

REAL_CLOCK = time.monotonic
_LEASE = threading.Lock()
_ENV_LOCK = threading.Lock()


def validate_command(message):
    value=strict_json(_encode(message))
    if value.get('operation')=='retry':
        fields(value,('operation','interval'))
        if type(value['interval']) is not int or not 1<=value['interval']<=3600:raise WorkerError()
        return value
    if value.get('operation')=='freeze':
        fields(value,('operation',))
        return value
    if value.get('operation') in ('cycle','probe','maintenance'):
        fields(value,('operation','key'))
        key=validate_event_key(value['key'])
        phases=('probe',) if value['operation']=='probe' else ('training','measured')
        stage='update' if value['operation']=='maintenance' else 'pre'
        if key[3]!=stage or key[0] not in phases:
            raise WorkerError()
        return value
    return validate_request(value)


class WorkerError(ContractError):
    pass


def _encode(value):
    try:
        raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
        strict_json(raw)
        return raw
    except (ValueError,TypeError,UnicodeError):
        raise WorkerError() from None


def _memory_bytes():
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform=='darwin' else rss*1024)


def _worker_entry(pipe, launch):
    core=None
    try:
        session=install_worker_adapters(launch)
        from .adapters import construct_core, CaptureSession, capture_updates, producer_payload
        from seed.migrations import schema_version
        client=LearnerClient(pipe,session.clock)
        if launch.protocol=='FROZEN_SELECTION_ASSAY':
            if launch.launch_mode!='COMPLETED_OWNED_FIXTURE':raise WorkerError()
            from .frozen import FrozenWorker
            core=FrozenWorker(launch.fixture,session)
            capture=None
        else:
            core=construct_core(launch,session,client)
            capture=CaptureSession(client,session.clock)
            capture.attach(core)
        if _memory_bytes()>512*1024**2:
            raise WorkerError()
        training_completed=0
        last_cycle=None
        pipe.send_bytes(_encode({'status':'ready','schema':schema_version(core.memory.db),
                                 'memory_accounting':'best_effort','rss_bytes':_memory_bytes()}))
        while True:
            message=strict_json(pipe.recv_bytes(MESSAGE_BYTES))
            if message=={'operation':'stop'}:
                break
            try:
                message=validate_command(message)
                if _memory_bytes()>512*1024**2:
                    raise WorkerError()
                if message['operation']=='retry':
                    if last_cycle is None or last_cycle['status']!='skipped':raise WorkerError()
                    session.clock.retry(message['interval'])
                    last_cycle=None
                    value={'status':'retry_scheduled'}
                elif message['operation']=='maintenance':
                    if capture is None or not capture.acked or message['key'][:3]!=list(capture.key[:3]):raise WorkerError()
                    session.clock.stage(capture.key[0],capture.key[2],4)
                    run=core.consolidate(state=core.memory.get_meta('last_state',{}),provenance='owner_requested')
                    stored=core.memory.db.execute('SELECT * FROM consolidation_runs WHERE id=?',(run['id'],)).fetchone()
                    if stored is None:raise WorkerError()
                    value=dict(run_id=run['id'],status=run['status'],stored=producer_payload(stored))
                elif message['operation']=='freeze':
                    if launch.protocol!='PREQUENTIAL' or capture.failed or training_completed!=launch.training_count:
                        raise WorkerError()
                    from .state import OwnedState
                    from .frozen import freeze_state
                    owned=OwnedState(launch.learner,core.memory,core.memory.db.monitor)
                    fixture=freeze_state(owned)
                    value=dict(inode=list(fixture.inode),byte_length=fixture.byte_length,sha256=fixture.sha256)
                elif message['operation']=='probe':
                    if launch.protocol!='FROZEN_SELECTION_ASSAY':raise WorkerError()
                    key=message['key']
                    observation=client.observation(key[0],key[2],key[1])
                    value=strict_json(core.probe(observation,key,client).body)
                elif message['operation']=='cycle':
                    if launch.protocol!='PREQUENTIAL':raise WorkerError()
                    capture.begin(message['key'])
                    try:
                        result=core.cycle()
                        value=dict(status=result.status,reason=result.reason,delay_seconds=result.delay_seconds,
                                   acked=capture.acked,capture={k:v for k,v in capture.record.items() if k!='history_rows'})
                        if result.status=='skipped':client.discard_skipped(message['key'])
                        if capture.acked:
                            value['updates']=capture_updates(core,message['key'])
                            calls=capture.record['producer_calls']
                            if calls.get('b7',{}).get('result')=='failed' or any(
                                    value['updates'][name]['status']!='confirmed' for name in ('q','b1','b4','b5','b7','b8')):
                                value.update(status='incomplete',reason='PRODUCER_UNCONFIRMED')
                                capture.failed=True
                            value['capture']={k:v for k,v in capture.record.items() if k not in ('history_rows','updates')}
                        if result.status=='completed' and message['key'][0]=='training':training_completed+=1
                    except Exception:
                        capture.failed=True
                        value=dict(status='incomplete' if capture.acked else 'failed',reason='CYCLE_INTERRUPTED',
                                   delay_seconds=None,acked=capture.acked,
                                   capture={k:v for k,v in capture.record.items() if k!='history_rows'})
                        try:value['updates']=capture_updates(core,message['key'])
                        except BaseException:value['updates']=capture.record.get('updates',{})
                        value['capture']={k:v for k,v in capture.record.items() if k not in ('history_rows','updates')}
                    last_cycle=value
                elif message['operation']=='action_catalog':
                    value={'actions':list(client.action_catalog())}
                elif message['operation']=='observation':
                    key=message['key']
                    value=client.observation(key[0],key[2],key[1])
                else:
                    if client._pending != message['key'][:3]:
                        raise WorkerError()
                    value=client.apply(message['action'],message['key'][2])
                pipe.send_bytes(_encode({'kind':'result','value':value}))
                if message['operation']=='freeze':break
                if capture is not None and capture.failed:break
            except (ValueError,RuntimeError):
                pipe.send_bytes(_encode({'kind':'error','code':'INVALID_CONTRACT'}))
                break
    except BaseException:
        try: pipe.send_bytes(b'{"kind":"error","code":"WORKER_FAILED"}')
        except (OSError,EOFError): pass
    finally:
        cleanup='closed'
        if core is not None:
            try: core.close()
            except BaseException: cleanup='failed'
        try: pipe.send_bytes(_encode({'kind':'cleanup','status':cleanup}))
        except (OSError,EOFError): pass
        pipe.close()


class WorkerHandle:
    def __init__(self, launch, process, pipe, started, run_seconds, cleanup_seconds, channel):
        self.launch,self.process,self.pipe=launch,process,pipe
        self.started,self.run_seconds,self.cleanup_seconds=started,run_seconds,cleanup_seconds
        self.ready=None
        self._stopped=False
        self._request_lock=threading.Lock()
        self._stop_lock=threading.Lock()
        self._deadline_cancel=threading.Event()
        self._channel=channel
        self.last_channel_failure=None
        self.checkpoint_bytes=0
        self.cleanup_status='unconfirmed'

    @classmethod
    def start(cls, launch, *, run_seconds=120, cleanup_seconds=5, channel=None):
        validate_launch(launch)
        for value,maximum in ((run_seconds,120),(cleanup_seconds,5)):
            if type(value) not in (int,float) or not 0<value<=maximum:
                raise WorkerError()
        if not _LEASE.acquire(blocking=False):
            raise WorkerError()
        pipe=child=process=None
        try:
            ctx=multiprocessing.get_context('spawn')
            pipe,child=ctx.Pipe()
            process=ctx.Process(target=_worker_entry,args=(child,launch),name='seed-evaluation-worker')
            started=REAL_CLOCK()
            # Sanitize before interpreter startup, then restore parent environment.
            with _ENV_LOCK:
                original=dict(os.environ)
                try:
                    os.environ.clear(); os.environ.update(worker_environment())
                    process.start()
                finally:
                    os.environ.clear(); os.environ.update(original)
            child.close()
            handle=cls(launch,process,pipe,started,run_seconds,cleanup_seconds,channel)
            ready=handle._receive()
            fields(ready,('status','schema','memory_accounting','rss_bytes'))
            if ready['status']!='ready' or ready['schema']!=7 or ready['rss_bytes']>512*1024**2:
                raise WorkerError()
            handle.ready=ready
            def deadline():
                remaining=max(0,run_seconds-(REAL_CLOCK()-started))
                if not handle._deadline_cancel.wait(remaining):
                    handle.stop('LIMIT_REACHED')
            threading.Thread(target=deadline,name='evaluation-deadline',daemon=True).start()
            return handle
        except BaseException:
            if process is not None and process.pid:
                process.terminate(); process.join(5)
                if process.is_alive(): process.kill(); process.join(1)
            if pipe is not None: pipe.close()
            if child is not None: child.close()
            _LEASE.release()
            raise WorkerError() from None

    def _receive(self):
        remaining=self.run_seconds-(REAL_CLOCK()-self.started)
        if remaining<=0 or not self.pipe.poll(remaining):
            raise WorkerError()
        try:
            return strict_json(self.pipe.recv_bytes(MESSAGE_BYTES))
        except (OSError,EOFError,ValueError):
            raise WorkerError() from None

    def request(self, message):
        if self._stopped or not self.process.is_alive() or REAL_CLOCK()-self.started>=self.run_seconds:
            raise WorkerError()
        if not self._request_lock.acquire(blocking=False):
            raise WorkerError()
        sent=False
        try:
            message=validate_command(message)
            if message['operation']=='cycle':
                self.checkpoint_bytes=0
                self.last_channel_failure=None
            self.pipe.send_bytes(_encode(message))
            sent=True
            response=self._receive()
            while response.get('kind')=='request':
                fields(response,('kind','request'))
                try:
                    incoming=validate_request(response['request'])
                    if message['operation'] in ('cycle','probe'):
                        if incoming['operation'] in ('observation','apply'):
                            if incoming['key'][:3]!=message['key'][:3]:raise WorkerError()
                        elif incoming['operation']=='checkpoint':
                            if message['operation']!='cycle':raise WorkerError()
                            evidence=incoming['evidence']
                            if [evidence['phase'],evidence['subcase'],evidence['transition_ordinal']]!=message['key'][:3]:raise WorkerError()
                        else:raise WorkerError()
                    elif incoming!=message:
                        raise WorkerError()
                    if self._channel is None:
                        if incoming!={'operation':'action_catalog'}:
                            raise WorkerError()
                        value={'actions':list(ACTIONS)}
                    else:
                        previous_size=self._channel._journal.path.stat().st_size if incoming['operation']=='checkpoint' and self._channel._journal else None
                        value=self._channel.dispatch(incoming)
                        if previous_size is not None:self.checkpoint_bytes=self._channel._journal.path.stat().st_size-previous_size
                    self.pipe.send_bytes(_encode({'kind':'response','value':value}))
                except BaseException as error:
                    self.last_channel_failure=RunResult(getattr(error,'status','FAILED'),getattr(error,'reason','INVALID_CONTRACT'))
                    self.pipe.send_bytes(b'{"kind":"error","code":"INVALID_CONTRACT"}')
                response=self._receive()
            fields(response,('kind','value'))
            if response['kind']!='result':
                raise WorkerError()
            if message['operation']=='cycle' and response['value']['status']=='skipped' and self._channel is not None:
                self._channel.discard_skipped(message['key'])
            return response['value']
        except (OSError,EOFError,ValueError,RuntimeError):
            if sent:
                if self.last_channel_failure is None and self.checkpoint_bytes:
                    self.last_channel_failure=RunResult('INCOMPLETE','WORKER_DIED_AFTER_ACK')
                from .db_adapter import RunBudget
                try: RunBudget(self.launch.learner.home.parent).stop()
                finally: self.stop('WORKER_DIED')
            raise WorkerError() from None
        finally:
            self._request_lock.release()

    def stop(self, reason='OWNER_CANCELLED'):
        if reason not in ('OWNER_CANCELLED','LIMIT_REACHED','WORKER_DIED'):
            raise WorkerError()
        with self._stop_lock:
            if not self._stopped:
                self._stopped=True
                self._deadline_cancel.set()
                try:
                    if self.process.is_alive():
                        try: self.pipe.send_bytes(b'{"operation":"stop"}')
                        except (OSError,EOFError): pass
                        self.process.join(self.cleanup_seconds)
                        if self.process.is_alive(): self.process.terminate(); self.process.join(1)
                        if self.process.is_alive(): self.process.kill(); self.process.join(1)
                    # A dead process alone does not prove successful producer
                    # cleanup. Require the worker's separate closed status.
                    if self.pipe.poll(0):
                        try:
                            receipt=strict_json(self.pipe.recv_bytes(MESSAGE_BYTES))
                            if receipt in ({'kind':'cleanup','status':'closed'},{'kind':'cleanup','status':'failed'}):
                                self.cleanup_status=receipt['status']
                        except (OSError,EOFError,ValueError):pass
                finally:
                    self.pipe.close()
                    _LEASE.release()
        return RunResult('INCOMPLETE',reason)

    def freeze(self):
        value=self.request({'operation':'freeze'})
        self.stop()
        fields(value,('inode','byte_length','sha256'))
        from .state import CompletedFixture
        fixture=CompletedFixture(self.launch.learner,tuple(value['inode']),value['byte_length'],value['sha256'])
        return fixture.validate()
