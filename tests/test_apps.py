"""Unit tests for platform apps connectors (`apps/`)."""

from pathlib import Path

import pytest

from apps.instagram import download_reel, extract_metadata
from apps.reddit import download_reddit_video
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
    assert res["status"] == "UPLOADED"
    assert res["video_id"].startswith("yt_")
    assert "https://youtu.be/" in res["url"]


@pytest.mark.asyncio
async def test_tiktok_and_reddit(tmp_path: Path):
    tk = await download_tiktok_video("https://tiktok.com/@user/video/123", output_dir=tmp_path)
    assert tk["file_path"].exists()

    rd = await download_reddit_video(
        "https://reddit.com/r/sub/comments/123/video", output_dir=tmp_path
    )
    assert rd["file_path"].exists()
