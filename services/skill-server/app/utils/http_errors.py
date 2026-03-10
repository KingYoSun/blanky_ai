from typing import Any

import httpx


def extract_response_detail(response: Any, fallback: str | None = None) -> Any:
    if response is None:
        return fallback or "Unknown error."

    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        return payload.get("detail") or payload.get("errors") or payload
    if payload is not None:
        return payload

    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    return fallback or "Unknown error."


def extract_tweepy_status_code(exc: Exception) -> int:
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return int(status_code) if status_code is not None else 400


def extract_tweepy_detail(exc: Exception) -> Any:
    return extract_response_detail(getattr(exc, "response", None), fallback=str(exc))


def extract_httpx_status_code(exc: httpx.HTTPStatusError) -> int:
    return exc.response.status_code
