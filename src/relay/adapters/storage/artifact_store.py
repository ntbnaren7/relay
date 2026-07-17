"""Local filesystem and memory implementation of `IArtifactStore`."""

import aiofiles
from pathlib import Path
from typing import AsyncIterator
from relay.contracts.storage import IArtifactStore
from relay.domain.artifact import Artifact, ArtifactType


class LocalArtifactStore(IArtifactStore):
    """Persists artifacts to local filesystem (`~/.relay/artifacts`) or memory."""

    def __init__(self, base_dir: Path | str = Path.home() / ".relay" / "artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, bytes] = {}

    async def save(self, artifact: Artifact, data_stream: AsyncIterator[bytes]) -> str:
        if artifact.artifact_type == ArtifactType.MEMORY:
            chunks = []
            async for chunk in data_stream:
                chunks.append(chunk)
            payload = b"".join(chunks)
            uri = f"memory://{artifact.id}"
            self._memory_cache[uri] = payload
            artifact.storage_uri = uri
            return uri

        # File or archive persistence
        target_dir = self.base_dir / artifact.id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / artifact.name

        async with aiofiles.open(target_path, "wb") as f:
            async for chunk in data_stream:
                await f.write(chunk)

        uri = f"file://{target_path.resolve()}"
        artifact.local_path = target_path.resolve()
        artifact.storage_uri = uri
        return uri

    async def resolve(self, artifact: Artifact) -> AsyncIterator[bytes]:
        uri = artifact.storage_uri
        if not uri:
            if artifact.local_path and artifact.local_path.exists():
                uri = f"file://{artifact.local_path.resolve()}"
            else:
                uri = f"memory://{artifact.id}"

        if uri.startswith("memory://"):
            if uri not in self._memory_cache:
                raise KeyError(f"Memory artifact {uri} not found in LocalArtifactStore.")
            yield self._memory_cache[uri]
            return

        if uri.startswith("file://"):
            file_path = Path(uri[7:])
            if not file_path.exists():
                raise FileNotFoundError(f"Local artifact file not found: {file_path}")
            async with aiofiles.open(file_path, "rb") as f:
                while True:
                    chunk = await f.read(65536)
                    if not chunk:
                        break
                    yield chunk
            return

        raise ValueError(f"Unsupported artifact storage scheme: {uri}")

    async def delete(self, artifact: Artifact) -> bool:
        uri = artifact.storage_uri
        if not uri:
            return False

        if uri.startswith("memory://"):
            if uri in self._memory_cache:
                del self._memory_cache[uri]
                return True
            return False

        if uri.startswith("file://"):
            file_path = Path(uri[7:])
            if file_path.exists():
                file_path.unlink()
                # Remove empty directory if clean
                parent = file_path.parent
                if parent != self.base_dir and not any(parent.iterdir()):
                    parent.rmdir()
                return True
            return False

        return False
