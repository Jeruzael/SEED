from pathlib import Path
import secrets
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .services.seed_service import SeedService, ServiceError
from .security import SecurityMiddleware
from .api.observer import observer_router
from .api.stream import StreamSlots
from .api.operator import operator_router
from .command_broker.broker import CommandBroker
from .services.settings import SettingsStore
from .services.backups import BackupStore
from seed.migrations import VERSION
from seed.version import CORE_VERSION

DASHBOARD_VERSION = '0.1'
DASHBOARD_EDITION = 'Observer Edition'


def create_app(home: Path, port: int = 8765, operator: bool = False,
               evaluation_root: Path | None = None) -> FastAPI:
    from .__main__ import server_options
    server_options(port)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    service = SeedService(home)
    if operator:
        with service.store.connection() as db:
            required = {'seed_schema', 'episodes', 'meta', 'q_values', 'concepts', 'events',
                        'runtime', 'concept_evidence', 'commands', 'annotations', 'settings',
                        'automations', 'automation_runs', 'audit', 'transitions',
                        'world_beliefs', 'world_pending', 'world_model_queue', 'world_model_processed',
                        'curiosity_assessments', 'curiosity_runtime', 'semantic_memories',
                        'semantic_memory_history', 'consolidation_runs', 'consolidation_state', 'self_model_current', 'decision_records'}
            if not required <= service.store.tables(db):
                raise ServiceError('incompatible_schema',
                                   'Operator mode requires the upgraded core schema; no migration was performed.', 409)
            versions = [row[0] for row in db.execute('SELECT version FROM seed_schema')]
            if versions != [VERSION]:
                raise ServiceError('incompatible_schema', 'Operator mode cannot use this schema version.', 409)
    token = secrets.token_urlsafe(32)
    app.state.service = service
    app.state.operator = operator
    app.add_middleware(SecurityMiddleware, port=port, token=token, operator=operator)
    @app.exception_handler(ServiceError)
    async def service_error(request, error):
        return JSONResponse({'error':{'code':error.code,'message':error.message}},status_code=error.status)
    @app.exception_handler(RequestValidationError)
    async def invalid(request,error):
        return JSONResponse({'error':{'code':'invalid_request','message':'Invalid request fields or query values.'}},status_code=422)
    @app.get('/api/bootstrap')
    def bootstrap():
        return {'token':token,'operator':operator,
                'version':f'{DASHBOARD_VERSION} {DASHBOARD_EDITION}','refresh_seconds':5,
                'core_source_version':CORE_VERSION,'dashboard_version':DASHBOARD_VERSION,
                'dashboard_edition':DASHBOARD_EDITION,'supported_schema_version':VERSION}
    app.include_router(observer_router(service, StreamSlots()))
    from .services.evaluation import EvaluationService
    from .api.evaluation import evaluation_router
    evaluation = EvaluationService.from_root(evaluation_root)
    app.state.evaluation = evaluation
    app.include_router(evaluation_router(evaluation))
    @app.get('/api/settings')
    def settings(): return SettingsStore(service.home).get()
    app.include_router(operator_router(service, CommandBroker(service, storage=BackupStore(service.home))))
    @app.get('/api/automations')
    def automations(): return {'items':[],'available':False}
    static = Path(__file__).parent / 'static'
    app.mount('/static', StaticFiles(directory=static), name='static')
    @app.get('/')
    def index(): return FileResponse(static / 'index.html')
    return app
