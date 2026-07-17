"""End-to-end verification test of the Instagram -> FFmpeg -> YouTube Studio pipeline."""

import pytest
from pathlib import Path
from relay.adapters.browser.manager import PlaywrightManager
from relay.adapters.secrets.vault import LocalVault
from relay.adapters.storage.artifact_store import LocalArtifactStore
from relay.adapters.storage.repository import SQLRepository
from relay.domain.events import JobCompleted, JobStarted, StepCompleted
from relay.engine.event_bus import EventBus
from relay.engine.orchestrator import Orchestrator
from relay.engine.plugin_registry import PluginRegistry
from relay.workflow.compiler import compile_workflow
from relay.workflow.parser import parse_workflow_string

# Complete YAML definition of the omnichannel automation pipeline
INSTAGRAM_TO_YOUTUBE_YAML = """
version: "1.0"
name: "instagram_to_youtube_studio"
description: "Download reel, transcode via FFmpeg, extract metadata, upload to YouTube, and notify."
variables:
  target_url: "https://www.instagram.com/reel/C1234567890/"
  privacy_status: "unlisted"
  notification_msg: "Reel successfully published to YouTube Studio."

steps:
  - name: "download_reel"
    uses: "instagram.download"
    with:
      url: "{{ target_url }}"

  - name: "extract_meta"
    uses: "instagram.extract_metadata"
    with:
      url: "{{ target_url }}"

  - name: "transcode_video"
    uses: "common.ffmpeg"
    depends_on: ["download_reel"]
    with:
      codec: "copy"
      output_name: "final_reel.mp4"

  - name: "upload_to_youtube"
    uses: "youtube.upload"
    depends_on: ["transcode_video", "extract_meta"]
    with:
      privacy: "{{ privacy_status }}"
      profile: "main_channel"

  - name: "send_notification"
    uses: "common.notify"
    depends_on: ["upload_to_youtube"]
    with:
      message: "{{ notification_msg }}"
"""


@pytest.mark.asyncio
async def test_e2e_instagram_to_youtube_pipeline(tmp_path: Path):
    # 1. Parse and compile workflow DAG
    ast = parse_workflow_string(INSTAGRAM_TO_YOUTUBE_YAML)
    dag = compile_workflow(ast)

    assert dag.name == "instagram_to_youtube_studio"
    assert len(dag.nodes) == 5
    # Check layer structure:
    # Layer 0: download_reel, extract_meta (no deps, run in parallel)
    # Layer 1: transcode_video (depends on download_reel)
    # Layer 2: upload_to_youtube (depends on transcode_video, extract_meta)
    # Layer 3: send_notification (depends on upload_to_youtube)
    assert len(dag.execution_layers) == 4
    assert set(dag.execution_layers[0]) == {"download_reel", "extract_meta"}
    assert set(dag.execution_layers[1]) == {"transcode_video"}
    assert set(dag.execution_layers[2]) == {"upload_to_youtube"}
    assert set(dag.execution_layers[3]) == {"send_notification"}

    # 2. Setup plugins and infrastructure
    import plugins.instagram.plugin
    import plugins.youtube.plugin
    import plugins.common.plugin
    plugins.instagram.plugin.InstagramPlugin()
    plugins.youtube.plugin.YouTubePlugin()
    plugins.common.plugin.CommonPlugin()

    registry = PluginRegistry()
    registry.discover_from_decorators()

    event_bus = EventBus()
    db_path = tmp_path / "e2e_state.db"
    repo = SQLRepository(db_url=f"sqlite+aiosqlite:///{db_path}")
    await repo.init_db()

    store = LocalArtifactStore(base_dir=tmp_path / "artifacts")
    browser_mgr = PlaywrightManager()
    vault = LocalVault()

    # Track lifecycle events
    completed_steps = []
    async def _on_step_done(e: StepCompleted):
        completed_steps.append(e.step_name)
    event_bus.subscribe("step.completed", _on_step_done)

    orchestrator = Orchestrator(
        event_bus=event_bus,
        plugin_registry=registry,
        repository=repo,
        artifact_store=store,
        browser_manager=browser_mgr,
        vault=vault,
    )

    job_id = "e2e-run-001"
    try:
        # 3. Execute workflow
        job_ctx = await orchestrator.run_workflow(dag=dag, job_id=job_id)

        # 4. Verify in-memory job context accumulation
        assert job_ctx.job_id == job_id
        assert "download_reel" in job_ctx.artifacts
        assert "extract_meta" in job_ctx.artifacts
        assert "transcode_video" in job_ctx.artifacts
        assert "upload_to_youtube" in job_ctx.artifacts

        assert set(completed_steps) == {
            "download_reel",
            "extract_meta",
            "transcode_video",
            "upload_to_youtube",
            "send_notification",
        }

        # 5. Verify database records
        job_record = await repo.get_job(job_id)
        assert job_record is not None
        assert job_record.status == "SUCCESS"

        steps_records = await repo.list_steps(job_id)
        assert len(steps_records) == 5
        for s in steps_records:
            assert s.status == "SUCCESS"

    finally:
        await browser_mgr.shutdown_all()
        await repo.close()
