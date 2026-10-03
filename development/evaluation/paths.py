"""Descriptor-relative owned storage, with no installed-home fallback."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
from .contracts import ContractError
from .limits import Usage, Budget
from .specs import CAPS, identifier


def worker_environment():
    # Fresh Python workers need no inherited user configuration or credentials.
    return {'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C', 'TZ': 'UTC'}


def _checked(st, *, directory=False):
    if st.st_uid != os.geteuid() or not (stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode)):
        raise ContractError()
    if not directory and st.st_nlink != 1:
        raise ContractError()


def _directory(path):
    # Resolve nothing silently: every existing path component must be a real directory.
    path = Path(path)
    if not path.is_absolute():
        raise ContractError()
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        _checked(os.fstat(fd), directory=True)
        return fd
    except (OSError, ValueError):
        os.close(fd)
        raise ContractError() from None


def _mkdir(parent, name):
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent)
    except FileExistsError:
        pass
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        _checked(os.fstat(fd), directory=True)
        return fd
    except OSError:
        raise ContractError() from None


def _identity(st):
    return st.st_dev, st.st_ino


def _open_file(directory, name, mode):
    flags = os.O_NOFOLLOW | os.O_NONBLOCK
    if mode == 'read':
        flags |= os.O_RDONLY
    elif mode == 'create':
        flags |= os.O_WRONLY | os.O_CREAT | os.O_EXCL
    else:
        raise ContractError()
    try:
        fd = os.open(name, flags, 0o600, dir_fd=directory)
        try:
            st = os.fstat(fd)
            _checked(st)
            if _identity(st) != _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)):
                raise ContractError()
            return fd
        except BaseException:
            os.close(fd)
            raise
    except OSError:
        raise ContractError() from None


@dataclass(frozen=True)
class LearnerCapability:
    home: Path
    token: str
    inode: tuple[int, int]
    kind: str = 'learner'
    root: object = None
    run_inode: tuple[int, int] = ()

    def validate(self):
        if self.kind != 'learner' or type(self.token) is not str or not re.fullmatch('[0-9a-f]{64}', self.token):
            raise ContractError()
        if type(self.root) is not EvaluationRoot or self.home.parent.parent != self.root.path/'work' or self.home.name not in ('learner','clone'):
            raise ContractError()
        identifier(self.home.parent.name)
        self.root.admit_control(0)
        runfd = _directory(self.home.parent)
        try:
            if _identity(os.fstat(runfd)) != self.run_inode:
                raise ContractError()
        finally:
            os.close(runfd)
        fd = _directory(self.home)
        try:
            if _identity(os.fstat(fd)) != self.inode:
                raise ContractError()
            marker = _open_file(fd, '.ownership', 'read')
            with os.fdopen(marker, 'rb') as f:
                if f.read(65) != self.token.encode('ascii'):
                    raise ContractError()
        finally:
            os.close(fd)
        return self

    def open(self, kind, identity, mode):
        self.validate()
        names = {('state', 'db'): 'memory.sqlite3', ('snapshot', 'checkpoint'): 'checkpoint.sqlite3', ('lease','writer'): '.writer-lease', ('lease','checkpoint'): '.checkpoint-lease'}
        if (kind, identity) not in names:
            raise ContractError()
        fd = _directory(self.home)
        try:
            return _open_file(fd, names[(kind, identity)], mode)
        finally:
            os.close(fd)

    def sync(self):
        self.validate()
        fd = _directory(self.home)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class EvaluationRoot:
    def __init__(self, path, inode, plan_inode):
        self.path, self._inode, self._plan_inode = path, inode, plan_inode
        self.plan_directory = path / 'evaluation' / 'plans'
        self.budget=Budget(retained_bytes=0,retained_runs=0,usage=self.usage)

    @classmethod
    def create(cls, checkout):
        fd = _directory(checkout)
        try:
            try:
                os.mkdir('.seed-evaluation', mode=0o700, dir_fd=fd)
                created = True
            except FileExistsError:
                created = False
            root = _mkdir(fd, '.seed-evaluation')
            try:
                # An existing root is accepted only with an ownership marker.
                if created:
                    marker = _open_file(root, '.ownership', 'create')
                else:
                    marker = _open_file(root, '.ownership', 'read')
                    with os.fdopen(marker, 'rb') as f:
                        if f.read(65) != b'SEED_B10_OWNED_ROOT_V1':
                            raise ContractError()
                if created:
                    with os.fdopen(marker, 'wb') as f:
                        f.write(b'SEED_B10_OWNED_ROOT_V1')
                        f.flush()
                        os.fsync(f.fileno())
                evaluation = _mkdir(root, 'evaluation')
                plans = _mkdir(evaluation, 'plans')
                work = _mkdir(root, 'work')
                for name in ('runs', 'partials', 'receipts'):
                    child = _mkdir(evaluation, name)
                    os.close(child)
                result = cls(Path(checkout)/'.seed-evaluation', _identity(os.fstat(root)), _identity(os.fstat(plans)))
                for child in (plans, evaluation, work):
                    os.fsync(child)
                    os.close(child)
                os.fsync(root)
                return result
            finally:
                os.close(root)
        finally:
            os.close(fd)

    def _validate(self):
        root = _directory(self.path)
        if _identity(os.fstat(root)) != self._inode:
            os.close(root)
            raise ContractError()
        return root

    def admit_control(self, bytes):
        self.budget.require_capacity(bytes=bytes)

    def open(self, kind, identity, mode):
        if mode=='create': self.admit_control(0)
        if kind not in ('plan', 'freeze') or type(identity) is not str or not re.fullmatch('[a-z0-9][a-z0-9-]{0,127}', identity):
            raise ContractError()
        root = self._validate()
        os.close(root)
        fd = _directory(self.plan_directory)
        try:
            if _identity(os.fstat(fd)) != self._plan_inode:
                raise ContractError()
            return _open_file(fd, identity + '.' + kind, mode)
        finally:
            os.close(fd)

    def sync(self):
        self.admit_control(0)
        root = self._validate()
        os.close(root)
        fd = _directory(self.plan_directory)
        try:
            if _identity(os.fstat(fd)) != self._plan_inode:
                raise ContractError()
            os.fsync(fd)
        finally:
            os.close(fd)

    def assign_learner(self, run, slot):
        identifier(run)
        if type(slot) is not int or slot not in (0, 1):
            raise ContractError()
        usage = self.usage()
        reserved=next((r for key,r in self.budget._reservations.items() if key==run or run in r._active),None)
        if reserved is not None and run not in reserved._active:
            reserved.activate(run)
        # Ownership marker bytes consume an active run's reservation, or must
        # be newly admitted before any directory/marker is created.
        if reserved is not None and dict(usage.run_bytes).get(run,0)+64>reserved.request.reservation_bytes:
            raise ContractError()
        self.budget.require_capacity(bytes=0 if reserved is not None else 64,
                                      runs=0 if run in usage.run_ids or reserved is not None else 1)
        root = self._validate()
        try:
            work = _mkdir(root, 'work')
            runfd = _mkdir(work, run)
            os.close(work)
            try:
                # Exclusive assigned slot; no silently opening foreign prior state.
                name = 'learner' if slot == 0 else 'clone'
                os.mkdir(name, mode=0o700, dir_fd=runfd)
                learner = _mkdir(runfd, name)
                try:
                    token = os.urandom(32).hex()
                    marker = _open_file(learner, '.ownership', 'create')
                    with os.fdopen(marker, 'wb') as f:
                        f.write(token.encode('ascii'))
                        f.flush()
                        os.fsync(f.fileno())
                    os.fsync(learner)
                    return LearnerCapability(self.path/'work'/run/name, token, _identity(os.fstat(learner)), root=self, run_inode=_identity(os.fstat(runfd)))
                finally:
                    os.close(learner)
            finally:
                os.close(runfd)
        except OSError:
            raise ContractError() from None
        finally:
            os.close(root)

    def usage(self):
        root = self._validate()
        total, runs, run_bytes = 0, set(), {}
        def scan(fd, prefix):
            nonlocal total
            for name in os.listdir(fd):
                st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(st.st_mode):
                    _checked(st, directory=True)
                    if prefix in ('work', 'evaluation/runs', 'evaluation/partials'):
                        runs.add(name)
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        if _identity(os.fstat(child)) != _identity(st):
                            raise ContractError()
                        scan(child, prefix + '/' + name if prefix else name)
                    finally:
                        os.close(child)
                else:
                    _checked(st)
                    total += st.st_size
                    parts=prefix.split('/')
                    identity=parts[1] if len(parts)>=2 and parts[0]=='work' else parts[2] if len(parts)>=3 and parts[:2] in (['evaluation','runs'],['evaluation','partials']) else None
                    if identity is not None: run_bytes[identity]=run_bytes.get(identity,0)+st.st_size
                    if total > CAPS['root_bytes'] or len(runs) > CAPS['retained_runs']:
                        raise ContractError()
        try:
            scan(root, '')
            if len(runs)>CAPS['retained_runs']: raise ContractError()
            return Usage(total,len(runs),tuple(sorted(run_bytes.items())),tuple(sorted(runs)))
        except OSError:
            raise ContractError() from None
        finally:
            os.close(root)
