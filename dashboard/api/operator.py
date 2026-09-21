from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from ..command_broker.broker import CommandBroker
from ..services.settings import SettingsStore


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    confirmation: str | None = None


class SettingsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revision: int
    values: dict


def operator_router(service, broker):
    router = APIRouter(prefix='/api')
    @router.get('/commands')
    def commands(): return broker.available()
    @router.post('/commands/{name}')
    def request_command(name: str, request: CommandRequest):
        return broker.request(name, request.confirmation)
    @router.get('/commands/{command_id}/result')
    def result(command_id: str): return broker.result(command_id)
    @router.patch('/settings')
    def settings(request: SettingsRequest):
        result = SettingsStore(service.home).update(request.values, request.revision)
        service.invalidate()
        return result
    return router
