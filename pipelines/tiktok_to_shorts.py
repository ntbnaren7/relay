"""Pipeline orchestrating TikTok video download to YouTube Shorts upload."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.tiktok import download_tiktok_video
from apps.youtube import upload_video_to_studio
from automation.browser import PlaywrightManager


async def run(
    url: str,
    output_dir: Path | str | None = None,
    profile_name: str = "default",
    privacy: str = "private",
    progress_callback: Callable[[str], None] | None = None,
    headless: bool = False,
) -> dict[str, Any]:
    """Execute TikTok to YouTube Shorts pipeline."""
    if output_dir is None:
        output_dir = Path.home() / ".relay" / "media"
    if progress_callback:
        progress_callback("[tiktok.download] Downloading video...")
    download_res = await download_tiktok_video(url, output_dir=output_dir)

    raw_path = download_res["file_path"]
    title = download_res.get("title", "TikTok Short")
    desc = download_res.get("description", f"Repurposed from {url}")

    if progress_callback:
        progress_callback("[youtube.upload] Uploading to Shorts...")

    browser_manager = PlaywrightManager()
    try:
        upload_res = await upload_video_to_studio(
            video_path=raw_path,
            title=title,
            description=desc,
            privacy=privacy,
            browser_manager=browser_manager,
            profile_name=profile_name,
            headless=headless,
        )
    finally:
        await browser_manager.close_all()

    if progress_callback:
        progress_callback("[pipeline.completed] Done.")

    return {
        "status": "SUCCESS",
        "tiktok_url": url,
        "youtube_url": upload_res["url"],
        "local_file": str(raw_path),
    }
