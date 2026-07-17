"""Compiler converting validated `WorkflowAST` nodes into executable topological execution layers."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from relay.domain.workflow import StepAST, WorkflowAST
from relay.workflow.validator import validate_workflow_ast


class CompiledDAG(BaseModel):
    """An executable workflow graph organized into topological execution batches (layers)."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(...)
    version: str = Field(...)
    description: str = Field(...)
    variables: dict[str, Any] = Field(default_factory=dict)
    nodes: dict[str, StepAST] = Field(default_factory=dict)
    adjacency: dict[str, list[str]] = Field(
        default_factory=dict, description="Mapping of step_name to its direct dependent children."
    )
    reverse_adjacency: dict[str, list[str]] = Field(
        default_factory=dict, description="Mapping of step_name to its direct prerequisite parents."
    )
    execution_layers: list[list[str]] = Field(
        default_factory=list,
        description="Ordered list of concurrent execution layers. Steps in the same layer have no dependencies on each other and can run in parallel via `asyncio.gather`.",
    )


def compile_workflow(ast: WorkflowAST, known_steps: set[str] | None = None) -> CompiledDAG:
    """Validate and compile a `WorkflowAST` into a `CompiledDAG` with concurrent execution layers."""
    validate_workflow_ast(ast, known_steps=known_steps)

    nodes = {step.name: step for step in ast.steps}
    adj = {name: [] for name in nodes}
    rev_adj = {name: [] for name in nodes}
    in_degree = {name: 0 for name in nodes}

    for step in ast.steps:
        for dep in step.depends_on:
            adj[dep].append(step.name)
            rev_adj[step.name].append(dep)
            in_degree[step.name] += 1

    # Build concurrent execution layers (BFS level order via topological sort)
    execution_layers = []
    current_layer = [name for name, deg in in_degree.items() if deg == 0]

    while current_layer:
        execution_layers.append(sorted(current_layer))
        next_layer = []
        for name in current_layer:
            for child in adj[name]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_layer.append(child)
        current_layer = next_layer

    return CompiledDAG(
        name=ast.name,
        version=ast.version,
        description=ast.description,
        variables=ast.variables,
        nodes=nodes,
        adjacency=adj,
        reverse_adjacency=rev_adj,
        execution_layers=execution_layers,
    )
