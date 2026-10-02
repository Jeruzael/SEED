import hashlib
import json
import multiprocessing
import sys
import time
import uuid
import pytest


IDENTITY = dict(experiment_id='technical-fixture', experiment_version=1, family='A', seed=0,
                protocol='PREQUENTIAL', variant='seed', role='learner')


def test_keyed_scenario_draws(foundation_module):
    d = foundation_module('determinism')
    c = foundation_module('canonical')
    s = d.Streams.for_identity(IDENTITY)
    key = ['technical-fixture', 1, 'A', 0, 'measured', 3, 'load']
    raw = hashlib.sha256(b'SEED_B10_SCENARIO_RNG_V1\0' + c.canonical_bytes(key)).digest()
    expected = (int.from_bytes(raw[:7], 'big') >> 3) / 2**53
    assert s.scenario('measured', 3, 'load') == expected
    assert d.Streams.for_identity({**IDENTITY,'variant':'random-eligible'}).scenario('measured',3,'load') == expected
    assert 0 <= expected < 1


def test_named_stream_independence(foundation_module):
    d = foundation_module('determinism')
    a, b = d.Streams.for_identity(IDENTITY), d.Streams.for_identity(IDENTITY)
    for _ in range(100):
        a.baseline.random()
        a.legacy.random()
    assert [a.learner.random() for _ in range(5)] == [b.learner.random() for _ in range(5)]
    assert a.scenario('training',1,'load') == b.scenario('training',1,'load')


def test_clock_schedule(foundation_module):
    d = foundation_module('determinism')
    clock = d.Clock(training_count=2)
    clock.stage('training',1,0)
    assert clock.wall() == 1800000010 and clock.monotonic() == 10
    clock.stage('measured',1,2)
    assert clock.wall() == 1800000032
    assert clock.wall() == clock.wall()
    clock.stale()
    assert clock.wall() == 1800000333
    retry = d.Clock(training_count=0)
    retry.stage('measured',1,0)
    retry.retry(8)
    last = retry.monotonic()
    retry.stage('measured',1,1)
    assert retry.monotonic() > last
    retry.stage('measured',2,0)
    assert retry.monotonic() >= last
    with pytest.raises(ValueError):
        retry.stage('measured',1,0)


def test_uuid_preinitialization_identity(foundation_module):
    d = foundation_module('determinism')
    a, b = d.UUIDStream('a'*64), d.UUIDStream('a'*64)
    assert a.next_hex('session') == b.next_hex('session')
    assert len(a.next_hex('session')) == 32
    assert d.UUIDStream('a'*64).next_hex('session') != d.UUIDStream('a'*64).next_hex('decision')
    with pytest.raises(ValueError):
        d.UUIDStream('run-storage-id')


def _bootstrap_probe(pipe, capability):
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        session = install_worker_adapters(WorkerLaunch(capability, b'{}', 3, 'a'*64))
        import seed.self_model as sm
        import seed.organism as o
        import seed.body as body
        import socket
        session.clock.stage('measured',1,2)
        assert sm.SelfModel.__init__.__defaults__[-1] == time.time or sm.SelfModel.__init__.__kwdefaults__['clock'] == time.time
        assert time.time() == 1800000012 and time.monotonic() == 12
        assert uuid.uuid4().hex != uuid.uuid4().hex
        for call in (lambda: body.Body(None), lambda: socket.create_connection(('example.invalid',80)), lambda: time.sleep(.01)):
            try: call()
            except RuntimeError: pass
            else: raise AssertionError('live fallback')
        try: o.Body(None).perceive()
        except RuntimeError: pass
        else: raise AssertionError('host fallback')
        pipe.send({'ok':True})
    except BaseException as e:
        pipe.send({'ok':False,'error':type(e).__name__})
    finally: pipe.close()


def test_bound_clock_and_host_poison(foundation_module, tmp_path):
    b = foundation_module('bootstrap')
    before = time.time()
    original = time.time
    parent, child = multiprocessing.get_context('spawn').Pipe()
    capability = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve()).assign_learner('probe',0)
    worker = multiprocessing.get_context('spawn').Process(target=_bootstrap_probe,args=(child,capability),name='seed-evaluation-worker')
    worker.start()
    child.close()
    assert parent.poll(10)
    result = parent.recv()
    worker.join(5)
    assert result == {'ok':True}
    assert time.time is original and time.time() >= before and len(uuid.uuid4().hex) == 32
    with pytest.raises(ValueError):
        b.install_worker_adapters(None)
