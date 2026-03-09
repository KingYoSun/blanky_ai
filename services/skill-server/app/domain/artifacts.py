import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings


class ArtifactStore:
    def __init__(self, settings: Settings):
        self._settings = settings

    def ensure_ready(self) -> None:
        (self._settings.artifacts_root / "media").mkdir(parents=True, exist_ok=True)

    def build_paths(self, filename_hint: str | None) -> tuple[Path, Path]:
        relative = Path("media") / self._safe_filename(filename_hint)
        artifact_path = self._settings.artifacts_root / relative
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        client_path = self._settings.artifacts_client_root / relative
        return artifact_path, client_path

    def _safe_filename(self, filename_hint: str | None) -> str:
        raw_name = Path(filename_hint or "image.png").name
        stem = Path(raw_name).stem or "image"
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or "image"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
        return f"{timestamp}-{stem}.png"
