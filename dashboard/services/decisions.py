"""Bounded read-only B8 inspection; frozen evidence, never policy recomputation."""
import sqlite3
from seed.decision_record import (MAX_ID, ACTIONS, integer, compact, strict_json, validate_record)
from .read_store import ServiceError

READ_BUDGET = 300000

# SQL bounds each transferred scalar as well as each JSON payload. LEFT JOIN
# preserves orphan corruption as a consumed page slot, rather than refilling it.
PAYLOAD = '''SELECT d.transition_id,
 CASE WHEN typeof(d.created_at) IN ('integer','real') THEN d.created_at ELSE NULL END AS created_at,
 substr(d.model,1,129) AS model,
 CASE WHEN typeof(d.model_version)='integer' THEN d.model_version ELSE NULL END AS model_version,
 substr(d.selected_action,1,129) AS selected_action,substr(d.selection_mode,1,129) AS selection_mode,
 substr(CAST(d.data_json AS BLOB),1,16385) AS data,
 substr(CAST(t.prediction_json AS BLOB),1,16385) AS prediction,
 substr(CAST(t.state_before_json AS BLOB),1,16385) AS state_before,
 substr(t.action,1,129) AS action
 FROM decision_records d LEFT JOIN transitions t ON t.id=d.transition_id'''


def _invalid(tid, detail):
    result=dict(available=False,status='error',reason='invalid_decision',transition_id=tid)
    if detail:result['record']=None
    return result


def _row(row, detail):
    tid=row['transition_id']
    try:
        record=strict_json(row['data'])
        validate_record(record,prediction=strict_json(row['prediction']),
                        state_before=strict_json(row['state_before']),mirrors=row)
        if detail:
            return dict(available=True,status='stored',reason=None,transition_id=tid,record=record)
        item={k:record[k] for k in ('transition_id','created_at','selected_at','model','model_version','selected_action',
                                  'selection_mode','policy_basis','eligible_actions','fallback_reason','decision_id')}
        selected=record['candidates'][record['selected_action']]
        item.update(available=True,status='stored',reason=None,
                    constraint_reasons={a:record['candidates'][a]['constraint_reasons'] for a in ACTIONS},
                    q_value=selected['q_value'],decision_utility=selected['decision_utility'])
        if len(compact(item))>1024:raise ValueError('invalid_summary')
        return item
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError,UnicodeError):
        return _invalid(tid,detail)


class DecisionReadService:
    def __init__(self,store):
        self.store=store

    def list(self,before=None,limit=20):
        if (before is not None and not integer(before,1)) or not integer(limit,1,50):
            raise ServiceError('invalid_query','Invalid decision cursor or limit.')
        return self._read(False,MAX_ID if before is None else before,limit)

    def detail(self,transition_id):
        if not integer(transition_id,1):
            raise ServiceError('invalid_query','Invalid decision ID.')
        return self._read(True,transition_id,1)

    def _read(self,detail,cursor,limit):
        def absent(status,reason):
            base=dict(available=False,status=status,reason=reason)
            return dict(**base,transition_id=cursor,record=None) if detail else dict(**base,items=[],next_cursor=None)
        try:
            with self.store.connection() as db:
                ticks=0
                def progress():
                    nonlocal ticks
                    ticks+=1000
                    return ticks>=READ_BUDGET
                db.execute('PRAGMA busy_timeout=0')
                db.set_progress_handler(progress,1000)
                try:
                    db.execute('BEGIN')
                    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('seed_schema','decision_records') LIMIT 2")}
                    if 'seed_schema' not in tables:
                        return absent('unavailable','legacy_schema')
                    versions=db.execute('SELECT version FROM seed_schema LIMIT 2').fetchall()
                    if len(versions)!=1 or not integer(versions[0][0],1,7):
                        raise ServiceError('incompatible_schema','Decision inspection cannot use this schema version.',409)
                    if versions[0][0]<7:
                        return absent('unavailable','legacy_schema')
                    if 'decision_records' not in tables:
                        return absent('error','missing_decision_table')
                    if detail:
                        row=db.execute(PAYLOAD+' WHERE d.transition_id=?',(cursor,)).fetchone()
                        if row is None:
                            raise ServiceError('decision_not_found','No decision record exists for this transition.',404)
                        result=_row(row,True)
                    else:
                        ids=[r[0] for r in db.execute('SELECT transition_id FROM decision_records WHERE transition_id<=? ORDER BY transition_id DESC LIMIT ?', (cursor,limit+1))]
                        next_cursor=ids[limit] if len(ids)>limit else None
                        ids=ids[:limit]
                        rows=[]
                        if ids:
                            marks=','.join('?' for _ in ids)
                            rows=db.execute(PAYLOAD+f' WHERE d.transition_id IN ({marks}) ORDER BY d.transition_id DESC',ids).fetchall()
                        result=dict(available=True,status='stored',reason=None,items=[_row(r,False) for r in rows],next_cursor=next_cursor)
                    if len(compact(result))>(17408 if detail else 53248):
                        raise ServiceError('invalid_decision_response','Decision response exceeds its bounded contract.',503)
                    return result
                except sqlite3.Error as error:
                    raise ServiceError('decision_read_unavailable','Decision evidence is temporarily unavailable.',503) from error
                finally:
                    db.set_progress_handler(None,0)
                    if db.in_transaction:db.rollback()
        except ServiceError as error:
            if error.code=='missing_database':
                return absent('unavailable','missing_home')
            if error.code=='database_unavailable':
                raise ServiceError('decision_read_unavailable','Decision evidence is temporarily unavailable.',503) from error
            raise
