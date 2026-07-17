"""Local credential storage adapter implementing `IVault`."""

import json
import os
from pathlib import Path
from relay.contracts.storage import IVault

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False


class LocalVault(IVault):
    """Stores secrets via OS Keyring (`keyring`) or protected local JSON fallback (`~/.relay/secrets.json`)."""

    def __init__(self, service_name: str = "relay.automation", fallback_path: Path | str = Path.home() / ".relay" / "secrets.json"):
        self.service_name = service_name
        self.fallback_path = Path(fallback_path)
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)

    async def set_secret(self, key: str, value: str) -> None:
        if _KEYRING_AVAILABLE:
            try:
                keyring.set_password(self.service_name, key, value)
                return
            except Exception:
                pass  # Fallback if headless or keyring daemon inactive

        data = {}
        if self.fallback_path.exists():
            try:
                data = json.loads(self.fallback_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data[key] = value
        self.fallback_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(self.fallback_path, 0o600)
        except Exception:
            pass

    async def get_secret(self, key: str) -> str | None:
        if _KEYRING_AVAILABLE:
            try:
                val = keyring.get_password(self.service_name, key)
                if val is not None:
                    return val
            except Exception:
                pass

        if self.fallback_path.exists():
            try:
                data = json.loads(self.fallback_path.read_text(encoding="utf-8"))
                return data.get(key)
            except Exception:
                return None
        return None

    async def delete_secret(self, key: str) -> bool:
        if _KEYRING_AVAILABLE:
            try:
                keyring.delete_password(self.service_name, key)
                return True
            except Exception:
                pass

        if self.fallback_path.exists():
            try:
                data = json.loads(self.fallback_path.read_text(encoding="utf-8"))
                if key in data:
                    del data[key]
                    self.fallback_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    return True
            except Exception:
                pass
        return False
