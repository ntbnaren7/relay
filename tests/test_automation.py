"""Unit tests for automation modules (`automation/`)."""

from pathlib import Path

import pytest

from automation.browser import SessionStorageManager, get_random_user_agent
from automation.downloader import download_media, transcode_video
from automation.uploader import FileNotReadyError, format_progress_message, verify_file_for_upload


def test_user_agent_randomization():
    ua1 = get_random_user_agent()
    assert "Mozilla/5.0" in ua1


def test_session_storage_manager(tmp_profile_dir: Path):
    mgr = SessionStorageManager(tmp_profile_dir)
    path = mgr.get_state_path("test_user")
    assert path.name == "storage_state.json"
    assert not mgr.state_exists("test_user")


def test_format_progress_message():
    msg = format_progress_message("test.step", 50, 100)
    assert "[test.step] 50.0% (50/100 bytes)" in msg


def test_verify_file_for_upload(tmp_path: Path):
    dummy = tmp_path / "test.mp4"
    with pytest.raises(FileNotReadyError):
        verify_file_for_upload(dummy)

    dummy.write_bytes(b"A" * 200)
    verified = verify_file_for_upload(dummy, min_size_bytes=100)
    assert verified == dummy


@pytest.mark.asyncio
async def test_download_media_fallback(tmp_media_dir: Path):
    res = await download_media("https://instagram.com/p/mock123", output_dir=tmp_media_dir)
    assert res["file_path"].exists()
    assert "mock123" in str(res["file_path"]) or res["file_path"].name.startswith("reel_")


@pytest.mark.asyncio
async def test_transcode_video_fallback(tmp_media_dir: Path):
    input_file = tmp_media_dir / "input.mp4"
    input_file.write_bytes(b"MOCK_MP4_DATA")
    out_file = tmp_media_dir / "output.mp4"
    res = await transcode_video(input_file, out_file)
    assert res.exists()
