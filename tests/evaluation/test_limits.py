import pytest


def test_root_and_run_reservations(foundation_module):
    l = foundation_module('limits')
    c = foundation_module('contracts')
    b = l.Budget(retained_bytes=0, retained_runs=59)
    reservation = b.reserve(c.RunRequest('one'))
    with pytest.raises(ValueError):
        b.reserve(c.RunRequest('two'))
    reservation.release()
    assert b.reserve(c.RunRequest('two'))
    for retained_bytes, retained_runs, request in [
        (16*1024**3, 0, c.RunRequest('one')), (0, 60, c.RunRequest('one')),
        (0, 0, c.RunRequest('one', 33)), (0, 0, c.RunRequest('one', 1, 448*1024**2+1))]:
        with pytest.raises(ValueError):
            l.Budget(retained_bytes=retained_bytes, retained_runs=retained_runs).reserve(request)
    b = l.Budget(retained_bytes=0, retained_runs=0)
    assert b.reserve(c.RunRequest('suite', 32))
    with pytest.raises(ValueError):
        b.reserve(c.RunRequest('suite', 1))


def test_retained_root_accounting(foundation_module, tmp_path):
    p = foundation_module('paths')
    root = p.EvaluationRoot.create(tmp_path.resolve())
    root.assign_learner('run-0', 0)
    fd = root.open('plan', 'small', 'create')
    import os
    os.write(fd, b'x' * 123)
    os.close(fd)
    usage = root.usage()
    assert usage.bytes >= 123 and usage.runs == 1
