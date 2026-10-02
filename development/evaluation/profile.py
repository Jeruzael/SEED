"""Coordinator-owned read-only source/profile identity; no environment dump."""
import ast
from dataclasses import asdict, dataclass
import hashlib
import os
import platform
import sqlite3
import subprocess
import sys
from .contracts import ContractError, ExperimentSpec, strict_json
from .paths import EvaluationRoot


@dataclass(frozen=True)
class Profile:
    source_commit: str
    clean: bool
    lock_digest: str
    schema_version: int
    core_version: str
    python_implementation: str
    python_version: str
    sqlite_version: str
    sqlite_compile: tuple[str, ...]
    os_name: str
    architecture: str
    adapter_version: int = 1
    rng_algorithm: str = 'python-mt19937-v1'
    clock_version: str = 'staged-v1'
    uuid_version: str = 'role-counter-v1'

    def as_dict(self):
        return asdict(self)


def _constant(path, name):
    for n in ast.parse(path.read_text()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id == name for t in n.targets):
            return ast.literal_eval(n.value)
    raise ContractError()


def capture_profile(checkout):
    if type(checkout) is not EvaluationRoot:
        raise ContractError()
    fd = checkout._validate()
    os.close(fd)
    path = checkout.path.parent
    def git(*args):
        try:
            return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.DEVNULL,timeout=5).decode().strip()
        except (OSError,ValueError,subprocess.SubprocessError):
            raise ContractError() from None
    commit = git('rev-parse','HEAD')
    clean = not git('status','--porcelain=v1','--untracked-files=all')
    lock_digest = hashlib.sha256((path/'requirements-lock.txt').read_bytes()).hexdigest()
    with sqlite3.connect(':memory:') as db:
        compile_facts = tuple(sorted(r[0] for r in db.execute('PRAGMA compile_options')))
    profile = Profile(commit,clean,lock_digest,_constant(path/'seed/migrations.py','VERSION'),
                      _constant(path/'seed/version.py','CORE_VERSION'),platform.python_implementation(),
                      platform.python_version(),sqlite3.sqlite_version,compile_facts,platform.system(),platform.machine())
    if git('rev-parse','HEAD') != commit or (not git('status','--porcelain=v1','--untracked-files=all')) != clean:
        raise ContractError()
    fd = checkout._validate()
    os.close(fd)
    return profile


def require_source(spec, profile):
    value = strict_json(spec.body, max_bytes=128*1024) if isinstance(spec,ExperimentSpec) else spec
    if not profile.clean or profile.schema_version != 7 or value['source_commit'] != profile.source_commit or value['lock_digest'] != profile.lock_digest:
        raise ContractError()


def compatible(left, right):
    return left.clean and right.clean and left == right
