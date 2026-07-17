"""Unit tests for secure credential vault storage (`cli/main.py`)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli.main import _get_secret, _migrate_legacy_secrets, _save_secret


@pytest.fixture
def mock_secrets_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target_path = tmp_path / ".relay" / "secrets.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("cli.main._get_secrets_path", lambda: target_path)
    return target_path


def test_vault_keyring_success(mock_secrets_path: Path):
    """Verify secrets are saved and retrieved via Keyring when available without writing to disk."""
    store = {}

    def mock_set(system: str, username: str, password: str) -> None:
        store[(system, username)] = password

    def mock_get(system: str, username: str) -> str | None:
        return store.get((system, username))

    with patch("keyring.set_password", side_effect=mock_set), \
         patch("keyring.get_password", side_effect=mock_get):
        res = _save_secret("youtube", "client_id", "secret_123")
        assert res is True
        assert _get_secret("youtube", "client_id") == "secret_123"
        assert not mock_secrets_path.exists()


def test_vault_keyring_fallback(mock_secrets_path: Path):
    """Verify fallback to secrets.json when Keyring raises an exception (e.g., in CI or headless)."""
    with patch("keyring.set_password", side_effect=RuntimeError("No keyring backend")), \
         patch("keyring.get_password", side_effect=RuntimeError("No keyring backend")):
        res = _save_secret("instagram", "token", "token_abc")
        assert res is False
        assert mock_secrets_path.exists()

        saved_data = json.loads(mock_secrets_path.read_text())
        assert saved_data["instagram"]["token"] == "token_abc"
        assert _get_secret("instagram", "token") == "token_abc"


def test_vault_automatic_migration(mock_secrets_path: Path):
    """Verify that existing plaintext secrets in secrets.json are automatically migrated to Keyring."""
    mock_secrets_path.parent.mkdir(parents=True, exist_ok=True)
    mock_secrets_path.write_text(json.dumps({"reddit": {"username": "test_user"}}))

    store = {}

    def mock_set(system: str, username: str, password: str) -> None:
        store[(system, username)] = password

    def mock_get(system: str, username: str) -> str | None:
        return store.get((system, username))

    with patch("keyring.set_password", side_effect=mock_set), \
         patch("keyring.get_password", side_effect=mock_get):
        _migrate_legacy_secrets()
        assert store[("relay.reddit", "username")] == "test_user"
        assert not mock_secrets_path.exists()
