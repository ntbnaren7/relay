"""Instagram session authentication checks."""

from relay.contracts.browser import IBrowserDriver


async def verify_instagram_auth(driver: IBrowserDriver) -> bool:
    """Check if the browser driver is currently logged into an active Instagram session."""
    try:
        await driver.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        content = await driver.get_content()
        # Look for logged-in indicators vs login form
        if 'loginForm' in content or 'Log In' in content:
            return False
        return True
    except Exception:
        return False
