from pydantic import BaseModel, Field, field_validator, model_validator


class TweetRequest(BaseModel):
    text: str = Field(min_length=1, max_length=280)
    media_ids: list[str] = Field(default_factory=list)

    @field_validator("media_ids")
    @classmethod
    def validate_media_ids(cls, media_ids: list[str]) -> list[str]:
        cleaned = [str(media_id).strip() for media_id in media_ids if str(media_id).strip()]
        if len(cleaned) > 4:
            raise ValueError("X supports up to 4 attached images per post.")
        return cleaned


class ReplyRequest(TweetRequest):
    tweet_id: str


class TweetActionRequest(BaseModel):
    tweet_id: str


class FollowRequest(BaseModel):
    user_id: str | None = None
    username: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "FollowRequest":
        if not self.user_id and not self.username:
            raise ValueError("Either user_id or username is required.")
        return self


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)
    recent: bool = False
    lang: str = "en"


class TweetUploadResponse(BaseModel):
    tweet_id: str
    url: str
    media_ids: list[str] = Field(default_factory=list)


class MediaUploadResponse(BaseModel):
    count: int
    media_ids: list[str] = Field(default_factory=list)


class RefreshRequest(BaseModel):
    force: bool = False
