from pathlib import Path

from fastapi import APIRouter, Request


router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz(request: Request) -> dict[str, object]:
    twitter_service = request.app.state.twitter_service
    nano_banana_service = request.app.state.nano_banana_service
    settings = request.app.state.settings

    return {
        "ok": True,
        "request_id": request.state.request_id,
        "nano_banana_configured": nano_banana_service.is_configured(),
        "x_auth": twitter_service.auth_status(),
        "artifacts_root": str(settings.artifacts_root),
    }


@router.get("/readyz")
def readyz(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    twitter_service = request.app.state.twitter_service
    artifacts_root = Path(settings.artifacts_root)
    artifacts_ready = artifacts_root.exists() and artifacts_root.is_dir()

    return {
        "ok": artifacts_ready,
        "request_id": request.state.request_id,
        "artifacts_ready": artifacts_ready,
        "x_auth": twitter_service.auth_status(),
    }
