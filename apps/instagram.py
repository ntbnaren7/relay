"""Instagram application connector (`apps/instagram.py`).

Handles post/reel URL extraction, session authentication verification,
and media downloading via `automation.downloader`.
"""

import re
from pathlib import Path
from typing import Any

from automation.browser import BrowserDriver
from automation.downloader import download_media


async def verify_login(driver: BrowserDriver) -> bool:
    """Verify whether the active browser driver session is logged into Instagram."""
    try:
        await driver.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        content = await driver.get_content()
        if "loginForm" in content or "Log In" in content:
            return False
        return True
    except Exception:
        return False


async def extract_metadata(url: str, driver: BrowserDriver | None = None) -> dict[str, Any]:
    """Inspect an Instagram post or reel URL and extract title, description, and author."""
    if driver:
        try:
            await driver.goto(url, wait_until="domcontentloaded")
            content = await driver.get_content()
            video_match = re.search(r'property="og:video" content="([^"]+)"', content)
            title_match = re.search(r'property="og:title" content="([^"]+)"', content)
            desc_match = re.search(r'property="og:description" content="([^"]+)"', content)

            video_url = video_match.group(1).replace("&amp;", "&") if video_match else None
            title = title_match.group(1) if title_match else "Instagram Reel"
            description = desc_match.group(1) if desc_match else ""

            if video_url or title:
                return {
                    "video_url": video_url,
                    "title": title,
                    "description": description,
                    "author": "instagram_user",
                    "url": url,
                }
        except Exception:
            pass

    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "", url.split("?")[0].rstrip("/").split("/")[-1])
    return {
        "title": f"Instagram Reel {clean_id}",
        "description": f"Downloaded from {url}",
        "author": "instagram_creator",
        "url": url,
    }


async def download_reel(url: str, output_dir: Path | str) -> dict[str, Any]:
    """Download an Instagram reel video using `automation.downloader` (`yt-dlp`)."""
    return await download_media(url=url, output_dir=output_dir)
