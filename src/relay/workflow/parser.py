"""Workflow DSL parser converting YAML/JSON definitions into `WorkflowAST` domain objects."""

import json
from pathlib import Path
import textwrap
from typing import Any
import yaml
from pydantic import ValidationError
from relay.domain.workflow import StepAST, WorkflowAST


class WorkflowParseError(Exception):
    """Raised when a workflow definition syntax or structure is invalid."""
    pass


def parse_workflow_dict(data: dict[str, Any]) -> WorkflowAST:
    """Parse a raw Python dictionary into a validated `WorkflowAST`."""
    try:
        # If steps don't have explicit `depends_on` and aren't root, we can optionally infer linear sequence
        raw_steps = data.get("steps", [])
        if isinstance(raw_steps, list):
            for i, step_dict in enumerate(raw_steps):
                if isinstance(step_dict, dict) and "depends_on" not in step_dict and i > 0:
                    # Infer sequential dependency from order if depends_on not specified
                    prev_name = raw_steps[i - 1].get("name")
                    if prev_name:
                        step_dict["depends_on"] = [prev_name]

        return WorkflowAST.model_validate(data)
    except ValidationError as e:
        raise WorkflowParseError(f"Workflow schema validation failed: {e}") from e


def parse_workflow_string(content: str) -> WorkflowAST:
    """Parse a YAML or JSON formatted string into `WorkflowAST`."""
    content_str = textwrap.dedent(content).strip()
    try:
        if content_str.startswith("{") or content_str.startswith("["):
            data = json.loads(content_str)
        else:
            data = yaml.safe_load(content_str)
        if not isinstance(data, dict):
            raise WorkflowParseError("Workflow definition root must be a YAML/JSON dictionary.")
        return parse_workflow_dict(data)
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise WorkflowParseError(f"Syntax error while decoding workflow string: {e}") from e


def parse_workflow_file(file_path: Path | str) -> WorkflowAST:
    """Parse a workflow definition file from the local filesystem."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow file not found: {path}")
    content = path.read_text(encoding="utf-8")
    return parse_workflow_string(content)
