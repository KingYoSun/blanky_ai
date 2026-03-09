from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from app.schemas.twitter import (
    FollowRequest,
    RefreshRequest,
    ReplyRequest,
    SearchRequest,
    TweetActionRequest,
    TweetRequest,
)


router = APIRouter(prefix="/v1/x", tags=["x"])


@router.get("/auth/status")
def auth_status(request: Request) -> dict[str, object]:
    service = request.app.state.twitter_service
    return {
        "ok": True,
        "request_id": request.state.request_id,
        **service.auth_status(),
    }


@router.post("/auth/refresh")
def refresh_auth(request: Request, payload: RefreshRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.refresh_tokens(force=payload.force)
    result["request_id"] = request.state.request_id
    return result


@router.post("/tweets")
def post_tweet(request: Request, payload: TweetRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.post_tweet(payload.text, media_ids=payload.media_ids)
    result["request_id"] = request.state.request_id
    return result


@router.post("/tweets/media")
async def post_tweet_with_media(
    request: Request,
    text: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, object]:
    service = request.app.state.twitter_service
    media_files = []
    for upload in files:
        media_files.append(
            {
                "filename": upload.filename or "upload.bin",
                "content_type": upload.content_type or "application/octet-stream",
                "data": await upload.read(),
            }
        )
    result = service.post_tweet(text, media_files=media_files)
    result["request_id"] = request.state.request_id
    return result


@router.post("/media/upload")
async def upload_media(
    request: Request,
    files: list[UploadFile] = File(...),
) -> dict[str, object]:
    service = request.app.state.twitter_service
    media_files = []
    for upload in files:
        media_files.append(
            {
                "filename": upload.filename or "upload.bin",
                "content_type": upload.content_type or "application/octet-stream",
                "data": await upload.read(),
            }
        )
    result = service.upload_media(media_files)
    result["request_id"] = request.state.request_id
    return result


@router.post("/replies")
def post_reply(request: Request, payload: ReplyRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.reply_tweet(
        payload.tweet_id,
        payload.text,
        media_ids=payload.media_ids,
    )
    result["request_id"] = request.state.request_id
    return result


@router.post("/replies/media")
async def post_reply_with_media(
    request: Request,
    tweet_id: str = Form(...),
    text: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, object]:
    service = request.app.state.twitter_service
    media_files = []
    for upload in files:
        media_files.append(
            {
                "filename": upload.filename or "upload.bin",
                "content_type": upload.content_type or "application/octet-stream",
                "data": await upload.read(),
            }
        )
    result = service.reply_tweet(tweet_id, text, media_files=media_files)
    result["request_id"] = request.state.request_id
    return result


@router.post("/likes")
def like_tweet(request: Request, payload: TweetActionRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.like_tweet(payload.tweet_id)
    result["request_id"] = request.state.request_id
    return result


@router.post("/retweets")
def retweet(request: Request, payload: TweetActionRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.retweet(payload.tweet_id)
    result["request_id"] = request.state.request_id
    return result


@router.post("/follows")
def follow_user(request: Request, payload: FollowRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.follow_user(user_id=payload.user_id, username=payload.username)
    result["request_id"] = request.state.request_id
    return result


@router.post("/search")
def search_tweets(request: Request, payload: SearchRequest) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.search_tweets(
        query=payload.query,
        limit=payload.limit,
        recent=payload.recent,
        lang=payload.lang,
    )
    result["request_id"] = request.state.request_id
    return result


@router.get("/timeline")
def get_timeline(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    include_retweets: bool = False,
    exclude_retweets: bool = False,
) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.get_timeline(
        limit=limit,
        include_retweets=include_retweets,
        exclude_retweets=exclude_retweets,
    )
    result["request_id"] = request.state.request_id
    return result


@router.get("/mentions")
def get_mentions(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    since_id: str | None = Query(default=None),
    until_id: str | None = Query(default=None),
    pagination_token: str | None = Query(default=None),
) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.get_mentions(
        limit=limit,
        since_id=since_id,
        until_id=until_id,
        pagination_token=pagination_token,
    )
    result["request_id"] = request.state.request_id
    return result


@router.get("/users/by-username/{username}")
def get_user_by_username(request: Request, username: str) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.get_user(username=username)
    result["request_id"] = request.state.request_id
    return result


@router.get("/users/{user_id}")
def get_user_by_id(request: Request, user_id: str) -> dict[str, object]:
    service = request.app.state.twitter_service
    result = service.get_user(user_id=user_id)
    result["request_id"] = request.state.request_id
    return result
