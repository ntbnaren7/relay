"""Playwright manager pooling browser processes and leasing isolated profile contexts (`IBrowserManager`)."""

import asyncio
from pathlib import Path
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright
from relay.contracts.browser import IBrowserDriver, IBrowserManager
from relay.adapters.browser.driver import PlaywrightDriver
from relay.adapters.browser.anti_detect import apply_stealth_scripts, get_random_user_agent
from relay.adapters.browser.session import SessionStorageManager


class PlaywrightManager(IBrowserManager):
    """Manages lifecycle of Playwright engine, browser processes, and isolated profile contexts."""

    def __init__(self, profiles_dir: Path | str = Path.home() / ".relay" / "profiles"):
        self.session_manager = SessionStorageManager(profiles_dir)
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()

    async def _ensure_browser(self, headless: bool = True) -> Browser:
        async with self._lock:
            if not self._playwright:
                self._playwright = await async_playwright().start()
            if not self._browser or not self._browser.is_connected():
                self._browser = await self._playwright.chromium.launch(
                    headless=headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
        return self._browser

    async def get_driver(
        self,
        profile_name: str = "default",
        headless: bool = True,
        proxy_url: str | None = None,
    ) -> IBrowserDriver:
        """Lease an isolated driver with anti-detect scripts and profile cookies."""
        browser = await self._ensure_browser(headless=headless)

        async with self._lock:
            if profile_name in self._contexts:
                context = self._contexts[profile_name]
            else:
                state_path = self.session_manager.get_state_path(profile_name)
                context_args = {
                    "user_agent": get_random_user_agent(),
                    "viewport": {"width": 1280, "height": 720},
                }
                if proxy_url:
                    context_args["proxy"] = {"server": proxy_url}
                if state_path.exists():
                    context_args["storage_state"] = state_path

                context = await browser.new_context(**context_args)
                await apply_stealth_scripts(context)
                self._contexts[profile_name] = context

        page = await context.new_page()
        return PlaywrightDriver(page, context)

    async def save_profile(self, profile_name: str) -> Path | None:
        """Persist active profile cookies and session tokens."""
        if profile_name in self._contexts:
            return await self.session_manager.save_context_state(self._contexts[profile_name], profile_name)
        return None

    async def close_all(self) -> None:
        """Terminate all active browser contexts and shut down Playwright."""
        async with self._lock:
            for name, context in list(self._contexts.items()):
                try:
                    await context.close()
                except Exception:
                    pass
            self._contexts.clear()

            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
