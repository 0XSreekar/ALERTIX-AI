import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import Response

from app import __version__
from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.redis_client import close_redis
from app.tasks.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("alertix_starting", version=__version__, env=settings.app_env)

    # Validate JWT secret is properly configured before accepting traffic
    settings.validate_jwt_secret()

    if settings.sentry_dsn_backend:
        sentry_sdk.init(
            dsn=settings.sentry_dsn_backend,
            traces_sample_rate=0.2 if settings.is_production else 1.0,
            environment=settings.app_env,
        )

    start_scheduler()

    yield

    stop_scheduler()
    await close_redis()
    log.info("alertix_shutdown")


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Alertix AI",
    description="Real-time multi-hazard disaster monitoring API for India",
    version=__version__,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Any, _rate_limit_exceeded_handler))

_cors_origins = settings.cors_origins_list
# credentials=True is incompatible with wildcard origins per the CORS spec
_allow_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security headers middleware ────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next: Any) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Allow http/ws connections in dev so the Vite frontend can reach localhost:8000
    if settings.is_production:
        connect_src = "'self' wss: https:"
    else:
        connect_src = "'self' http: https: ws: wss:"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        f"connect-src {connect_src};"
    )
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Request correlation ID middleware ──────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Public API routers ─────────────────────────────────────────
from app.api.ai import router as ai_router  # noqa: E402
from app.api.alerts import router as alerts_router  # noqa: E402
from app.api.auth import router as auth_router  # noqa: E402
from app.api.citizen_reports import router as citizen_reports_router  # noqa: E402
from app.api.contact import router as contact_router  # noqa: E402
from app.api.damage import router as damage_router  # noqa: E402
from app.api.events import router as events_router  # noqa: E402
from app.api.predict import router as predict_router  # noqa: E402
from app.api.processing import router as processing_router  # noqa: E402
from app.api.sos import router as sos_router  # noqa: E402

app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(events_router)
app.include_router(alerts_router)
app.include_router(sos_router)
app.include_router(predict_router)
app.include_router(damage_router)
app.include_router(contact_router)
app.include_router(processing_router)
app.include_router(__import__("app.api.ingestion", fromlist=["router"]).router)
app.include_router(citizen_reports_router)

# ── Internal routers ───────────────────────────────────────────
from app.api.internal_ingest import router as ingest_router  # noqa: E402
from app.api.internal_llm import router as llm_router  # noqa: E402

app.include_router(ingest_router)
app.include_router(llm_router)

# ── WebSocket ──────────────────────────────────────────────────
from app.ws.alerts import router as ws_router  # noqa: E402

app.include_router(ws_router)


# ── Health & version ───────────────────────────────────────────
@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/version", tags=["infra"])
async def version() -> dict:
    return {"version": __version__, "env": settings.app_env}
