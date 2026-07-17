"""Browser automation module (`automation/browser.py`).

Provides isolated Playwright browser contexts, anti-detect stealth scripts,
profile session management, and a clean driver interface.
"""

import asyncio
import random
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

USER_AGENTS = [
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
"""


def get_random_user_agent() -> str:
    """Select a randomized modern desktop user-agent."""
    return random.choice(USER_AGENTS)


async def apply_stealth_scripts(context: BrowserContext) -> None:
    """Inject anti-bot evasion scripts into all pages spawned by this browser context."""
    await context.add_init_script(STEALTH_INIT_SCRIPT)


class SessionStorageManager:
    """Loads/saves browser cookies to `~/.relay/profiles/<profile_name>/storage_state.json`."""

    def __init__(self, profiles_dir: Path | str | None = None):
        if profiles_dir is None:
            profiles_dir = Path.home() / ".relay" / "profiles"
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def get_state_path(self, profile_name: str) -> Path:
        profile_dir = self.profiles_dir / profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir / "storage_state.json"

    def state_exists(self, profile_name: str) -> bool:
        return self.get_state_path(profile_name).exists()

    async def save_context_state(self, context: BrowserContext, profile_name: str) -> Path:
        """Export state from an active context to disk."""
        path = self.get_state_path(profile_name)
        await context.storage_state(path=path)
        return path


class BrowserDriver:
    """Clean, isolated browser page and context wrapper."""

    def __init__(self, page: Page, context: BrowserContext):
        self.page = page
        self.context = context
        self._closed = False

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> Any:
        if self._closed:
            raise RuntimeError("Cannot navigate closed BrowserDriver.")
        return await self.page.goto(url, wait_until=wait_until)

    async def get_content(self) -> str:
        if self._closed:
            raise RuntimeError("Cannot get content from closed BrowserDriver.")
        return await self.page.content()

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self.page.close()


class PlaywrightManager:
    """Manages Playwright engine, browser processes, and isolated profile contexts."""

    def __init__(self, profiles_dir: Path | str | None = None):
        if profiles_dir is None:
            profiles_dir = Path.home() / ".relay" / "profiles"
        self.session_manager = SessionStorageManager(profiles_dir)
        self._playwright: Playwright | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()

    async def get_driver(
        self,
        profile_name: str = "default",
        headless: bool = True,
        proxy_url: str | None = None,
    ) -> BrowserDriver:
        """Lease an isolated driver with anti-detect scripts and profile cookies."""
        async with self._lock:
            if not self._playwright:
                self._playwright = await async_playwright().start()

            if profile_name in self._contexts:
                context = self._contexts[profile_name]
            else:
                user_data_dir = (
                    self.session_manager.profiles_dir / f"{profile_name}_chrome_data"
                )
                user_data_dir.mkdir(parents=True, exist_ok=True)
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                ]
                context_args: dict[str, Any] = {
                    "user_data_dir": user_data_dir,
                    "headless": headless,
                    "args": launch_args,
                    "viewport": {"width": 1280, "height": 720},
                }
                if proxy_url:
                    context_args["proxy"] = {"server": proxy_url}

                try:
                    context = await (
                        self._playwright.chromium.launch_persistent_context(
                            channel="chrome",
                            **context_args,
                        )
                    )
                except Exception:
                    context = await (
                        self._playwright.chromium.launch_persistent_context(
                            **context_args,
                        )
                    )

                await apply_stealth_scripts(context)
                self._contexts[profile_name] = context

        pages = context.pages
        page = pages[0] if pages else await context.new_page()
        return BrowserDriver(page, context)

    async def save_profile(self, profile_name: str) -> Path | None:
        """Persist active profile cookies and session tokens."""
        if profile_name in self._contexts:
            context = self._contexts[profile_name]
            return await self.session_manager.save_context_state(context, profile_name)
        return None

    async def close_all(self) -> None:
        """Terminate all active browser contexts and shut down Playwright."""
        async with self._lock:
            for _name, context in list(self._contexts.items()):
                try:
                    await context.close()
                except Exception:
                    pass
            self._contexts.clear()

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
