"""Custom base runner helper for custom user scripts (`pipelines/custom.py`)."""

from collections.abc import Callable, Coroutine
from typing import Any


async def run_custom_pipeline(
    task_fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute any user-provided async workflow function inside a managed event loop wrapper."""
    return await task_fn(*args, **kwargs)
