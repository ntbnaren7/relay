"""Core atomic execution contracts (`Step` and its execution status/result representations)."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from relay.domain.artifact import Artifact
from relay.domain.context import StepContext


class Permission(str, Enum):
    """Enums declaring security permissions required by a Step."""

    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    SECRETS = "secrets"


class StepStatus(str, Enum):
    """Execution status result of a Step."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class StepResult(BaseModel):
    """Result payload returned when a Step completes execution."""

    model_config = ConfigDict(frozen=False)

    status: StepStatus = Field(..., description="Final outcome status of the step.")
    output_artifacts: list[Artifact] = Field(
        default_factory=list, description="Artifacts produced during execution."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible metrics or summary data."
    )
    error_message: str | None = Field(
        default=None, description="Diagnostic error string if failed."
    )
    should_retry: bool = Field(
        default=False, description="Whether the engine should re-attempt execution."
    )


class Step(ABC):
    """Stable interface contract for all atomic execution units in Relay."""

    name: str
    description: str
    permissions: list[Permission] = []

    @abstractmethod
    async def execute(self, context: StepContext) -> StepResult:
        """Execute the step using inputs from the provided StepContext."""
        pass

    @abstractmethod
    async def validate_inputs(self, context: StepContext) -> bool:
        """Verify that required artifacts, variables, or accounts exist before running."""
        pass
