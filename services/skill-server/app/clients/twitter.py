import logging
import mimetypes
from datetime import timedelta
from io import BytesIO
from threading import Lock
from typing import Any, Callable

import httpx
import tweepy
from PIL import Image as PILImage

from app.config import Settings
from app.domain.credentials import XTokenState, XTokenStore, utcnow


logger = logging.getLogger(__name__)


def _tweet_to_dict(
    tweet: tweepy.Tweet,
    author_map: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    author_id = str(tweet.author_id) if getattr(tweet, "author_id", None) else None
    payload = {
        "id": str(tweet.id),
        "text": tweet.text,
        "created_at": tweet.created_at.isoformat() if getattr(tweet, "created_at", None) else None,
        "author_id": author_id,
        "public_metrics": getattr(tweet, "public_metrics", None),
    }
    if author_id and author_map and author_id in author_map:
        payload["author"] = author_map[author_id]
    return payload


def _user_to_dict(user: tweepy.User) -> dict[str, Any]:
    user_id = getattr(user, "id", None)
    return {
        "id": str(user_id) if user_id is not None else None,
        "username": getattr(user, "username", None),
        "name": getattr(user, "name", None),
        "description": getattr(user, "description", None),
        "location": getattr(user, "location", None),
        "verified": getattr(user, "verified", None),
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        "public_metrics": getattr(user, "public_metrics", None),
    }


class TwitterService:
    def __init__(self, settings: Settings, token_store: XTokenStore):
        self._settings = settings
        self._token_store = token_store
        self._refresh_lock = Lock()
        self._last_refresh_attempt_at = None
        self._last_refresh_at = None
        self._refresh_failures = 0
        self._last_refresh_error: str | None = None

    def can_refresh(self) -> bool:
        state = self._token_store.get()
        return bool(
            self._settings.x_client_key
            and self._settings.x_client_secret
            and state.refresh_token
        )

    def auth_status(self) -> dict[str, Any]:
        state = self._token_store.get()
        return {
            "configured": bool(state.access_token),
            "can_refresh": self.can_refresh(),
            "expires_at": state.expires_at.isoformat() if state.expires_at else None,
            "seconds_remaining": state.seconds_remaining(),
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
            "token_type": state.token_type,
            "scope": state.scope,
            "refresh_failures": self._refresh_failures,
            "last_refresh_at": self._last_refresh_at.isoformat()
            if self._last_refresh_at
            else None,
            "last_refresh_error": self._last_refresh_error,
        }

    def refresh_if_due(self) -> dict[str, Any]:
        state = self._token_store.get()
        if not self._needs_refresh(state):
            return {
                "ok": True,
                "refreshed": False,
                **self.auth_status(),
            }
        return self.refresh_tokens(force=False)

    def refresh_tokens(self, force: bool = False) -> dict[str, Any]:
        with self._refresh_lock:
            state = self._token_store.get()
            if not self.can_refresh():
                raise RuntimeError("X token refresh is not configured on skill-server.")

            if not force and not self._needs_refresh(state):
                return {
                    "ok": True,
                    "refreshed": False,
                    **self.auth_status(),
                }

            now = utcnow()
            if (
                self._last_refresh_attempt_at is not None
                and now - self._last_refresh_attempt_at
                < timedelta(seconds=self._settings.x_refresh_min_interval_seconds)
                and not state.is_expired()
            ):
                return {
                    "ok": True,
                    "refreshed": False,
                    **self.auth_status(),
                }

            self._last_refresh_attempt_at = now

            try:
                response = httpx.post(
                    "https://api.twitter.com/2/oauth2/token",
                    auth=(self._settings.x_client_key, self._settings.x_client_secret),
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": state.refresh_token,
                        "client_id": self._settings.x_client_key,
                    },
                    timeout=self._settings.request_timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()

                expires_in = int(payload.get("expires_in", 7200))
                refreshed_state = XTokenState(
                    access_token=payload.get("access_token"),
                    refresh_token=payload.get("refresh_token") or state.refresh_token,
                    expires_at=utcnow() + timedelta(seconds=expires_in),
                    updated_at=utcnow(),
                    token_type=payload.get("token_type"),
                    scope=payload.get("scope"),
                )
                self._token_store.save(refreshed_state)

                self._last_refresh_at = utcnow()
                self._refresh_failures = 0
                self._last_refresh_error = None

                logger.info("X access token refreshed successfully")
                return {
                    "ok": True,
                    "refreshed": True,
                    **self.auth_status(),
                }
            except Exception as exc:
                self._refresh_failures += 1
                self._last_refresh_error = str(exc)
                logger.warning("X token refresh failed: %s", exc)
                raise

    def post_tweet(
        self,
        text: str,
        media_files: list[dict[str, Any]] | None = None,
        media_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        media_ids = self._resolve_media_ids(
            media_files=media_files or [],
            media_ids=media_ids or [],
        )
        response = self._execute_user_call(
            lambda client: client.create_tweet(
                text=text,
                media_ids=media_ids or None,
                user_auth=False,
            )
        )
        tweet_id = response.data["id"]
        return {
            "tweet_id": str(tweet_id),
            "url": f"https://twitter.com/user/status/{tweet_id}",
            "media_ids": media_ids,
        }

    def reply_tweet(
        self,
        tweet_id: str,
        text: str,
        media_files: list[dict[str, Any]] | None = None,
        media_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        media_ids = self._resolve_media_ids(
            media_files=media_files or [],
            media_ids=media_ids or [],
        )
        response = self._execute_user_call(
            lambda client: client.create_tweet(
                text=text,
                in_reply_to_tweet_id=tweet_id,
                media_ids=media_ids or None,
                user_auth=False,
            )
        )
        reply_id = response.data["id"]
        return {
            "reply_id": str(reply_id),
            "url": f"https://twitter.com/user/status/{reply_id}",
            "media_ids": media_ids,
        }

    def upload_media(self, media_files: list[dict[str, Any]]) -> dict[str, Any]:
        media_ids = self._upload_media_files(media_files)
        return {
            "count": len(media_ids),
            "media_ids": media_ids,
        }

    def like_tweet(self, tweet_id: str) -> dict[str, Any]:
        response = self._execute_user_call(
            lambda client: client.like(tweet_id=tweet_id, user_auth=False)
        )
        return {
            "tweet_id": tweet_id,
            "liked": bool(response.data["liked"]),
        }

    def retweet(self, tweet_id: str) -> dict[str, Any]:
        response = self._execute_user_call(
            lambda client: client.retweet(tweet_id=tweet_id, user_auth=False)
        )
        return {
            "tweet_id": tweet_id,
            "retweeted": bool(response.data["retweeted"]),
        }

    def follow_user(
        self, user_id: str | None = None, username: str | None = None
    ) -> dict[str, Any]:
        if not user_id and not username:
            raise RuntimeError("Either user_id or username is required.")

        resolved_user_id = user_id
        if username and not user_id:
            profile = self.get_user(username=username)
            resolved_user_id = profile["user"]["id"]

        response = self._execute_user_call(
            lambda client: client.follow_user(
                target_user_id=resolved_user_id, user_auth=False
            )
        )
        return {
            "user_id": str(resolved_user_id),
            "username": username,
            "following": bool(response.data["following"]),
        }

    def search_tweets(
        self, query: str, limit: int = 20, recent: bool = False, lang: str = "en"
    ) -> dict[str, Any]:
        client = self._get_bearer_client()
        if client is None:
            raise RuntimeError("X_BEARER_TOKEN is not configured on skill-server.")

        requested_limit = limit
        search_query = f"{query} lang:{lang}" if lang else query
        tweet_fields = ["created_at", "public_metrics", "author_id"]

        scope_used = "recent" if recent else "all"
        fallback_reason = None

        if recent:
            fetch_limit = max(10, min(limit, 100))
            response = client.search_recent_tweets(
                query=search_query,
                max_results=fetch_limit,
                tweet_fields=tweet_fields,
            )
        else:
            try:
                fetch_limit = max(10, min(limit, 500))
                response = client.search_all_tweets(
                    query=search_query,
                    max_results=fetch_limit,
                    tweet_fields=tweet_fields,
                )
            except tweepy.TweepyException as exc:
                if not self._is_full_archive_access_error(exc):
                    raise
                logger.info(
                    "search_all_tweets unavailable; falling back to recent search: %s",
                    exc,
                )
                fetch_limit = max(10, min(limit, 100))
                response = client.search_recent_tweets(
                    query=search_query,
                    max_results=fetch_limit,
                    tweet_fields=tweet_fields,
                )
                scope_used = "recent"
                fallback_reason = str(exc)

        tweets = [_tweet_to_dict(tweet) for tweet in response.data or []][:requested_limit]
        return {
            "query": query,
            "count": len(tweets),
            "requested_limit": requested_limit,
            "tweets": tweets,
            "next_token": response.meta.get("next_token") if response.meta else None,
            "scope_requested": "recent" if recent else "all",
            "scope_used": scope_used,
            "fallback_reason": fallback_reason,
        }

    def get_timeline(
        self,
        limit: int = 10,
        include_retweets: bool = False,
        exclude_retweets: bool = False,
    ) -> dict[str, Any]:
        tweet_fields = ["created_at", "public_metrics", "context_annotations"]
        response = self._execute_user_call(
            lambda client: client.get_home_timeline(
                max_results=limit,
                tweet_fields=tweet_fields,
                user_auth=False,
            )
        )

        tweets = [_tweet_to_dict(tweet) for tweet in response.data or []]
        if exclude_retweets:
            tweets = [tweet for tweet in tweets if not tweet["text"].startswith("RT @")]
        elif not include_retweets:
            tweets = tweets[:limit]

        return {
            "count": len(tweets),
            "requested_limit": limit,
            "tweets": tweets,
            "next_token": response.meta.get("next_token") if response.meta else None,
        }

    def get_mentions(
        self,
        limit: int = 20,
        since_id: str | None = None,
        until_id: str | None = None,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        authenticated_user = self._get_authenticated_user()
        requested_limit = limit
        fetch_limit = max(5, min(limit, 100))
        tweet_fields = ["created_at", "public_metrics", "author_id"]
        user_fields = [
            "created_at",
            "public_metrics",
            "description",
            "verified",
            "location",
        ]

        params: dict[str, Any] = {
            "max_results": fetch_limit,
            "expansions": ["author_id"],
            "tweet_fields": tweet_fields,
            "user_fields": user_fields,
            "user_auth": False,
        }
        if since_id:
            params["since_id"] = since_id
        if until_id:
            params["until_id"] = until_id
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = self._execute_user_call(
            lambda client: client.get_users_mentions(str(authenticated_user.id), **params)
        )

        includes = getattr(response, "includes", None) or {}
        author_map: dict[str, dict[str, Any]] = {}
        if isinstance(includes, dict):
            for user in includes.get("users", []):
                user_payload = _user_to_dict(user)
                user_id = user_payload.get("id")
                if user_id:
                    author_map[user_id] = user_payload

        mentions = [
            _tweet_to_dict(tweet, author_map=author_map) for tweet in (response.data or [])
        ][:requested_limit]

        return {
            "user": _user_to_dict(authenticated_user),
            "count": len(mentions),
            "requested_limit": requested_limit,
            "mentions": mentions,
            "next_token": response.meta.get("next_token") if response.meta else None,
            "previous_token": response.meta.get("previous_token") if response.meta else None,
            "since_id": since_id,
            "until_id": until_id,
        }

    def get_user(self, username: str | None = None, user_id: str | None = None) -> dict[str, Any]:
        if not username and not user_id:
            raise RuntimeError("Either username or user_id is required.")

        user_fields = [
            "created_at",
            "public_metrics",
            "description",
            "verified",
            "location",
        ]

        client = self._get_bearer_client()
        if client is None:
            result = self._execute_user_call(
                lambda fallback_client: fallback_client.get_user(
                    username=username,
                    id=user_id,
                    user_fields=user_fields,
                    user_auth=False,
                )
            )
        else:
            result = client.get_user(
                username=username,
                id=user_id,
                user_fields=user_fields,
            )

        return {"user": _user_to_dict(result.data)}

    def _get_authenticated_user(self) -> tweepy.User:
        user_fields = [
            "created_at",
            "public_metrics",
            "description",
            "verified",
            "location",
        ]
        result = self._execute_user_call(
            lambda client: client.get_me(
                user_fields=user_fields,
                user_auth=False,
            )
        )
        if result.data is None:
            raise RuntimeError("Failed to resolve the authenticated X user.")
        return result.data

    def _needs_refresh(self, state: XTokenState) -> bool:
        if not state.access_token:
            return True
        remaining = state.seconds_remaining()
        if remaining is None:
            return True
        return remaining <= self._settings.x_refresh_leeway_seconds

    def _get_bearer_client(self) -> tweepy.Client | None:
        if not self._settings.x_bearer_token:
            return None
        return tweepy.Client(self._settings.x_bearer_token)

    def _get_user_access_token(self) -> str:
        state = self._token_store.get()
        if not state.access_token:
            raise RuntimeError("X access token is not configured on skill-server.")
        return state.access_token

    def _get_user_client(self) -> tweepy.Client:
        return tweepy.Client(self._get_user_access_token())

    def _execute_user_call(self, callback: Callable[[tweepy.Client], Any]) -> Any:
        self.refresh_if_due()
        client = self._get_user_client()

        try:
            return callback(client)
        except tweepy.errors.Unauthorized:
            self.refresh_tokens(force=True)
            client = self._get_user_client()
            return callback(client)

    def _resolve_media_ids(
        self,
        media_files: list[dict[str, Any]],
        media_ids: list[str],
    ) -> list[str]:
        combined_ids = [media_id for media_id in media_ids if media_id]
        if media_files:
            combined_ids.extend(self._upload_media_files(media_files))
        if len(combined_ids) > 4:
            raise RuntimeError("X supports up to 4 attached images per post.")
        return combined_ids

    def _upload_media_files(self, media_files: list[dict[str, Any]]) -> list[str]:
        if not media_files:
            return []
        if len(media_files) > 4:
            raise RuntimeError("X supports up to 4 attached images per post.")

        self.refresh_if_due()
        media_ids: list[str] = []
        access_token = self._get_user_access_token()

        for file_info in media_files:
            content_type = self._normalize_media_content_type(
                file_info.get("content_type"),
                file_info["filename"],
            )
            if content_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
                raise RuntimeError(
                    f"Unsupported media type for X upload: {content_type}. "
                    "Supported types are JPEG, PNG, GIF, and WEBP."
                )

            data = file_info["data"]
            self._validate_image_upload(data, content_type, file_info["filename"])

            response = self._post_media_upload(
                access_token=access_token,
                filename=file_info["filename"],
                data=data,
                content_type=content_type,
            )
            if response.status_code == 401:
                self.refresh_tokens(force=True)
                access_token = self._get_user_access_token()
                response = self._post_media_upload(
                    access_token=access_token,
                    filename=file_info["filename"],
                    data=data,
                    content_type=content_type,
                )

            self._raise_for_upload_error(response, file_info["filename"])
            payload = response.json()
            media_id = (
                payload.get("data", {}).get("id")
                or payload.get("data", {}).get("media_id")
                or payload.get("media_id")
            )
            if not media_id:
                raise RuntimeError("X media upload succeeded without returning a media id.")
            media_ids.append(str(media_id))

        return media_ids

    def _post_media_upload(
        self,
        *,
        access_token: str,
        filename: str,
        data: bytes,
        content_type: str,
    ) -> httpx.Response:
        return httpx.post(
            "https://api.x.com/2/media/upload",
            headers={"Authorization": f"Bearer {access_token}"},
            data={
                "media_category": "tweet_gif" if content_type == "image/gif" else "tweet_image",
                "media_type": content_type,
            },
            files={"media": (filename, data, content_type)},
            timeout=self._settings.request_timeout_seconds,
        )

    def _raise_for_upload_error(self, response: httpx.Response, filename: str) -> None:
        if not response.is_error:
            return

        detail: Any = response.text
        try:
            payload = response.json()
            detail = payload.get("detail") or payload
        except Exception:
            payload = None

        logger.warning(
            "X media upload failed for %s: status=%s body=%s",
            filename,
            response.status_code,
            response.text,
        )
        raise RuntimeError(
            f"X media upload failed for {filename}: {detail if isinstance(detail, str) else payload or detail}"
        )

    def _normalize_media_content_type(
        self, content_type: str | None, filename: str
    ) -> str:
        if content_type:
            normalized = content_type.lower()
            if normalized == "image/jpg":
                return "image/jpeg"
            return normalized
        guessed, _ = mimetypes.guess_type(filename)
        return (guessed or "application/octet-stream").lower()

    def _validate_image_upload(self, data: bytes, content_type: str, filename: str) -> None:
        max_bytes = 15 * 1024 * 1024 if content_type == "image/gif" else 5 * 1024 * 1024
        if len(data) > max_bytes:
            raise RuntimeError(f"{filename} exceeds the X upload size limit for {content_type}.")
        try:
            with PILImage.open(BytesIO(data)) as image:
                image.verify()
        except Exception as exc:
            raise RuntimeError(f"{filename} is not a valid image for X upload: {exc}") from exc

    def _is_full_archive_access_error(self, exc: tweepy.TweepyException) -> bool:
        message = str(exc).lower()
        return "elevated api access" in message or "search_all_tweets" in message
