"""GET-only Evaluation API (B10 I26).

Every route delegates to the read-only EvaluationService. Query strings
are validated from the raw request: duplicate or unknown parameters are
rejected, run IDs are exactly 32 lowercase hex characters, cursors are
opaque and at most 512 bytes, chunk indexes are bounded integers, and
file IDs come from the fixed stored inventory (enforced by the reader's
receipt-verified chunk contract). No mutation verb exists here.
"""
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from ..services.evaluation import EvaluationService
from ..services.read_store import ServiceError

_RESPONSE_BYTES = 1024 * 1024


def _respond(payload):
    """Serialize once and enforce the 1 MiB response ceiling on the
    exact bytes that will be sent. An oversized indivisible response
    fails explicitly; scientific content is never truncated to fit."""
    response = JSONResponse(payload)
    if len(response.body) > _RESPONSE_BYTES:
        raise ServiceError(
            'resource_limit',
            'Evaluation response exceeded its approved size limit.',
            429)
    return response

_RUN_ID = re.compile(r'^[0-9a-f]{32}$')
_TOKEN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')
_DIGITS = re.compile(r'^[0-9]{1,10}$')
_FILE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')


def _invalid(message='Invalid request fields or query values.'):
    return ServiceError('invalid_request', message, 422)


def _params(request: Request, allowed: set) -> dict:
    items = request.query_params.multi_items()
    keys = [key for key, _ in items]
    if len(keys) != len(set(keys)) or not set(keys) <= allowed:
        raise _invalid('Duplicate or unknown query parameters.')
    return dict(items)


def _run_id(value: str) -> str:
    if not _RUN_ID.fullmatch(value):
        raise _invalid('Invalid run ID.')
    return value


def _limit(params: dict) -> int:
    raw = params.get('limit', '20')
    if not _DIGITS.fullmatch(raw):
        raise _invalid('Invalid page limit.')
    value = int(raw)
    if not 1 <= value <= 20:
        raise _invalid('Invalid page limit.')
    return value


def _cursor(params: dict):
    raw = params.get('cursor')
    if raw is None:
        return None
    if len(raw.encode('utf-8')) > 512:
        raise _invalid('Invalid cursor.')
    return raw


def _event_key(value: str) -> tuple:
    parts = value.split(':')
    if len(parts) != 4:
        raise _invalid('Invalid event identity.')
    phase, subcase, ordinal, stage = parts
    if not (_TOKEN.fullmatch(phase) and _TOKEN.fullmatch(subcase)
            and _TOKEN.fullmatch(stage)):
        raise _invalid('Invalid event identity.')
    if not _DIGITS.fullmatch(ordinal):
        raise _invalid('Invalid event identity.')
    number = int(ordinal)
    if number > 2**63 - 1:
        raise _invalid('Invalid event identity.')
    return (phase, subcase, number, stage)


def evaluation_router(service: EvaluationService) -> APIRouter:
    router = APIRouter(prefix='/api/evaluation')

    @router.get('/runs')
    def runs(request: Request):
        with service.request_context() as guard:
            params = _params(request, {'limit', 'cursor'})
            response = _respond(service.runs(_cursor(params),
                                             _limit(params)))
            guard.enforce()
            return response

    @router.get('/runs/{run_id}')
    def detail(request: Request, run_id: str):
        with service.request_context() as guard:
            _params(request, set())
            response = _respond(service.detail(_run_id(run_id)))
            guard.enforce()
            return response

    @router.get('/runs/{run_id}/measurements')
    def measurements(request: Request, run_id: str):
        with service.request_context() as guard:
            params = _params(request, {'limit', 'cursor'})
            response = _respond(service.measurements(
                _run_id(run_id), _cursor(params), _limit(params)))
            guard.enforce()
            return response

    @router.get('/runs/{run_id}/events')
    def events(request: Request, run_id: str):
        with service.request_context() as guard:
            params = _params(request, {'limit', 'cursor'})
            response = _respond(service.events(
                _run_id(run_id), _cursor(params), _limit(params)))
            guard.enforce()
            return response

    @router.get('/runs/{run_id}/events/{event_key}')
    def event(request: Request, run_id: str, event_key: str):
        with service.request_context() as guard:
            _params(request, set())
            response = _respond(service.event(
                _run_id(run_id), _event_key(event_key)))
            guard.enforce()
            return response

    @router.get('/runs/{run_id}/curve')
    def curve(request: Request, run_id: str):
        with service.request_context() as guard:
            params = _params(request, {'metric', 'series'})
            metric, series = params.get('metric'), params.get('series')
            if not metric or not series or not _NAME.fullmatch(metric) \
                    or not _NAME.fullmatch(series):
                raise _invalid('Invalid curve selection.')
            response = _respond(service.curve(_run_id(run_id), metric,
                                              series))
            guard.enforce()
            return response

    @router.get('/compare')
    def compare(request: Request):
        with service.request_context() as guard:
            params = _params(request, {'left', 'right', 'metric'})
            left, right = params.get('left'), params.get('right')
            if not left or not right:
                raise _invalid('Compare requires two run IDs.')
            metric = params.get('metric')
            if metric is not None and not _NAME.fullmatch(metric):
                raise _invalid('Invalid metric.')
            response = _respond(service.compare(
                _run_id(left), _run_id(right), metric))
            guard.enforce()
            return response

    @router.get('/runs/{run_id}/files/{file_id}')
    def files(request: Request, run_id: str, file_id: str):
        with service.request_context() as guard:
            params = _params(request, {'chunk'})
            if not _FILE_ID.fullmatch(file_id) or '..' in file_id:
                raise _invalid('Invalid file ID.')
            raw = params.get('chunk', '0')
            if not _DIGITS.fullmatch(raw):
                raise _invalid('Invalid chunk index.')
            data = service.chunk(_run_id(run_id), file_id, int(raw))
            if len(data) > _RESPONSE_BYTES:
                raise ServiceError(
                    'resource_limit',
                    'Evaluation response exceeded its approved size '
                    'limit.', 429)
            response = Response(
                content=data, media_type='application/octet-stream',
                headers={'Content-Disposition':
                         f'attachment; filename="{file_id}"'})
            guard.enforce()
            return response

    return router
