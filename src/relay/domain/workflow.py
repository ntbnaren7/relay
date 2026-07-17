"""Abstract Syntax Tree (AST) representations of workflows parsed from definitions."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class StepAST(BaseModel):
    """AST node representing a declared step in a workflow definition."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Step identifier inside this workflow.")
    uses: str = Field(
        ..., description="Reference to the plugin/step implementation (e.g. 'instagram.download_reels')."
    )
    with_args: dict[str, Any] = Field(
        default_factory=dict, description="Configuration parameters provided to the step."
    )
    depends_on: list[str] = Field(
        default_factory=list, description="Explicit step names that must complete before this step."
    )
    retry_policy: dict[str, Any] | None = Field(
        default=None, description="Optional custom retry overrides (max_attempts, backoff_seconds)."
    )


class EdgeAST(BaseModel):
    """AST node representing a directed dependency link from source step to target step."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(..., description="Source step name.")
    target: str = Field(..., description="Target step name.")


class WorkflowAST(BaseModel):
    """Parsed Abstract Syntax Tree of a complete Relay workflow."""

    model_config = ConfigDict(frozen=True)

    version: str = Field(default="1.0", description="Workflow schema version.")
    name: str = Field(..., description="Human-readable workflow name.")
    description: str = Field(default="", description="Workflow purpose summary.")
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Global workflow variables and default values."
    )
    steps: list[StepAST] = Field(default_factory=list, description="List of declared steps.")

    def get_step_by_name(self, name: str) -> StepAST | None:
        """Look up a step definition node by its name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None
