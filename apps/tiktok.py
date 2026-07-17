"""TikTok application connector (`apps/tiktok.py`).

Handles TikTok video extraction, metadata parsing, and upload helpers.
"""

from pathlib import Path
from typing import Any

from automation.downloader import download_media


async def download_tiktok_video(url: str, output_dir: Path | str) -> dict[str, Any]:
    """Download a TikTok video without watermark using `yt-dlp` (`automation.downloader`)."""
    return await download_media(url=url, output_dir=output_dir)
