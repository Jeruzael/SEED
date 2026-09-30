"""Bounded, read-only inspection of current semantic knowledge and prior revisions."""
from seed.semantic_memory import normalized_source
from seed.world_model import SIGNALS
from .read_store import ServiceError
from . import evidence_reads as er

MAX_ID = er.MAX_ID


def bounds(cursor, limit):
    if not er.integer(cursor) or not er.integer(limit,1,100):
        raise ServiceError('invalid_query','Invalid semantic pagination.')


def identity(semantic_id):
    if not er.integer(semantic_id,1):
        raise ServiceError('invalid_id','Invalid semantic memory ID.')


class SemanticReadService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def source_query(tables):
        selection = er.projection(er.SEMANTIC,'m')
        source = 'semantic_memories m'
        if 'world_beliefs' in tables:
            selection += ','+er.projection(er.WORLD,'w','source_')
            source += ' LEFT JOIN world_beliefs w ON w.id=m.source_belief_id'
        return selection,source

    @staticmethod
    def source_status(item, row, tables):
        if item.get('read_status')=='corrupt':return
        item['source_status']='source_unavailable'
        if 'world_beliefs' not in tables:return
        source=er.stored_record(row,'world','source_')
        if source.get('read_status')=='corrupt':return
        try:
            source['value_json']=er.compact(source.pop('value')).decode('ascii')
            normalized_source(source)  # Existing pure validation; no derived values exposed.
            item['source_status']='available'
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
            pass

    def memories(self, signal=None, scope=None, status=None, after=0, limit=50):
        bounds(after,limit)
        if (signal not in (None,*SIGNALS) or scope not in (None,'global','action') or
            status not in (None,'active','weakened','source_unavailable')):
            raise ServiceError('invalid_query','Invalid semantic filter.')
        with er.bounded_read(self.store) as db:
            unavailable,tables=er.feature(db,'semantic_memories',5,('world_beliefs',))
            if unavailable is not None:return unavailable
            selection,source=self.source_query(tables)
            result,rows=er.page(db,'semantic_memories','semantic',
                'id>? AND (? IS NULL OR signal=?) AND (? IS NULL OR scope=?) AND (? IS NULL OR status=?)',
                (after,signal,signal,scope,scope,status,status),limit,select=selection,source=source)
            for item,row in zip(result['items'],rows):self.source_status(item,row,tables)
            return er.capped(result,1847296)

    def memory(self, semantic_id):
        identity(semantic_id)
        with er.bounded_read(self.store) as db:
            unavailable,tables=er.feature(db,'semantic_memories',5,('world_beliefs',))
            if unavailable is not None:
                if unavailable.get('status')=='error':return unavailable
                raise ServiceError('not_found','Semantic memory does not exist.',404)
            selection,source=self.source_query(tables)
            row=db.execute(f'SELECT {selection} FROM {source} WHERE m.id=?',(semantic_id,)).fetchone()
            if row is None:raise ServiceError('not_found','Semantic memory does not exist.',404)
            item=er.stored_record(row,'semantic')
            self.source_status(item,row,tables)
            return er.capped(item,20480)

    def history(self, semantic_id, before=MAX_ID, limit=50):
        identity(semantic_id);bounds(before,limit)
        with er.bounded_read(self.store) as db:
            unavailable,tables=er.feature(db,'semantic_memories',5,('semantic_memory_history',))
            if unavailable is not None:
                if unavailable.get('status')=='error':return unavailable
                raise ServiceError('not_found','Semantic memory does not exist.',404)
            if 'semantic_memory_history' not in tables:
                return dict(available=False,status='error',reason='missing_feature_table',items=[],next_cursor=None)
            if db.execute('SELECT id FROM semantic_memories WHERE id=?',(semantic_id,)).fetchone() is None:
                raise ServiceError('not_found','Semantic memory does not exist.',404)
            rows=db.execute(f'SELECT {er.projection(er.HISTORY)} FROM semantic_memory_history WHERE semantic_memory_id=? AND revision<=? ORDER BY revision DESC LIMIT ?',
                (semantic_id,before,limit+1)).fetchall()
            result=dict(available=True,items=[er.stored_record(r,'history') for r in rows[:limit]],
                next_cursor=rows[limit-1]['revision']-1 if len(rows)>limit else None)
            return er.capped(result,3485696)

    def runs(self, before=MAX_ID, limit=50):
        bounds(before,limit)
        with er.bounded_read(self.store) as db:
            unavailable,_=er.feature(db,'consolidation_runs',5)
            if unavailable is not None:return unavailable
            result,_=er.page(db,'consolidation_runs','run','id<=?',(before,),limit,True)
            return er.capped(result,1847296)
