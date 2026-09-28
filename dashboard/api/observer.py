from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse, Response
from seed.decision_record import compact
from .stream import event_stream
from ..services.read_store import ServiceError


def observer_router(service, slots):
    router = APIRouter(prefix='/api')
    @router.get('/status')
    def status(): return service.status()
    @router.get('/environment')
    def environment(): return service.environment()
    @router.get('/health')
    def health(): return service.health()
    @router.get('/storage')
    def storage(): return service.storage()
    @router.get('/development')
    def development(): return service.development()
    @router.get('/learning')
    def learning(): return service.learning()
    @router.get('/concepts')
    def concepts(): return service.concepts()
    @router.get('/self-model')
    def self_model(request: Request):
        if request.query_params:
            raise ServiceError('invalid_query', 'Self model inspection accepts no query parameters.')
        return service.self_model()
    def decision_query(request, allowed):
        seen=set()
        for key,value in request.query_params.multi_items():
            if key not in allowed or key in seen or not value.isascii() or not value.isdigit():
                raise ServiceError('invalid_query', 'Invalid decision query.')
            seen.add(key)

    @router.get('/decisions')
    def decisions(request: Request):
        decision_query(request, {'before','limit'})
        # Avoid parsing unbounded integer strings even on Python versions without
        # the interpreter's integer conversion limit.
        if any(len(v)>19 for v in request.query_params.values()):
            raise ServiceError('invalid_query', 'Invalid decision query.')
        before=request.query_params.get('before')
        limit=request.query_params.get('limit','20')
        result=service.decisions(None if before is None else int(before),int(limit))
        return Response(compact(result),media_type='application/json')

    @router.get('/decisions/{transition_id}')
    def decision(transition_id: str, request: Request):
        decision_query(request,set())
        if len(transition_id)>19 or not transition_id.isascii() or not transition_id.isdigit():
            raise ServiceError('invalid_query', 'Invalid decision ID.')
        return Response(compact(service.decision(int(transition_id))),media_type='application/json')

    @router.get('/world-beliefs')
    def world_beliefs(signal: str | None = Query(None, max_length=32),
                      scope: str | None = Query(None, max_length=16),
                      scope_value: str | None = Query(None, max_length=16),
                      after: int = Query(0, ge=0, le=2**63-1), limit: int = Query(50, ge=1, le=100)):
        return service.world_beliefs(signal, scope, scope_value, after, limit)
    @router.get('/world-beliefs/{belief_id}')
    def world_belief(belief_id: int): return service.world_belief(belief_id)
    @router.get('/curiosity')
    def curiosity(before: int = Query(2**63-1, ge=0, le=2**63-1), limit: int = Query(50, ge=1, le=100)):
        return service.curiosity_assessments(before, limit)
    @router.get('/curiosity/summary')
    def curiosity_summary(): return service.curiosity_summary()
    @router.get('/curiosity/{transition_id}')
    def curiosity_assessment(transition_id: int): return service.curiosity_assessment(transition_id)
    @router.get('/semantic-memories')
    def semantic_memories(signal: str | None = Query(None, max_length=32),
                          scope: str | None = Query(None, max_length=16),
                          status: str | None = Query(None, max_length=32),
                          after: int = Query(0, ge=0, le=2**63-1), limit: int = Query(50, ge=1, le=100)):
        return service.semantic_memories(signal, scope, status, after, limit)
    @router.get('/semantic-memories/{semantic_id}')
    def semantic_memory(semantic_id: int): return service.semantic_memory(semantic_id)
    @router.get('/semantic-memories/{semantic_id}/history')
    def semantic_history(semantic_id: int, before: int = Query(2**63-1, ge=0, le=2**63-1),
                         limit: int = Query(50, ge=1, le=100)):
        return service.semantic_history(semantic_id, before, limit)
    @router.get('/consolidation-runs')
    def consolidation_runs(before: int = Query(2**63-1, ge=0, le=2**63-1),
                           limit: int = Query(50, ge=1, le=100)):
        return service.consolidation_runs(before, limit)
    @router.get('/history')
    def history(limit: int = Query(200, ge=2, le=500)): return service.history(limit)
    @router.get('/memories')
    def memories(search: str = Query('', max_length=200), event: str | None = Query(None,max_length=50),
                 sort: str = 'newest', page: int = Query(1,ge=1,le=100000), page_size: int = Query(50,ge=1,le=100)):
        return service.memories(search,event,sort,page,page_size)
    @router.get('/memories/{episode_id}')
    def memory(episode_id: int): return service.memory(episode_id)
    @router.get('/events')
    def events(after: int = Query(0,ge=0,le=2**63-1), limit: int = Query(100,ge=1,le=100)):
        return service.events(after,limit)
    @router.get('/stream')
    async def stream(request: Request, after: int = Query(0,ge=0,le=2**63-1)):
        raw = request.headers.get('last-event-id')
        if raw is not None:
            try:
                after = int(raw)
                if not 0 <= after <= 2**63-1: raise ValueError()
            except ValueError:
                raise ServiceError('invalid_cursor','Invalid event cursor.') from None
        if not slots.acquire():
            raise ServiceError('stream_limit','Too many event streams; close another dashboard tab.',429)
        return StreamingResponse(event_stream(request,service,slots,after),media_type='text/event-stream',
                                 headers={'X-Accel-Buffering':'no'})
    return router
