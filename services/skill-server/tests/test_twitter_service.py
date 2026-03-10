from types import SimpleNamespace

from app.clients.twitter import TwitterService
from app.domain.credentials import XTokenState


class DummyTokenStore:
    def __init__(self, state: XTokenState):
        self._state = state

    def get(self) -> XTokenState:
        return self._state


def test_auth_status_includes_scope_and_token_type():
    settings = SimpleNamespace(
        x_client_key="client-key",
        x_client_secret="client-secret",
    )
    state = XTokenState(
        access_token="access-token",
        refresh_token="refresh-token",
        token_type="bearer",
        scope="tweet.write media.write",
    )
    service = TwitterService(settings, DummyTokenStore(state))

    status = service.auth_status()

    assert status["configured"] is True
    assert status["can_refresh"] is True
    assert status["token_type"] == "bearer"
    assert status["scope"] == "tweet.write media.write"
