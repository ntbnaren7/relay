"""Reddit application connector (`apps/reddit.py`).

Handles Reddit media post extraction and video downloading.
"""

from pathlib import Path
from typing import Any

from automation.downloader import download_media


async def download_reddit_video(url: str, output_dir: Path | str) -> dict[str, Any]:
    """Download media from a Reddit post using `yt-dlp` (`automation.downloader`)."""
    return await download_media(url=url, output_dir=output_dir)
