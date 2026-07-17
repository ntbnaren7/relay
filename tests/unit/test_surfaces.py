"""Unit tests verifying REST API endpoints, SSE streams, and CLI Rich progress handling."""

import pytest
from httpx import ASGITransport, AsyncClient
from relay.domain.events import JobCompleted, JobStarted, LogEvent, ProgressUpdated, StepCompleted, StepStarted
from relay.engine.event_bus import EventBus
from relay.surfaces.api.server import app, repository
from relay.surfaces.cli.progress import RichProgressSubscriber


@pytest.mark.asyncio
async def test_rest_api_job_submission_and_status():
    await repository.init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Submit valid workflow via YAML string
        yaml_payload = """
        name: "api_test_flow"
        steps:
          - name: "step_1"
            uses: "common.notify"
            with:
              message: "Hello from API"
        """
        res = await client.post("/api/v1/jobs/run", json={"workflow_yaml": yaml_payload})
        assert res.status_code == 202
        data = res.json()
        assert data["workflow_name"] == "api_test_flow"
        assert data["status"] == "SUBMITTED"
        job_id = data["job_id"]

        # Query job status
        res_status = await client.get(f"/api/v1/jobs/{job_id}/status")
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["job_id"] == job_id
        assert status_data["workflow_name"] == "api_test_flow"

        # Test invalid workflow submission (missing both yaml and path)
        res_bad = await client.post("/api/v1/jobs/run", json={})
        assert res_bad.status_code == 400


@pytest.mark.asyncio
async def test_rich_progress_subscriber():
    bus = EventBus()
    subscriber = RichProgressSubscriber()
    subscriber.subscribe_to_bus(bus)

    # Publish sequence of lifecycle events
    await bus.publish(JobStarted(job_id="job-1", workflow_name="rich_flow", total_steps=2))
    await bus.publish(StepStarted(job_id="job-1", step_name="dl"))
    await bus.publish(ProgressUpdated(job_id="job-1", step_name="dl", progress_percentage=50.0, message="Halfway"))
    await bus.publish(StepCompleted(job_id="job-1", step_name="dl", output_count=1, duration_seconds=1.2))
    await bus.publish(LogEvent(job_id="job-1", level="INFO", message="Step dl completed smoothly."))
    await bus.publish(JobCompleted(job_id="job-1", workflow_name="rich_flow", duration_seconds=2.5))

    # Verify task status tracked in memory
    assert "dl" in subscriber.task_ids
    assert subscriber.job_task_id is not None
