"""Anti-detection browser evasion scripts and realistic user-agent profiles."""

import random
from playwright.async_api import BrowserContext


# Common realistic user agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
window.chrome = {
    runtime: {}
};
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3]
});
"""


def get_random_user_agent() -> str:
    """Select a randomized modern desktop user-agent."""
    return random.choice(USER_AGENTS)


async def apply_stealth_scripts(context: BrowserContext) -> None:
    """Inject anti-bot evasion scripts into all pages spawned by this browser context."""
    await context.add_init_script(STEALTH_INIT_SCRIPT)
