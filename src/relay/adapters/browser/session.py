"""Persistent browser profile session state (`storage_state.json`) management."""

import json
from pathlib import Path
from playwright.async_api import BrowserContext


class SessionStorageManager:
    """Loads and saves browser cookies and local storage to `~/.relay/profiles/<profile_name>/state.json`."""

    def __init__(self, profiles_dir: Path | str = Path.home() / ".relay" / "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def get_state_path(self, profile_name: str) -> Path:
        profile_dir = self.profiles_dir / profile_name
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir / "storage_state.json"

    def state_exists(self, profile_name: str) -> bool:
        return self.get_state_path(profile_name).exists()

    async def save_context_state(self, context: BrowserContext, profile_name: str) -> Path:
        """Export state from an active context to disk."""
        path = self.get_state_path(profile_name)
        await context.storage_state(path=path)
        return path
