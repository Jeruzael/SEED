from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from ..command_broker.broker import CommandBroker
from ..services.settings import SettingsStore
from ..services.interaction import InteractionService


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    confirmation: str | None = None


class SettingsRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    revision: int
    values: dict


class NoteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    text: str
    important: bool = False


class AnnotationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    important: bool
    tags: list[str]


def operator_router(service, broker):
    router = APIRouter(prefix='/api')
    interaction = InteractionService(service.home)
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
    @router.post('/notes')
    def note(request: NoteRequest):
        result = interaction.note(request.text, request.important)
        service.invalidate()
        return result
    @router.patch('/memories/{episode_id}/annotation')
    def annotate(episode_id: int, request: AnnotationRequest):
        result = interaction.annotate(episode_id, request.important, request.tags)
        service.invalidate()
        return result
    @router.get('/summary')
    def summary(since: float = 0):
        return interaction.summary(since)
    return router
