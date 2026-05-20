from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import __version__
from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.redis_client import close_redis

settings = get_settings()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("alertix_starting", version=__version__, env=settings.app_env)

    if settings.sentry_dsn_backend:
        sentry_sdk.init(
            dsn=settings.sentry_dsn_backend,
            traces_sample_rate=0.2 if settings.is_production else 1.0,
            environment=settings.app_env,
        )

    yield

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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public API routers ─────────────────────────────────────────
from app.api.events import router as events_router  # noqa: E402
from app.api.alerts import router as alerts_router  # noqa: E402
from app.api.sos import router as sos_router  # noqa: E402
from app.api.predict import router as predict_router  # noqa: E402
from app.api.damage import router as damage_router  # noqa: E402
from app.api.contact import router as contact_router  # noqa: E402

app.include_router(events_router)
app.include_router(alerts_router)
app.include_router(sos_router)
app.include_router(predict_router)
app.include_router(damage_router)
app.include_router(contact_router)

# ── Internal routers ───────────────────────────────────────────
from app.api.internal_ingest import router as ingest_router  # noqa: E402

app.include_router(ingest_router)

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
