"""In-process pub/sub event bus + the `/ws/{space_id}` fan-out endpoint.

One `asyncio.Queue` per WS connection, keyed by `space_id`; `publish` fans a
JSON-safe event dict out to every queue subscribed to that space. There is no
cross-process transport here (a single demo process is the whole deployment
target for this hackathon build) — if that ever changes, this module is the
seam to swap for a real broker without touching any caller.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

HEARTBEAT_INTERVAL_SECONDS = 25

_subscribers: dict[str, set[asyncio.Queue]] = {}


def publish(space_id: str, event: dict) -> None:
    """Fan `event` out to every live subscriber of `space_id`. A no-op if
    nobody is listening — publishing never blocks on, or requires, a reader.
    """
    for queue in _subscribers.get(space_id, ()):
        queue.put_nowait(event)


def subscribe(space_id: str) -> asyncio.Queue:
    """Register a new queue for `space_id` and return it."""
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(space_id, set()).add(queue)
    return queue


def unsubscribe(space_id: str, queue: asyncio.Queue) -> None:
    """Drop `queue` from `space_id`'s subscriber set, pruning the set once empty."""
    subs = _subscribers.get(space_id)
    if subs is None:
        return
    subs.discard(queue)
    if not subs:
        _subscribers.pop(space_id, None)


async def _pump_events(websocket: WebSocket, queue: asyncio.Queue) -> None:
    """Forward published events to the socket; send a heartbeat ping whenever
    the space has been quiet for `HEARTBEAT_INTERVAL_SECONDS`.
    """
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            await websocket.send_json({"type": "ping"})
            continue
        await websocket.send_json(event)


async def _watch_for_disconnect(websocket: WebSocket) -> None:
    """Resolves the moment the client sends anything or closes the socket —
    the only way this side learns of a disconnect without itself blocking
    forever on a send.
    """
    while True:
        await websocket.receive_text()


@router.websocket("/ws/{space_id}")
async def space_events(websocket: WebSocket, space_id: str) -> None:
    await websocket.accept()
    queue = subscribe(space_id)
    try:
        pump_task = asyncio.create_task(_pump_events(websocket, queue))
        watch_task = asyncio.create_task(_watch_for_disconnect(websocket))
        try:
            await asyncio.wait({pump_task, watch_task}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in (pump_task, watch_task):
                if not task.done():
                    task.cancel()
            # Swallow WebSocketDisconnect/CancelledError/etc from either task —
            # any way this loop ends, cleanup below still runs.
            await asyncio.gather(pump_task, watch_task, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe(space_id, queue)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
