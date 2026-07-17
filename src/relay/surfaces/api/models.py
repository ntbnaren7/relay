"""Pydantic request and response schemas for Relay REST API endpoints."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class WorkflowRunRequest(BaseModel):
    """Request payload to submit and execute a workflow."""

    model_config = ConfigDict(frozen=True)

    workflow_yaml: str | None = Field(
        default=None, description="Raw YAML or JSON string definition of the workflow to run."
    )
    workflow_path: str | None = Field(
        default=None, description="Local filesystem path to the workflow definition file."
    )
    job_id: str | None = Field(
        default=None, description="Optional custom job execution identifier."
    )
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Variables and configuration overrides."
    )
    account_ids: dict[str, str] = Field(
        default_factory=dict, description="Platform account profile ID mappings."
    )


class JobRunResponse(BaseModel):
    """Immediate response payload returned upon successful workflow submission."""

    job_id: str
    workflow_name: str
    status: str = "SUBMITTED"


class StepHistoryItem(BaseModel):
    """Individual step execution record summary within a job status query."""

    step_name: str
    status: str
    duration_seconds: float | None = None
    error_message: str | None = None


class JobStatusResponse(BaseModel):
    """Detailed execution status report for a job run."""

    job_id: str
    workflow_name: str
    status: str
    error_message: str | None = None
    steps: list[StepHistoryItem] = Field(default_factory=list)
