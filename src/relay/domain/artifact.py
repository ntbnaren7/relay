"""Artifact domain models representing data payloads moving between steps."""

from enum import Enum
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ArtifactType(str, Enum):
    """Enumeration of supported artifact data types."""

    FILE = "file"
    MEMORY = "memory"
    JSON = "json"
    ARCHIVE = "archive"


class Artifact(BaseModel):
    """Represents a standardized data payload or media item produced or consumed by a Step."""

    model_config = ConfigDict(frozen=False, extra="allow")

    id: str = Field(..., description="Unique identifier for this artifact instance.")
    artifact_type: ArtifactType = Field(..., description="The type of storage/representation.")
    name: str = Field(..., description="Human-readable filename or payload name.")
    mime_type: str = Field(default="application/octet-stream", description="MIME content type.")
    local_path: Path | None = Field(default=None, description="Physical path if type is FILE.")
    data_payload: dict[str, Any] | None = Field(
        default=None, description="Structured data if type is JSON."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible metadata (duration, resolution, tags)."
    )
    checksum_sha256: str | None = Field(default=None, description="SHA-256 hash of the payload.")
    storage_uri: str | None = Field(default=None, description="Backend storage URI if persisted.")

    def get_file_path(self) -> Path:
        """Safely retrieve the local file path or raise ValueError if not a local file artifact."""
        if self.artifact_type != ArtifactType.FILE or not self.local_path:
            raise ValueError(f"Artifact {self.name} ({self.id}) is not a local file artifact.")
        return self.local_path
