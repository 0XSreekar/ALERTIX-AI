"""WebSocket endpoints — /ws/alerts and /ws/events.

Subscribes to Redis pub/sub channels and fans out to connected clients.
JWT token required as query parameter: ?token=<jwt>
"""

import asyncio

import jwt as pyjwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import get_jwt_secret
from app.logging import get_logger
from app.redis_client import get_redis

log = get_logger(__name__)
router = APIRouter(tags=["websocket"])

_WS_CLOSE_POLICY_VIOLATION = 1008


def _verify_ws_token(token: str | None) -> dict | None:
    """Decode and verify a JWT for WebSocket connections.

    Returns the payload dict on success, or None if the token is missing/invalid.
    Accepts both 'session' scope (legacy bearer tokens) and 'ws' scope (60s tickets
    minted via /api/auth/ws-ticket). HTTP API endpoints reject 'ws'-scoped tokens
    so a leaked ticket cannot be replayed against the REST API.
    """
    if not token:
        return None
    try:
        secret = get_jwt_secret()
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
    except pyjwt.PyJWTError:
        return None
    scope = payload.get("scope", "session")
    if scope not in ("session", "ws"):
        return None
    return payload


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
async def ws_alerts(ws: WebSocket, token: str | None = Query(default=None)):
    payload = _verify_ws_token(token)
    if payload is None:
        await ws.close(code=_WS_CLOSE_POLICY_VIOLATION, reason="Missing or invalid JWT token")
        return

    user_id: str = payload.get("sub", "")
    role: str = payload.get("role", "citizen")
    log.info("ws_alerts_auth", user_id=user_id, role=role)

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
async def ws_events(
    ws: WebSocket,
    hazard_type: str = Query("earthquake"),
    token: str | None = Query(default=None),
):
    payload = _verify_ws_token(token)
    if payload is None:
        await ws.close(code=_WS_CLOSE_POLICY_VIOLATION, reason="Missing or invalid JWT token")
        return

    user_id: str = payload.get("sub", "")
    role: str = payload.get("role", "citizen")
    log.info("ws_events_auth", user_id=user_id, role=role, hazard_type=hazard_type)

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
