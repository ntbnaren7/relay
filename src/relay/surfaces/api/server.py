"""FastAPI server application exposing REST endpoints and SSE streams for Relay."""

import asyncio
import os
from pathlib import Path
import uuid
from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from relay.adapters.browser.manager import PlaywrightManager
from relay.adapters.secrets.vault import LocalVault
from relay.adapters.storage.artifact_store import LocalArtifactStore
from relay.adapters.storage.repository import SQLRepository
from relay.domain.artifact import Artifact, ArtifactType
from relay.engine.event_bus import EventBus
from relay.engine.orchestrator import Orchestrator
from relay.engine.plugin_registry import PluginRegistry
from relay.surfaces.api.models import (
    JobRunResponse,
    JobStatusResponse,
    StepHistoryItem,
    WorkflowRunRequest,
)
from relay.surfaces.api.sse import SSEBroadcaster
from relay.workflow.compiler import compile_workflow
from relay.workflow.parser import parse_workflow_file, parse_workflow_string

app = FastAPI(
    title="Relay Workflow Engine API",
    description="Omnichannel REST and SSE server for controlling local-first Relay automation workflows.",
    version="0.1.0",
)

# Shared singleton dependencies across API requests
event_bus = EventBus()
sse_broadcaster = SSEBroadcaster(event_bus)
plugin_registry = PluginRegistry()

# Initialize core built-in plugins
import plugins.instagram.plugin
import plugins.youtube.plugin
import plugins.common.plugin
plugins.instagram.plugin.InstagramPlugin()
plugins.youtube.plugin.YouTubePlugin()
plugins.common.plugin.CommonPlugin()
plugin_registry.discover_from_decorators()

# Infrastructure dependencies (defaults can be configured via environment variables)
DB_URL = os.environ.get("RELAY_DB_URL", "sqlite+aiosqlite:///relay_state.db")
ARTIFACTS_DIR = Path(os.environ.get("RELAY_ARTIFACTS_DIR", "./artifacts"))

repository = SQLRepository(db_url=DB_URL)
artifact_store = LocalArtifactStore(base_dir=ARTIFACTS_DIR)
browser_manager = PlaywrightManager()
vault = LocalVault()

orchestrator = Orchestrator(
    event_bus=event_bus,
    plugin_registry=plugin_registry,
    repository=repository,
    artifact_store=artifact_store,
    browser_manager=browser_manager,
    vault=vault,
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database tables on server startup."""
    await repository.init_db()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanly shut down active browser instances and database connections."""
    await browser_manager.shutdown_all()
    await repository.close()


@app.post("/api/v1/jobs/run", response_model=JobRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job(req: WorkflowRunRequest, background_tasks: BackgroundTasks) -> JobRunResponse:
    """Compile and asynchronously launch a workflow job."""
    if not req.workflow_yaml and not req.workflow_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'workflow_yaml' or 'workflow_path'.",
        )

    try:
        if req.workflow_yaml:
            ast = parse_workflow_string(req.workflow_yaml)
        else:
            ast = parse_workflow_file(req.workflow_path)
        dag = compile_workflow(ast)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Workflow compilation error: {e}",
        )

    job_id = req.job_id or f"job_{uuid.uuid4().hex[:8]}"

    # Launch execution in background task
    background_tasks.add_task(
        orchestrator.run_workflow,
        dag=dag,
        job_id=job_id,
        variable_overrides=req.variables,
        account_ids=req.account_ids,
    )

    return JobRunResponse(job_id=job_id, workflow_name=dag.name, status="SUBMITTED")


@app.get("/api/v1/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Fetch current status and step history for a submitted job."""
    job = await repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found.")

    steps = await repository.list_steps(job_id)
    history = [
        StepHistoryItem(
            step_name=s.step_name,
            status=s.status,
            duration_seconds=s.duration_seconds,
            error_message=s.error_message,
        )
        for s in steps
    ]

    return JobStatusResponse(
        job_id=job.job_id,
        workflow_name=job.workflow_name,
        status=job.status,
        error_message=job.error_message,
        steps=history,
    )


@app.get("/api/v1/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Stream live execution events (SSE) for a specific job ID."""
    return StreamingResponse(
        sse_broadcaster.stream_events(target_job_id=job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/v1/events")
async def stream_all_events() -> StreamingResponse:
    """Stream live execution events (SSE) across all active workflow jobs."""
    return StreamingResponse(
        sse_broadcaster.stream_events(target_job_id=None),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/v1/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str, name: str = "artifact.dat") -> StreamingResponse:
    """Download a stored binary artifact stream."""
    dummy_art = Artifact(id=artifact_id, artifact_type=ArtifactType.FILE, name=name)
    try:
        stream = artifact_store.resolve(dummy_art)
        return StreamingResponse(
            stream,
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Artifact not found: {e}")
