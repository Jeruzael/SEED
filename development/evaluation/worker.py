"""Bounded spawned lifecycle. Foundation has no cycle/experiment dispatcher."""
import json
import multiprocessing
import os
import resource
import sys
import threading
import time
from .bootstrap import validate_launch, install_worker_adapters
from .contracts import ContractError, RunResult, fields, strict_json, MESSAGE_BYTES
from .paths import worker_environment
from .registry import ACTIONS
from .channel import LearnerClient, validate_request

REAL_CLOCK = time.monotonic
_LEASE = threading.Lock()
_ENV_LOCK = threading.Lock()


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
        from .state import OwnedState, CompletedLearner
        from seed.migrations import schema_version
        if launch.launch_mode=='FRESH':
            state=OwnedState.fresh(launch.learner,strict_json(launch.settings))
            state.close()
            from seed.organism import SeedOrganism
            core=SeedOrganism(launch.learner.home)
            core.decisions.rng=session.learner_rng
        else:
            core=CompletedLearner(launch.fixture,strict_json(launch.settings),session)
        client=LearnerClient(pipe,session.clock)
        if _memory_bytes()>512*1024**2:
            raise WorkerError()
        pipe.send_bytes(_encode({'status':'ready','schema':schema_version(core.memory.db),
                                 'memory_accounting':'best_effort','rss_bytes':_memory_bytes()}))
        while True:
            message=strict_json(pipe.recv_bytes(MESSAGE_BYTES))
            if message=={'operation':'stop'}:
                break
            try:
                message=validate_request(message)
                if _memory_bytes()>512*1024**2:
                    raise WorkerError()
                if message['operation']=='action_catalog':
                    value={'actions':list(client.action_catalog())}
                elif message['operation']=='observation':
                    key=message['key']
                    value=client.observation(key[0],key[2],key[1])
                else:
                    if client._pending != message['key'][:3]:
                        raise WorkerError()
                    value=client.apply(message['action'],message['key'][2])
                pipe.send_bytes(_encode({'kind':'result','value':value}))
            except (ValueError,RuntimeError):
                pipe.send_bytes(_encode({'kind':'error','code':'INVALID_CONTRACT'}))
                break
    except BaseException:
        try: pipe.send_bytes(b'{"kind":"error","code":"WORKER_FAILED"}')
        except (OSError,EOFError): pass
    finally:
        if core is not None:
            try: core.close()
            except BaseException: pass
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
            message=validate_request(message)
            self.pipe.send_bytes(_encode(message))
            sent=True
            response=self._receive()
            while response.get('kind')=='request':
                fields(response,('kind','request'))
                try:
                    incoming=validate_request(response['request'])
                    if incoming!=message:
                        raise WorkerError()
                    if self._channel is None:
                        if incoming!={'operation':'action_catalog'}:
                            raise WorkerError()
                        value={'actions':list(ACTIONS)}
                    else:
                        value=self._channel.dispatch(incoming)
                    self.pipe.send_bytes(_encode({'kind':'response','value':value}))
                except BaseException:
                    self.pipe.send_bytes(b'{"kind":"error","code":"INVALID_CONTRACT"}')
                response=self._receive()
            fields(response,('kind','value'))
            if response['kind']!='result':
                raise WorkerError()
            return response['value']
        except (OSError,EOFError,ValueError,RuntimeError):
            if sent:
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
                finally:
                    self.pipe.close()
                    _LEASE.release()
        return RunResult('INCOMPLETE',reason)
