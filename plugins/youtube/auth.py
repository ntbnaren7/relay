"""YouTube Studio authentication checks."""

from relay.contracts.browser import IBrowserDriver


async def verify_youtube_studio_auth(driver: IBrowserDriver) -> bool:
    """Verify if the current browser profile has active credentials for YouTube Studio."""
    try:
        await driver.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        content = await driver.get_content()
        if "accounts.google.com/signin" in content or "Sign in" in content:
            return False
        return True
    except Exception:
        return False
