from pydantic import BaseModel, Field


class NanoBananaResponse(BaseModel):
    artifact_path: str
    media_path: str
    width: int | None
    height: int | None
    model: str
    request_id: str
    text_responses: list[str] = Field(default_factory=list)
