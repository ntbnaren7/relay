"""Plugin metadata contracts and step registration decorators."""

from abc import ABC
from typing import Callable, Type, TypeVar
from relay.contracts.step import Permission, Step

TStep = TypeVar("TStep", bound=Type[Step])

# Global in-memory registry map of decorated step classes by unique identifier
_STEP_REGISTRY: dict[str, Type[Step]] = {}


def step(
    name: str,
    description: str = "",
    version: str = "1.0.0",
    permissions: list[Permission] | None = None,
) -> Callable[[TStep], TStep]:
    """Decorator to register a Step implementation class under a unique identifier string (`uses`)."""
    def decorator(cls: TStep) -> TStep:
        cls.name = name
        cls.version = version
        if description:
            cls.description = description
        if permissions is not None:
            cls.permissions = permissions
        _STEP_REGISTRY[name] = cls
        return cls

    return decorator


def get_registered_steps() -> dict[str, Type[Step]]:
    """Return a copy of all steps registered via `@step` decorators."""
    return dict(_STEP_REGISTRY)


class Plugin(ABC):
    """Base contract for platform suites and bundles."""

    name: str
    version: str
    description: str
    author: str
