"""Browser automation interfaces (`IBrowserDriver` and `IBrowserManager`)."""

from abc import ABC, abstractmethod
from typing import Any


class IBrowserDriver(ABC):
    """Abstract wrapper around an isolated browser page or context session."""

    @abstractmethod
    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> Any:
        """Navigate the active browser context to the given target URL."""
        pass

    @abstractmethod
    async def get_content(self) -> str:
        """Return the current rendered DOM HTML string."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cleanly close and terminate this browser page/context session."""
        pass


class IBrowserManager(ABC):
    """Abstract contract for pooling and managing browser context instances."""

    @abstractmethod
    async def get_driver(
        self,
        profile_name: str = "default",
        headless: bool = True,
        proxy_url: str | None = None,
    ) -> IBrowserDriver:
        """Lease or create an isolated `IBrowserDriver` instance."""
        pass

    @abstractmethod
    async def close_all(self) -> None:
        """Terminate all active browser sessions and shut down browser processes."""
        pass
