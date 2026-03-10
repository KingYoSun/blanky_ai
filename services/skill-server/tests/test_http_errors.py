from app.utils.http_errors import (
    extract_httpx_status_code,
    extract_response_detail,
    extract_tweepy_detail,
    extract_tweepy_status_code,
)


class DummyResponse:
    def __init__(self, *, status_code=400, text="", json_payload=None, json_error=None):
        self.status_code = status_code
        self.text = text
        self._json_payload = json_payload
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_payload


class DummyTweepyError(Exception):
    def __init__(self, response=None, message="forbidden"):
        super().__init__(message)
        self.response = response


def test_extract_response_detail_prefers_detail_field():
    response = DummyResponse(json_payload={"detail": "write permission missing"})

    assert extract_response_detail(response) == "write permission missing"


def test_extract_response_detail_uses_errors_field():
    errors = [{"message": "You are not permitted to perform this action."}]
    response = DummyResponse(json_payload={"errors": errors})

    assert extract_response_detail(response) == errors


def test_extract_response_detail_falls_back_to_text():
    response = DummyResponse(text="403 Forbidden", json_error=ValueError("bad json"))

    assert extract_response_detail(response) == "403 Forbidden"


def test_extract_tweepy_status_code_uses_response_status():
    exc = DummyTweepyError(response=DummyResponse(status_code=403))

    assert extract_tweepy_status_code(exc) == 403


def test_extract_tweepy_detail_uses_response_payload():
    exc = DummyTweepyError(
        response=DummyResponse(json_payload={"detail": "You are not permitted to perform this action."}),
        message="403 Forbidden",
    )

    assert extract_tweepy_detail(exc) == "You are not permitted to perform this action."


def test_extract_httpx_status_code_uses_upstream_status():
    import httpx

    request = httpx.Request("POST", "https://api.x.com/2/tweets")
    response = httpx.Response(403, request=request, text="forbidden")
    exc = httpx.HTTPStatusError("403 Forbidden", request=request, response=response)

    assert extract_httpx_status_code(exc) == 403
