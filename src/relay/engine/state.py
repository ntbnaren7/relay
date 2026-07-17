"""StateManager responsible for persisting job and step execution state checkpoints via `IRepository`."""

from datetime import datetime, timezone
from typing import Any
from relay.contracts.step import StepResult
from relay.contracts.storage import IRepository


class StateManager:
    """Checkpoints and tracks DAG execution progress across database storage."""

    def __init__(self, repository: IRepository):
        self.repo = repository

    async def init_job(self, job_id: str, workflow_name: str, total_steps: int) -> None:
        """Create initial job checkpoint record."""
        job_data = {
            "job_id": job_id,
            "workflow_name": workflow_name,
            "status": "RUNNING",
            "total_steps": total_steps,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps": {},
        }
        await self.repo.save_job(job_data)

    async def record_step_result(
        self,
        job_id: str,
        step_name: str,
        result: StepResult,
        duration_seconds: float,
    ) -> None:
        """Update job checkpoint with the outcome of a completed step."""
        job = await self.repo.get_job(job_id)
        if not job:
            return

        step_info = {
            "step_name": step_name,
            "status": result.status.value,
            "duration_seconds": duration_seconds,
            "output_count": len(result.output_artifacts),
            "output_ids": [art.id for art in result.output_artifacts],
            "error_message": result.error_message,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        if "steps" not in job:
            job["steps"] = {}
        job["steps"][step_name] = step_info

        await self.repo.save_job(job)

    async def complete_job(self, job_id: str, status: str, error_message: str | None = None) -> None:
        """Mark job execution as finished."""
        await self.repo.update_job_status(job_id, status, error_message)
