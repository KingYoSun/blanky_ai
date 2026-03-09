from pathlib import Path

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()

    if settings.skill_server_bind == "uds":
        socket_path = Path(settings.skill_server_socket_path)
        socket_path.parent.mkdir(parents=True, exist_ok=True)
        if socket_path.exists():
            socket_path.unlink()
        uvicorn.run("app.main:app", uds=str(socket_path), log_level="info")
        return

    uvicorn.run(
        "app.main:app",
        host=settings.skill_server_host,
        port=settings.skill_server_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
