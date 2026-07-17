"""Storage, repository, and credential vault contracts (`IArtifactStore`, `IRepository`, `IVault`)."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator
from relay.domain.artifact import Artifact


class IArtifactStore(ABC):
    """Contract governing media and data artifact persistence across disk, memory, or S3."""

    @abstractmethod
    async def save(self, artifact: Artifact, data_stream: AsyncIterator[bytes]) -> str:
        """Stream bytes into storage and return the storage URI or identifier."""
        pass

    @abstractmethod
    async def resolve(self, artifact: Artifact) -> AsyncIterator[bytes]:
        """Stream bytes out of storage for a given artifact."""
        pass

    @abstractmethod
    async def delete(self, artifact: Artifact) -> bool:
        """Remove stored payload bytes from storage."""
        pass


class IRepository(ABC):
    """Contract for database persistence of jobs, steps, and execution history."""

    @abstractmethod
    async def save_job(self, job_data: dict[str, Any]) -> str:
        """Persist or update job state and return job_id."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Retrieve stored job metadata by ID."""
        pass

    @abstractmethod
    async def update_job_status(self, job_id: str, status: str, error_message: str | None = None) -> None:
        """Update job execution status."""
        pass


class IVault(ABC):
    """Contract for secure local credential and token storage (`keyring` / AES-GCM)."""

    @abstractmethod
    async def set_secret(self, key: str, value: str) -> None:
        """Securely store a secret string under a key."""
        pass

    @abstractmethod
    async def get_secret(self, key: str) -> str | None:
        """Retrieve a stored secret or return None if not set."""
        pass

    @abstractmethod
    async def delete_secret(self, key: str) -> bool:
        """Remove a secret from the vault."""
        pass
