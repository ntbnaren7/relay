"""Unit tests for direct workflow pipelines (`pipelines/`)."""

from pathlib import Path
from typing import Any

import pytest

from pipelines.custom import run_custom_pipeline
from pipelines.insta_to_youtube import run as run_insta_to_youtube
from pipelines.tiktok_to_shorts import run as run_tiktok_to_shorts


@pytest.mark.asyncio
async def test_pipeline_insta_to_youtube(tmp_path: Path):
    messages = []
    def _cb(msg: str) -> None:
        messages.append(msg)

    res = await run_insta_to_youtube(
        url="https://www.instagram.com/p/mock_pipeline/",
        output_dir=tmp_path,
        progress_callback=_cb,
    )
    assert res["status"] == "SUCCESS"
    assert res["youtube_video_id"].startswith("yt_")
    assert any("instagram.download" in m for m in messages)
    assert any("pipeline.completed" in m for m in messages)


@pytest.mark.asyncio
async def test_pipeline_tiktok_to_shorts(tmp_path: Path):
    res = await run_tiktok_to_shorts(
        url="https://tiktok.com/@creator/video/999",
        output_dir=tmp_path,
    )
    assert res["status"] == "SUCCESS"
    assert "https://youtu.be/" in res["youtube_url"]


@pytest.mark.asyncio
async def test_custom_pipeline():
    async def _dummy_job(x: int) -> dict[str, Any]:
        return {"status": "SUCCESS", "val": x * 2}

    res = await run_custom_pipeline(_dummy_job, 10)
    assert res["val"] == 20
