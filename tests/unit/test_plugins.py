"""Unit tests verifying official Instagram, YouTube, and Common plugins."""

import pytest
from pathlib import Path
from relay.contracts.plugin import get_registered_steps
from relay.contracts.step import StepStatus
from relay.domain.artifact import Artifact, ArtifactType
from relay.domain.context import StepContext
from relay.engine.event_bus import EventBus
from relay.engine.plugin_registry import PluginRegistry
from relay.adapters.storage.artifact_store import LocalArtifactStore
from plugins.instagram.plugin import InstagramPlugin
from plugins.youtube.plugin import YouTubePlugin
from plugins.common.plugin import CommonPlugin


@pytest.fixture
def plugin_registry():
    # Instantiate plugins to ensure module import side-effects (@step) run cleanly
    InstagramPlugin()
    YouTubePlugin()
    CommonPlugin()
    registry = PluginRegistry()
    registry.discover_from_decorators()
    return registry


@pytest.mark.asyncio
async def test_plugin_registration(plugin_registry):
    steps = plugin_registry.list_steps()
    assert "instagram.download" in steps
    assert "instagram.extract_metadata" in steps
    assert "youtube.upload" in steps
    assert "common.ffmpeg" in steps
    assert "common.notify" in steps


@pytest.mark.asyncio
async def test_instagram_download_and_metadata_steps(plugin_registry, tmp_path: Path):
    store = LocalArtifactStore(base_dir=tmp_path)
    bus = EventBus()

    # Test download step
    dl_step_cls = plugin_registry.get_step("instagram.download")
    assert dl_step_cls is not None
    dl_step = dl_step_cls()

    ctx = StepContext(
        job_id="test-job-ig",
        workflow_name="test",
        step_name="dl",
        config={"url": "https://www.instagram.com/reel/C1234567890/"},
        inputs=[],
        event_bus=bus,
        storage=store,
    )
    assert await dl_step.validate_inputs(ctx) is True
    res_dl = await dl_step.execute(ctx)
    assert res_dl.status == StepStatus.SUCCESS
    assert len(res_dl.output_artifacts) == 1
    assert res_dl.output_artifacts[0].name == "instagram_video.mp4"

    # Test metadata step
    meta_step_cls = plugin_registry.get_step("instagram.extract_metadata")
    assert meta_step_cls is not None
    meta_step = meta_step_cls()

    ctx_meta = StepContext(
        job_id="test-job-ig",
        workflow_name="test",
        step_name="meta",
        config={"url": "https://www.instagram.com/reel/C1234567890/"},
        inputs=[],
        event_bus=bus,
        storage=store,
    )
    res_meta = await meta_step.execute(ctx_meta)
    assert res_meta.status == StepStatus.SUCCESS
    assert res_meta.output_artifacts[0].name == "metadata.json"


@pytest.mark.asyncio
async def test_ffmpeg_and_notify_steps(plugin_registry, tmp_path: Path):
    store = LocalArtifactStore(base_dir=tmp_path)
    bus = EventBus()

    # Create dummy video file artifact
    dummy_file = tmp_path / "raw.mp4"
    dummy_file.write_bytes(b"dummy video content")
    art = Artifact(id="a-vid", artifact_type=ArtifactType.FILE, name="raw.mp4", local_path=dummy_file)

    ff_cls = plugin_registry.get_step("common.ffmpeg")
    assert ff_cls is not None
    ff_step = ff_cls()

    ctx_ff = StepContext(
        job_id="test-job-ff",
        workflow_name="test",
        step_name="transcode",
        config={"codec": "copy", "output_name": "clean.mp4"},
        inputs=[art],
        event_bus=bus,
        storage=store,
    )
    assert await ff_step.validate_inputs(ctx_ff) is True
    res_ff = await ff_step.execute(ctx_ff)
    assert res_ff.status == StepStatus.SUCCESS
    assert res_ff.output_artifacts[0].name == "clean.mp4"

    # Notify step
    notif_cls = plugin_registry.get_step("common.notify")
    assert notif_cls is not None
    notif_step = notif_cls()

    ctx_notif = StepContext(
        job_id="test-job-ff",
        workflow_name="test",
        step_name="alert",
        config={"message": "Video transcoded successfully."},
        inputs=[],
        event_bus=bus,
        storage=store,
    )
    res_notif = await notif_step.execute(ctx_notif)
    assert res_notif.status == StepStatus.SUCCESS
    assert res_notif.metadata["notified"] is True


@pytest.mark.asyncio
async def test_youtube_upload_step(plugin_registry, tmp_path: Path):
    store = LocalArtifactStore(base_dir=tmp_path)
    bus = EventBus()

    vid_art = Artifact(id="v-yt", artifact_type=ArtifactType.FILE, name="video.mp4")
    meta_art = Artifact(id="m-yt", artifact_type=ArtifactType.MEMORY, name="metadata.json")

    yt_cls = plugin_registry.get_step("youtube.upload")
    assert yt_cls is not None
    yt_step = yt_cls()

    ctx = StepContext(
        job_id="test-job-yt",
        workflow_name="test",
        step_name="upload",
        config={"privacy": "unlisted", "profile": "channel_main"},
        inputs=[vid_art, meta_art],
        event_bus=bus,
        storage=store,
    )
    assert await yt_step.validate_inputs(ctx) is True
    res = await yt_step.execute(ctx)
    assert res.status == StepStatus.SUCCESS
    assert res.metadata["video_id"].startswith("yt_")
    assert res.metadata["privacy"] == "unlisted"
