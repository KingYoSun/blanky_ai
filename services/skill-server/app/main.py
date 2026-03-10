import logging
from contextlib import asynccontextmanager

import httpx
import tweepy
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.nano_banana import router as nano_banana_router
from app.api.x_api import router as x_router
from app.clients.gemini import NanoBananaService
from app.clients.twitter import TwitterService
from app.config import get_settings
from app.domain.artifacts import ArtifactStore
from app.domain.credentials import XTokenStore
from app.domain.token_scheduler import TokenScheduler
from app.middleware.logging import RequestContextMiddleware
from app.utils.http_errors import (
    extract_httpx_status_code,
    extract_response_detail,
    extract_tweepy_detail,
    extract_tweepy_status_code,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    artifacts = ArtifactStore(settings)
    artifacts.ensure_ready()

    token_store = XTokenStore(settings)
    twitter_service = TwitterService(settings, token_store)
    nano_banana_service = NanoBananaService(settings, artifacts)
    token_scheduler = TokenScheduler(twitter_service, settings)

    app.state.settings = settings
    app.state.artifacts = artifacts
    app.state.token_store = token_store
    app.state.twitter_service = twitter_service
    app.state.nano_banana_service = nano_banana_service
    app.state.token_scheduler = token_scheduler

    await token_scheduler.start()
    try:
        yield
    finally:
        await token_scheduler.stop()


app = FastAPI(title="blanky local skill server", lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)


@app.middleware("http")
async def require_service_token(request: Request, call_next):
    settings = request.app.state.settings if hasattr(request.app.state, "settings") else get_settings()
    expected_token = settings.skill_server_service_token
    if expected_token:
        provided_token = request.headers.get("x-skill-service-token")
        if provided_token != expected_token:
            return JSONResponse(status_code=401, content={"detail": "Invalid skill server token."})
    return await call_next(request)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(tweepy.TweepyException)
async def tweepy_exception_handler(request: Request, exc: tweepy.TweepyException):
    status_code = extract_tweepy_status_code(exc)
    detail = extract_tweepy_detail(exc)
    logger.warning(
        "Tweepy error on %s %s: status=%s detail=%s",
        request.method,
        request.url.path,
        status_code,
        detail,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(httpx.HTTPStatusError)
async def httpx_status_error_handler(request: Request, exc: httpx.HTTPStatusError):
    status_code = extract_httpx_status_code(exc)
    detail = extract_response_detail(exc.response)
    logger.warning(
        "HTTP upstream error on %s %s: status=%s detail=%s",
        request.method,
        request.url.path,
        status_code,
        detail,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled skill-server exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(health_router)
app.include_router(nano_banana_router)
app.include_router(x_router)
