"""Playwright wrapper implementing `IBrowserDriver`."""

from typing import Any
from playwright.async_api import Page, BrowserContext
from relay.contracts.browser import IBrowserDriver


class PlaywrightDriver(IBrowserDriver):
    """Isolated browser page driver backed by Playwright."""

    def __init__(self, page: Page, context: BrowserContext):
        self.page = page
        self.context = context
        self._closed = False

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> Any:
        if self._closed:
            raise RuntimeError("Cannot navigate closed PlaywrightDriver.")
        return await self.page.goto(url, wait_until=wait_until)

    async def get_content(self) -> str:
        if self._closed:
            raise RuntimeError("Cannot get content from closed PlaywrightDriver.")
        return await self.page.content()

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self.page.close()
