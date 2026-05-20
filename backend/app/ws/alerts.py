"""WebSocket endpoints — /ws/alerts and /ws/events.

Subscribes to Redis pub/sub channels and fans out to connected clients.
"""

import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.logging import get_logger
from app.redis_client import get_redis

log = get_logger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(channel, set()).add(ws)
        log.info("ws_connect", channel=channel, total=len(self._connections[channel]))

    def disconnect(self, channel: str, ws: WebSocket):
        conns = self._connections.get(channel, set())
        conns.discard(ws)
        if not conns:
            self._connections.pop(channel, None)

    async def broadcast(self, channel: str, data: str):
        for ws in list(self._connections.get(channel, set())):
            try:
                await ws.send_text(data)
            except Exception:
                self.disconnect(channel, ws)


manager = ConnectionManager()

_pubsub_tasks: dict[str, asyncio.Task] = {}


async def _subscribe_redis(channel: str):
    """Background task that listens to a Redis pub/sub channel and broadcasts."""
    try:
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.broadcast(channel, message["data"])
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("redis_pubsub_error", channel=channel, error=str(exc))


def _ensure_pubsub(channel: str):
    if channel not in _pubsub_tasks or _pubsub_tasks[channel].done():
        _pubsub_tasks[channel] = asyncio.create_task(_subscribe_redis(channel))


@router.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    channel = "alerts:new"
    _ensure_pubsub(channel)
    await manager.connect(channel, ws)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(channel, ws)


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket, hazard_type: str = Query("earthquake")):
    channel = f"events:{hazard_type}"
    _ensure_pubsub(channel)
    await manager.connect(channel, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(channel, ws)
