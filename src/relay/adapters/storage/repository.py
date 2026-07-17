"""SQLAlchemy 2.0 async repository implementing `IRepository`."""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from relay.contracts.storage import IRepository
from relay.adapters.storage.models import JobRecord, StepRecord


class SQLRepository(IRepository):
    """Persistent database repository using async SQLAlchemy session factory."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def save_job(self, job_data: dict[str, Any]) -> str:
        job_id = job_data["job_id"]
        async with self.session_factory() as session:
            stmt = select(JobRecord).where(JobRecord.job_id == job_id).options(selectinload(JobRecord.steps))
            result = await session.execute(stmt)
            job_record = result.scalar_one_or_none()

            if not job_record:
                started_at = None
                if job_data.get("started_at"):
                    try:
                        started_at = datetime.fromisoformat(job_data["started_at"])
                    except ValueError:
                        started_at = datetime.now(timezone.utc)
                else:
                    started_at = datetime.now(timezone.utc)

                job_record = JobRecord(
                    job_id=job_id,
                    workflow_name=job_data.get("workflow_name", "unknown"),
                    status=job_data.get("status", "PENDING"),
                    total_steps=job_data.get("total_steps", 0),
                    started_at=started_at,
                    variables_json=job_data.get("variables", {}),
                )
                session.add(job_record)

            if "status" in job_data:
                job_record.status = job_data["status"]
            if "error_message" in job_data:
                job_record.error_message = job_data["error_message"]

            # Process step outcomes if provided
            steps_data = job_data.get("steps", {})
            for step_name, step_info in steps_data.items():
                step_stmt = select(StepRecord).where(
                    StepRecord.job_id == job_id, StepRecord.step_name == step_name
                )
                step_res = await session.execute(step_stmt)
                step_record = step_res.scalar_one_or_none()

                if not step_record:
                    step_record = StepRecord(
                        job_id=job_id,
                        step_name=step_name,
                        status=step_info.get("status", "PENDING"),
                        duration_seconds=step_info.get("duration_seconds", 0.0),
                        output_count=step_info.get("output_count", 0),
                        output_ids_json=step_info.get("output_ids", []),
                        error_message=step_info.get("error_message"),
                    )
                    session.add(step_record)
                else:
                    step_record.status = step_info.get("status", step_record.status)
                    step_record.duration_seconds = step_info.get("duration_seconds", step_record.duration_seconds)
                    step_record.output_count = step_info.get("output_count", step_record.output_count)
                    step_record.output_ids_json = step_info.get("output_ids", step_record.output_ids_json)
                    step_record.error_message = step_info.get("error_message", step_record.error_message)

            await session.commit()
            return job_id

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            stmt = select(JobRecord).where(JobRecord.job_id == job_id).options(selectinload(JobRecord.steps))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return None
            return job.to_dict()

    async def update_job_status(self, job_id: str, status: str, error_message: str | None = None) -> None:
        async with self.session_factory() as session:
            stmt = select(JobRecord).where(JobRecord.job_id == job_id).options(selectinload(JobRecord.steps))
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if job:
                job.status = status
                if error_message:
                    job.error_message = error_message
                if status in ("SUCCESS", "FAILED"):
                    job.completed_at = datetime.now(timezone.utc)
                await session.commit()
