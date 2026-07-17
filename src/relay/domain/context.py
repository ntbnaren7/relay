"""Execution context domain models passed between steps during workflow runs."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from relay.domain.artifact import Artifact


class StepContext(BaseModel):
    """Context object provided to a Step during its execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str = Field(..., description="Unique ID of the parent job execution.")
    workflow_name: str = Field(..., description="Name of the workflow executing.")
    step_name: str = Field(..., description="Unique identifier/name of this step.")
    config: dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters provided to the step (`with` clause)."
    )
    inputs: list[Artifact] = Field(
        default_factory=list, description="Input artifacts provided to this step."
    )
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Workflow configuration variables and parameters."
    )
    account_ids: dict[str, str] = Field(
        default_factory=dict, description="Mapping of platform name to active account profile ID."
    )
    scratch_data: dict[str, Any] = Field(
        default_factory=dict, description="Temporary scratch state across subroutines."
    )
    event_bus: Any = Field(default=None, description="Event bus to publish step progress and logs.")
    storage: Any = Field(default=None, description="Artifact store for saving and resolving binary/memory payloads.")
    browser: Any = Field(default=None, description="Optional browser manager/session provider if requested.")
    vault: Any = Field(default=None, description="Optional secret storage vault.")

    def get_input_by_name(self, name: str) -> Artifact | None:
        """Find an input artifact by its name."""
        for art in self.inputs:
            if art.name == name:
                return art
        return None

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Safely retrieve a variable value."""
        return self.variables.get(key, default)


class JobContext(BaseModel):
    """Global execution context and state accumulator for an entire DAG run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str = Field(..., description="Unique execution instance identifier.")
    workflow_name: str = Field(..., description="Name of the workflow executing.")
    variables: dict[str, Any] = Field(default_factory=dict)
    account_ids: dict[str, str] = Field(default_factory=dict)
    artifacts: dict[str, list[Artifact]] = Field(
        default_factory=dict,
        description="Accumulated output artifacts mapped by step_name.",
    )

    def add_step_artifacts(self, step_name: str, artifacts: list[Artifact]) -> None:
        """Register newly generated artifacts produced by a completed step."""
        if step_name not in self.artifacts:
            self.artifacts[step_name] = []
        self.artifacts[step_name].extend(artifacts)
