"""Dynamic discovery and lookup registry for `Step` and `Plugin` implementations."""

import importlib
import importlib.metadata
import pkgutil
from typing import Type
from relay.contracts.plugin import get_registered_steps
from relay.contracts.step import Step


class PluginLoadError(Exception):
    """Raised when a plugin module or step class fails to load."""
    pass


class PluginRegistry:
    """Discovers, loads, and indexes Step implementation classes by their unique `uses` identifier."""

    def __init__(self):
        self._steps: dict[str, Type[Step]] = {}

    def register_step_class(self, step_cls: Type[Step]) -> None:
        """Manually register a Step class."""
        self._steps[step_cls.name] = step_cls

    def discover_from_decorators(self) -> None:
        """Import all currently registered `@relay.step` decorators in memory."""
        self._steps.update(get_registered_steps())

    def discover_package(self, package_name: str) -> int:
        """Recursively import all submodules within a package to trigger `@relay.step` decorators."""
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            raise PluginLoadError(f"Failed to import package '{package_name}': {e}") from e

        imported_count = 0
        if hasattr(package, "__path__"):
            for _, modname, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
                try:
                    importlib.import_module(modname)
                    imported_count += 1
                except Exception as e:
                    raise PluginLoadError(f"Failed loading plugin submodule '{modname}': {e}") from e

        self.discover_from_decorators()
        return imported_count

    def discover_entry_points(self, group: str = "relay.plugins") -> int:
        """Discover and load plugin packages registered via Python package entry points."""
        loaded_count = 0
        try:
            eps = importlib.metadata.entry_points(group=group)
            for ep in eps:
                ep.load()
                loaded_count += 1
        except Exception as e:
            raise PluginLoadError(f"Error loading entry points for group '{group}': {e}") from e

        self.discover_from_decorators()
        return loaded_count

    def get_step(self, uses: str) -> Type[Step] | None:
        """Look up a Step class by its `uses` identifier (e.g. 'instagram.download_reels')."""
        return self._steps.get(uses)

    def get_step_class(self, uses: str) -> Type[Step] | None:
        """Alias for get_step."""
        return self.get_step(uses)

    def list_steps(self) -> dict[str, Type[Step]]:
        """Return a dictionary of all registered step identifiers to their classes."""
        return dict(self._steps)

    def list_available_steps(self) -> dict[str, Type[Step]]:
        """Alias for list_steps."""
        return self.list_steps()
