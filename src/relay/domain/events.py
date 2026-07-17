"""Strongly-typed domain events emitted by steps and orchestrators over the Event Bus."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Root event model for all EventBus lifecycle notifications."""

    event_type: str = Field(..., description="Unique discriminator string for event subscription.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event occurred.",
    )
    job_id: str | None = Field(default=None, description="Associated job ID if applicable.")


class JobStarted(BaseEvent):
    """Emitted when a workflow execution job begins."""

    event_type: str = "job.started"
    workflow_name: str = Field(...)
    total_steps: int = Field(...)


class JobCompleted(BaseEvent):
    """Emitted when all DAG steps complete successfully."""

    event_type: str = "job.completed"
    workflow_name: str = Field(...)
    duration_seconds: float = Field(...)


class JobFailed(BaseEvent):
    """Emitted when a job fails after exhausting retries."""

    event_type: str = "job.failed"
    workflow_name: str = Field(...)
    failed_step: str = Field(...)
    error_message: str = Field(...)


class StepStarted(BaseEvent):
    """Emitted when an atomic step begins execution."""

    event_type: str = "step.started"
    step_name: str = Field(...)


class ProgressUpdated(BaseEvent):
    """Emitted when a running step reports progress percentage or throughput metrics."""

    event_type: str = "step.progress"
    step_name: str = Field(...)
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    message: str = Field(default="")
    metrics: dict[str, Any] = Field(default_factory=dict)


class StepCompleted(BaseEvent):
    """Emitted when a step completes execution successfully."""

    event_type: str = "step.completed"
    step_name: str = Field(...)
    output_count: int = Field(default=0)
    duration_seconds: float = Field(...)


class StepFailed(BaseEvent):
    """Emitted when a step encounters an error during execution."""

    event_type: str = "step.failed"
    step_name: str = Field(...)
    error_message: str = Field(...)
    will_retry: bool = Field(default=False)
    attempt: int = Field(default=1)


class LogEvent(BaseEvent):
    """Emitted for structured diagnostic logs across steps."""

    event_type: str = "log.entry"
    level: str = Field(default="INFO")
    message: str = Field(...)
    context_data: dict[str, Any] = Field(default_factory=dict)
