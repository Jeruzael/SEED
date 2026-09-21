"""No executable, shell fragment, path or generated command enters this broker."""
import time
import uuid
from ..services.read_store import ServiceError, decode
from seed.paths import checked_path
from seed.telemetry import audit, emit

COMMANDS = {
    'observe': ('Observe now', False), 'reflect': ('Reflect now', False),
    'consolidate': ('Consolidate memory', False), 'backup': ('Create backup', False),
    'start': ('Start SEED', False), 'stop': ('Stop SEED', True), 'restart': ('Restart SEED', True),
    'export_status': ('Export status', False), 'open_logs': ('Open logs', False),
    'rotate_logs': ('Rotate managed logs', True),
}


class CommandBroker:
    def __init__(self, service, process=None, storage=None, clock=time.time):
        self.service, self.process, self.storage, self.clock = service, process or service.process, storage, clock
        self.handlers = {'observe':lambda:self.enqueue('observe'), 'reflect':lambda:self.enqueue('reflect'),
                         'consolidate':lambda:self.enqueue('consolidate'), 'rotate_logs':lambda:self.enqueue('rotate_logs'),
                         'backup':self.backup, 'start':self.process.start, 'stop':self.process.stop,
                         'restart':self.process.restart, 'export_status':self.service.status, 'open_logs':self.logs}

    def available(self):
        return {'items':[{'name':name,'label':label,'confirmation':confirmation} for name,(label,confirmation) in COMMANDS.items()]}

    def request(self, name, confirmation=None):
        if name not in COMMANDS:
            raise ServiceError('unknown_command', 'This command is not allowed.', 404)
        if COMMANDS[name][1] and confirmation != name:
            raise ServiceError('confirmation_required', f'Confirm the {name} operation.', 409)
        request_id = uuid.uuid4().hex
        with self.service.store.connection(write=True) as db:
            audit(db, 'command_requested', {'name':name, 'request_id':request_id}, {'status':'requested'})
            emit(db, 'OWNER', 'command_broker', f'Owner requested {name}', {'request_id':request_id})
        try:
            result = self.handlers[name]()
            if isinstance(result, dict) and result.get('status') == 'pending':
                outcome = result
            else:
                outcome = {'id':request_id, 'status':'complete', 'result':result}
        except Exception as error:
            with self.service.store.connection(write=True) as db:
                audit(db, 'command_failed', {'name':name, 'request_id':request_id}, {'error':str(error)[:300]})
            raise
        with self.service.store.connection(write=True) as db:
            audit(db, 'command_result', {'name':name, 'request_id':request_id}, outcome)
        self.service.invalidate()
        return outcome

    def enqueue(self, name):
        self.service.invalidate()
        status = self.service.status()
        if not status['fresh'] or status.get('lifecycle') != 'AWAKE':
            raise ServiceError('core_unavailable', 'This command needs a running, instrumented core.', 409)
        command_id = uuid.uuid4().hex
        with self.service.store.connection(write=True) as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE commands SET status='expired' WHERE status='pending' AND expires_at<=?", (self.clock(),))
            if db.execute("SELECT COUNT(*) FROM commands WHERE status='pending'").fetchone()[0] >= 20:
                raise ServiceError('queue_full', 'The core command queue is full.', 429)
            db.execute('INSERT INTO commands VALUES(?,?,?,?,?,?,NULL)',
                       (command_id, name, status['runtime']['session_id'], self.clock(), self.clock()+60, 'pending'))
        return {'id':command_id, 'status':'pending'}

    def result(self, command_id):
        with self.service.store.connection() as db:
            row = db.execute('SELECT * FROM commands WHERE id=?',(command_id,)).fetchone()
            if not row:
                raise ServiceError('not_found', 'Command receipt not found.', 404)
            item = dict(row)
            if item['status'] == 'pending' and item['expires_at'] <= self.clock():
                item['status'] = 'expired'
            item['result'] = decode(item.pop('result_json'), None)
            return item

    def backup(self):
        if self.storage is None:
            raise ServiceError('unavailable', 'Backup service is unavailable.', 503)
        return self.storage.create()

    def logs(self):
        items = []
        for name in ('seed.log','seed.err.log','dashboard.log'):
            path = checked_path(self.service.home, name)
            if path.is_file():
                with path.open('rb') as file:
                    file.seek(0,2)
                    file.seek(max(0,file.tell()-16384))
                    items.append({'name':name,'tail':file.read(16384).decode('utf-8',errors='replace')})
        return {'items':items, 'limit_bytes_per_file':16384}
