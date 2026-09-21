import asyncio
import json
from starlette.concurrency import run_in_threadpool
from ..services.read_store import ServiceError


def encode_event(event):
    return f"id: {event['id']}\nevent: seed\ndata: {json.dumps(event, ensure_ascii=True, allow_nan=False)}\n\n"


class StreamSlots:
    def __init__(self, maximum=8):
        self.maximum, self.active = maximum, 0

    def acquire(self):
        if self.active >= self.maximum:
            return False
        self.active += 1
        return True

    def release(self):
        self.active = max(0, self.active-1)


async def event_stream(request, service, slots, after):
    try:
        ticks = 0
        while not await request.is_disconnected():
            try:
                batch = await run_in_threadpool(service.events, after, 100)
                if batch['reset']:
                    after = 0
                    yield 'event: reset\ndata: {}\n\n'
                if batch['gap']:
                    yield 'event: gap\ndata: {}\n\n'
                if batch['legacy'] and ticks == 0:
                    yield 'event: legacy\ndata: {}\n\n'
                for event in batch['items']:
                    after = event['id']
                    yield encode_event(event)
                if ticks % 7 == 0:
                    yield ': heartbeat\n\n'
            except ServiceError:
                yield 'event: unavailable\ndata: {}\n\n'
            ticks += 1
            await asyncio.sleep(2)
    finally:
        slots.release()
