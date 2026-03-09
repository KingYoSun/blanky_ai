#!/usr/bin/env python3
"""
Common helpers for X API v2 operations via the local skill-server.
"""

import os
import sys
from pathlib import Path
from typing import Any

import httpx


def get_http_client() -> httpx.Client:
    server_url = os.environ.get("LOCAL_SKILL_SERVER_URL", "").strip()
    socket_path = os.environ.get("LOCAL_SKILL_SERVER_SOCKET", "/run/skill-server/api.sock")
    timeout = float(os.environ.get("LOCAL_SKILL_SERVER_TIMEOUT", "30"))
    service_token = os.environ.get("SKILL_SERVER_SERVICE_TOKEN", "").strip()

    headers = {}
    if service_token:
        headers["x-skill-service-token"] = service_token

    if server_url:
        return httpx.Client(
            base_url=server_url.rstrip("/"),
            timeout=timeout,
            headers=headers,
        )

    transport = httpx.HTTPTransport(uds=socket_path)
    return httpx.Client(
        base_url="http://skill-server",
        timeout=timeout,
        headers=headers,
        transport=transport,
    )


def request_json(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: list[tuple[str, tuple[str, object, str]]] | None = None,
) -> dict[str, Any]:
    try:
        with get_http_client() as client:
            response = client.request(
                method,
                path,
                json=json_body,
                params=params,
                data=data,
                files=files,
            )
    except Exception as exc:
        print(f"❌ Error contacting local skill-server: {exc}", file=sys.stderr)
        sys.exit(1)

    if response.is_error:
        detail = response.text
        try:
            payload = response.json()
            detail = payload.get("detail", detail)
        except Exception:
            pass
        print(f"❌ Skill server error ({response.status_code}): {detail}", file=sys.stderr)
        sys.exit(1)

    return response.json()


def validate_tweet_text(text: str) -> bool:
    if len(text) > 280:
        print(f"Error: Tweet exceeds 280 characters ({len(text)} chars).", file=sys.stderr)
        return False
    return True


def print_tweet(tweet: dict[str, Any]) -> None:
    print(f"Tweet ID: {tweet['id']}")
    print(f"Text: {tweet['text']}")
    print(f"Created: {tweet.get('created_at')}")
    public_metrics = tweet.get("public_metrics") or {}
    if public_metrics:
        print(
            "Metrics: "
            f"{public_metrics.get('retweet_count', 0)} retweets, "
            f"{public_metrics.get('reply_count', 0)} replies, "
            f"{public_metrics.get('like_count', 0)} likes"
        )
    print("-" * 40)


def print_user(user: dict[str, Any]) -> None:
    public_metrics = user.get("public_metrics") or {}
    print(f"👤 User Profile: @{user['username']}")
    print("=" * 50)
    print(f"User ID: {user['id']}")
    print(f"Name: {user.get('name')}")
    print(f"Description: {user.get('description') or 'N/A'}")
    print(f"Location: {user.get('location') or 'N/A'}")
    print(f"Verified: {'Yes' if user.get('verified') else 'No'}")
    print(f"Created: {user.get('created_at')}")
    print("\nMetrics:")
    print(f"  Followers: {public_metrics.get('followers_count', 0):,}")
    print(f"  Following: {public_metrics.get('following_count', 0):,}")
    print(f"  Tweets: {public_metrics.get('tweet_count', 0):,}")
    print(f"  Listed: {public_metrics.get('listed_count', 0):,}")


def print_auth_status(payload: dict[str, Any]) -> None:
    print("🔐 X Auth Status")
    print("=" * 50)
    print(f"Configured: {'Yes' if payload.get('configured') else 'No'}")
    print(f"Can refresh: {'Yes' if payload.get('can_refresh') else 'No'}")
    print(f"Expires at: {payload.get('expires_at') or 'Unknown'}")
    print(f"Seconds remaining: {payload.get('seconds_remaining')}")
    print(f"Updated at: {payload.get('updated_at') or 'Unknown'}")
    print(f"Refresh failures: {payload.get('refresh_failures', 0)}")
    if payload.get("last_refresh_at"):
        print(f"Last refresh at: {payload['last_refresh_at']}")
    if payload.get("last_refresh_error"):
        print(f"Last refresh error: {payload['last_refresh_error']}")


def build_upload_files(paths: list[str]) -> tuple[list[tuple[str, tuple[str, object, str]]], list[object]]:
    import mimetypes

    upload_files: list[tuple[str, tuple[str, object, str]]] = []
    handles: list[object] = []

    for image_path in paths:
        path = Path(image_path)
        if not path.exists():
            print(f"❌ Media file not found: {image_path}", file=sys.stderr)
            sys.exit(1)
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        handle = path.open("rb")
        handles.append(handle)
        upload_files.append(("files", (path.name, handle, mime_type)))

    return upload_files, handles
