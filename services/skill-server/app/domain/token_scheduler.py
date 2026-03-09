import asyncio
import logging

from app.clients.twitter import TwitterService
from app.config import Settings


logger = logging.getLogger(__name__)


class TokenScheduler:
    def __init__(self, twitter_service: TwitterService, settings: Settings):
        self._twitter_service = twitter_service
        self._settings = settings
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    def enabled(self) -> bool:
        return self._twitter_service.can_refresh()

    async def start(self) -> None:
        if not self.enabled():
            logger.info("X token scheduler disabled; refresh credentials are not configured")
            return
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="x-token-scheduler")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task

    async def _run(self) -> None:
        await asyncio.to_thread(self._twitter_service.refresh_if_due)
        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._settings.x_refresh_check_interval_seconds,
                )
            except asyncio.TimeoutError:
                try:
                    await asyncio.to_thread(self._twitter_service.refresh_if_due)
                except Exception:
                    logger.exception("Scheduled X token refresh failed")
