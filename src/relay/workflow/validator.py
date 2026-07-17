"""DAG verification rules checking for cycles, missing step dependencies, and duplicate names."""

from relay.domain.workflow import WorkflowAST


class WorkflowValidationError(Exception):
    """Raised when an AST contains structural violations like cycles or missing references."""
    pass


def validate_workflow_ast(ast: WorkflowAST, known_steps: set[str] | None = None) -> None:
    """Perform comprehensive structural check on a parsed `WorkflowAST`.

    Raises:
        WorkflowValidationError: If duplicates, missing targets, or cycles are found.
    """
    if not ast.steps:
        raise WorkflowValidationError(f"Workflow '{ast.name}' contains no steps.")

    step_names = set()
    for step in ast.steps:
        if step.name in step_names:
            raise WorkflowValidationError(f"Duplicate step name defined: '{step.name}'")
        step_names.add(step.name)

        if known_steps is not None and step.uses not in known_steps:
            raise WorkflowValidationError(
                f"Step '{step.name}' references unregistered plugin step: '{step.uses}'"
            )

    # Verify that every `depends_on` target actually exists in step_names
    for step in ast.steps:
        for dep in step.depends_on:
            if dep not in step_names:
                raise WorkflowValidationError(
                    f"Step '{step.name}' depends on non-existent step: '{dep}'"
                )
            if dep == step.name:
                raise WorkflowValidationError(f"Step '{step.name}' cannot depend on itself.")

    # Cycle detection via Kahn's topological sort algorithm
    in_degree = {name: 0 for name in step_names}
    adj = {name: [] for name in step_names}

    for step in ast.steps:
        for dep in step.depends_on:
            adj[dep].append(step.name)
            in_degree[step.name] += 1

    queue = [name for name, deg in in_degree.items() if deg == 0]
    visited_count = 0

    while queue:
        curr = queue.pop(0)
        visited_count += 1
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if visited_count < len(step_names):
        raise WorkflowValidationError(
            f"Cyclic dependency detected in workflow '{ast.name}' DAG. Check depends_on references."
        )
