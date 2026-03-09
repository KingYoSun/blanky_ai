import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock

from app.config import Settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass
class XTokenState:
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None
    token_type: str | None = None
    scope: str | None = None

    def seconds_remaining(self) -> int | None:
        if self.expires_at is None:
            return None
        return int((self.expires_at - utcnow()).total_seconds())

    def is_expired(self) -> bool:
        remaining = self.seconds_remaining()
        return remaining is not None and remaining <= 0

    def to_json_dict(self) -> dict[str, str | None]:
        data = asdict(self)
        for key in ("expires_at", "updated_at"):
            value = data[key]
            data[key] = value.isoformat() if value else None
        return data

    @classmethod
    def from_json_dict(cls, payload: dict[str, str | None]) -> "XTokenState":
        return cls(
            access_token=payload.get("access_token"),
            refresh_token=payload.get("refresh_token"),
            expires_at=parse_datetime(payload.get("expires_at")),
            updated_at=parse_datetime(payload.get("updated_at")),
            token_type=payload.get("token_type"),
            scope=payload.get("scope"),
        )


class XTokenStore:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._lock = RLock()
        self._state = self._load_initial_state()

    def _initial_state_from_env(self) -> XTokenState:
        expires_at = parse_datetime(self._settings.x_access_token_expires_at)
        if expires_at is None and self._settings.x_access_token:
            expires_at = utcnow() + timedelta(minutes=5)

        return XTokenState(
            access_token=self._settings.x_access_token,
            refresh_token=self._settings.x_refresh_token,
            expires_at=expires_at,
            updated_at=utcnow() if self._settings.x_access_token else None,
        )

    def _load_initial_state(self) -> XTokenState:
        path = Path(self._settings.x_token_state_path)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return XTokenState.from_json_dict(payload)
        return self._initial_state_from_env()

    def get(self) -> XTokenState:
        with self._lock:
            return XTokenState(
                access_token=self._state.access_token,
                refresh_token=self._state.refresh_token,
                expires_at=self._state.expires_at,
                updated_at=self._state.updated_at,
                token_type=self._state.token_type,
                scope=self._state.scope,
            )

    def save(self, state: XTokenState) -> XTokenState:
        with self._lock:
            path = Path(self._settings.x_token_state_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            payload = state.to_json_dict()
            tmp_path = path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp_path.replace(path)

            self._state = state
            return self.get()
