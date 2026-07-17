"""Pipeline orchestrating Instagram reel extraction to YouTube Studio upload.

Flow:
1. Extract metadata and download media from Instagram (`apps.instagram`) using `yt-dlp`.
2. Optionally transcode or verify media (`automation.downloader`).
3. Upload media along with title and description to YouTube Studio (`apps.youtube`).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.instagram import download_reel, extract_metadata
from apps.youtube import upload_video_to_studio
from automation.browser import PlaywrightManager
from automation.downloader import transcode_video
from automation.media_utils import format_progress_message


async def run(
    url: str,
    output_dir: Path | str | None = None,
    profile_name: str = "default",
    privacy: str = "private",
    progress_callback: Callable[[str], None] | None = None,
    headless: bool = False,
) -> dict[str, Any]:
    """Execute the full Instagram to YouTube Studio pipeline."""
    if output_dir is None:
        output_dir = Path.home() / ".relay" / "media"
    def _notify(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    _notify("[instagram.download] Downloading reel...")
    meta = await extract_metadata(url)
    download_res = await download_reel(url, output_dir=output_dir)

    raw_path = download_res["file_path"]
    title = meta.get("title") or download_res.get("title", "Instagram Reel")
    description = meta.get("description") or download_res.get("description", f"Reel from {url}")

    _notify("[automation.transcode] Transcoding video...")
    # Ensure standard MP4 compatibility before Studio ingestion
    processed_path = raw_path.parent / f"processed_{raw_path.name}"
    try:
        final_path = await transcode_video(raw_path, processed_path)
    except Exception:
        final_path = raw_path

    _notify("[youtube.upload] Uploading to YouTube Studio...")
    browser_manager = PlaywrightManager()
    try:
        upload_res = await upload_video_to_studio(
            video_path=final_path,
            title=title,
            description=description,
            privacy=privacy,
            browser_manager=browser_manager,
            profile_name=profile_name,
            headless=headless,
        )
    finally:
        await browser_manager.close_all()

    _notify("[pipeline.completed] Done.")
    return {
        "status": "SUCCESS",
        "instagram_url": url,
        "title": title,
        "youtube_video_id": upload_res["video_id"],
        "youtube_url": upload_res["url"],
        "local_file": str(final_path),
    }
