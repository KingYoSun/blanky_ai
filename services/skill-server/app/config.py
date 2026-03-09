from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")

    x_bearer_token: str | None = Field(default=None, validation_alias="X_BEARER_TOKEN")
    x_client_key: str | None = Field(default=None, validation_alias="X_CLIENT_KEY")
    x_client_secret: str | None = Field(default=None, validation_alias="X_CLIENT_SECRET")
    x_access_token: str | None = Field(default=None, validation_alias="X_ACCESS_TOKEN")
    x_refresh_token: str | None = Field(default=None, validation_alias="X_REFRESH_TOKEN")
    x_access_token_expires_at: str | None = Field(
        default=None, validation_alias="X_ACCESS_TOKEN_EXPIRES_AT"
    )
    x_token_state_path: Path = Field(
        default=Path("/state/x_token_state.json"), validation_alias="X_TOKEN_STATE_PATH"
    )
    x_refresh_leeway_seconds: int = Field(
        default=1800, validation_alias="X_REFRESH_LEEWAY_SECONDS"
    )
    x_refresh_check_interval_seconds: int = Field(
        default=300, validation_alias="X_REFRESH_CHECK_INTERVAL_SECONDS"
    )
    x_refresh_min_interval_seconds: int = Field(
        default=60, validation_alias="X_REFRESH_MIN_INTERVAL_SECONDS"
    )
    x_max_refresh_failures: int = Field(
        default=3, validation_alias="X_MAX_REFRESH_FAILURES"
    )

    skill_server_bind: str = Field(default="uds", validation_alias="SKILL_SERVER_BIND")
    skill_server_socket_path: Path = Field(
        default=Path("/run/skill-server/api.sock"),
        validation_alias="SKILL_SERVER_SOCKET_PATH",
    )
    skill_server_host: str = Field(
        default="0.0.0.0", validation_alias="SKILL_SERVER_HOST"
    )
    skill_server_port: int = Field(default=8081, validation_alias="SKILL_SERVER_PORT")
    skill_server_service_token: str | None = Field(
        default=None, validation_alias="SKILL_SERVER_SERVICE_TOKEN"
    )

    artifacts_root: Path = Field(
        default=Path("/artifacts"), validation_alias="SKILL_SERVER_ARTIFACT_ROOT"
    )
    artifacts_client_root: Path = Field(
        default=Path("/srv/skill-server-artifacts"),
        validation_alias="SKILL_SERVER_ARTIFACT_CLIENT_ROOT",
    )
    max_input_images: int = Field(default=14, validation_alias="MAX_INPUT_IMAGES")
    max_upload_bytes: int = Field(
        default=15 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES"
    )
    request_timeout_seconds: float = Field(
        default=30.0, validation_alias="REQUEST_TIMEOUT_SECONDS"
    )

    @field_validator(
        "gemini_api_key",
        "x_bearer_token",
        "x_client_key",
        "x_client_secret",
        "x_access_token",
        "x_refresh_token",
        "x_access_token_expires_at",
        "skill_server_service_token",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
