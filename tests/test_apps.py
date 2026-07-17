"""Unit tests for platform apps connectors (`apps/`)."""

from pathlib import Path

import pytest

from apps.instagram import download_reel, extract_metadata
from apps.tiktok import download_tiktok_video
from apps.youtube import upload_video_to_studio


@pytest.mark.asyncio
async def test_instagram_extract_metadata():
    meta = await extract_metadata("https://www.instagram.com/p/sample_id/")
    assert "sample_id" in meta["title"]
    assert meta["url"] == "https://www.instagram.com/p/sample_id/"


@pytest.mark.asyncio
async def test_instagram_download_reel(tmp_path: Path):
    res = await download_reel("https://www.instagram.com/p/sample_reel/", output_dir=tmp_path)
    assert res["file_path"].exists()


@pytest.mark.asyncio
async def test_youtube_studio_upload(tmp_path: Path):
    video = tmp_path / "my_video.mp4"
    video.write_bytes(b"X" * 500)
    res = await upload_video_to_studio(video, title="Test Video", description="Test Desc")
    # No browser_manager passed — expect placeholder status, not UPLOADED
    assert res["status"] == "NO_BROWSER_SESSION"
    assert res["video_id"].startswith("yt_")
    assert "https://youtu.be/" in res["url"]


@pytest.mark.asyncio
async def test_tiktok_download(tmp_path: Path):
    tk = await download_tiktok_video("https://tiktok.com/@user/video/123", output_dir=tmp_path)
    assert tk["file_path"].exists()
