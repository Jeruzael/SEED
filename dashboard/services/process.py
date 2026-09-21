"""Fixed LaunchAgent observation. Control operations are added by the operator broker."""
import os
import re
import subprocess

LABEL = 'local.seed.organism'


class ProcessController:
    def __init__(self, home):
        self.home = home
        self.target = f'gui/{os.getuid()}/{LABEL}'

    def status(self):
        try:
            result = subprocess.run(['/bin/launchctl', 'print', self.target], capture_output=True,
                                    text=True, timeout=2, shell=False)
        except (OSError, subprocess.TimeoutExpired):
            return {'state': 'unknown', 'reason': 'LaunchAgent inspection unavailable'}
        if result.returncode:
            if 'Could not find service' in result.stderr or 'Could not find service' in result.stdout:
                return {'state': 'unregistered', 'pid': None}
            return {'state': 'unknown', 'reason': 'LaunchAgent inspection failed'}
        match = re.search(r'^\s*pid = (\d+)\s*$', result.stdout, re.M)
        return {'state': 'running' if match else 'loaded', 'pid': int(match[1]) if match else None}

    def validate(self):
        import plistlib
        from pathlib import Path
        from seed.paths import checked_path
        from .read_store import ServiceError
        expected_home = Path.home() / 'Library/Application Support/SEED'
        plist = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
        try:
            if self.home.absolute() != expected_home:
                raise ValueError('Lifecycle control is only available for the installed SEED home')
            checked_path(plist.parent, plist.name)
            checked_path(self.home, 'app/main.py')
            data = plistlib.loads(plist.read_bytes())
            args = data.get('ProgramArguments', [])
            if (plist.stat().st_uid != os.getuid() or plist.stat().st_mode & 0o022 or
                data.get('Label') != LABEL or data.get('KeepAlive') or len(args) != 2 or
                args[1] != str(self.home / 'app/main.py') or not Path(args[0]).is_absolute() or
                not Path(args[0]).is_file() or data.get('WorkingDirectory') != str(self.home / 'app') or
                data.get('EnvironmentVariables', {}).get('SEED_HOME') != str(self.home)):
                raise ValueError('Installed LaunchAgent does not match the approved SEED configuration')
            return plist
        except (OSError, ValueError, TypeError) as error:
            raise ServiceError('process_configuration', str(error), 409) from error

    def _run(self, args):
        from .read_store import ServiceError
        try:
            result = subprocess.run(['/bin/launchctl', *args], capture_output=True, text=True, timeout=5, shell=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ServiceError('process_operation', 'LaunchAgent operation failed or timed out; inspect status before retrying.', 503) from error
        if result.returncode:
            raise ServiceError('process_operation', 'LaunchAgent rejected the operation; inspect the installed configuration.', 409)

    def start(self):
        from seed.runtime import owner
        from .read_store import ServiceError
        plist = self.validate()
        status = self.status()
        if status['state'] == 'running':
            return status
        if owner(self.home / 'organism.lock'):
            raise ServiceError('process_conflict', 'A manually running core owns this SEED home.', 409)
        if status['state'] == 'unknown':
            raise ServiceError('process_unknown', 'Cannot verify LaunchAgent state.', 409)
        if status['state'] == 'unregistered':
            self._run(['bootstrap', f'gui/{os.getuid()}', str(plist)])
        else:
            self._run(['kickstart', self.target])
        return self.status()

    def stop(self):
        from seed.runtime import owner
        from .read_store import ServiceError
        self.validate()
        status = self.status()
        if status['state'] == 'unknown':
            raise ServiceError('process_unknown', 'Cannot verify LaunchAgent state.', 409)
        if status['state'] == 'unregistered':
            if owner(self.home / 'organism.lock'):
                raise ServiceError('process_conflict', 'Stop the manually running core in its terminal.', 409)
            return status
        self._run(['bootout', self.target])
        return self.status()

    def restart(self):
        self.stop()
        return self.start()
