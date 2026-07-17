"""Unit tests for the Relay CLI layer (`cli/main.py`)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli.main import _get_secret, _save_secret, app
from cli.version import __version__

runner = CliRunner()


def test_version_flag():
    """--version must print the current version string and exit cleanly."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_vault_set_and_get_via_keyring():
    """vault set/get must round-trip secrets through the OS Keyring."""
    store: dict[tuple[str, str], str] = {}

    def mock_set(system: str, username: str, password: str) -> None:
        store[(system, username)] = password

    def mock_get(system: str, username: str) -> str | None:
        return store.get((system, username))

    with (
        patch("keyring.set_password", side_effect=mock_set),
        patch("keyring.get_password", side_effect=mock_get),
    ):
        set_result = runner.invoke(app, ["vault", "set", "youtube", "client_id", "abc123"])
        assert set_result.exit_code == 0
        assert "✔" in set_result.output

        get_result = runner.invoke(app, ["vault", "get", "youtube", "client_id"])
        assert get_result.exit_code == 0
        assert "abc123" in get_result.output


def test_vault_list_empty():
    """vault list must print a helpful message when no credentials are stored."""
    with patch("cli.main._list_all_secrets", return_value={}):
        result = runner.invoke(app, ["vault", "list"])
        assert result.exit_code == 0
        assert "No credentials" in result.output


def test_vault_list_with_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """vault list must render a table of stored service -> key mappings."""
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps({"instagram": {"username": "user1", "token": "tok1"}}))
    monkeypatch.setattr("cli.main._get_secrets_path", lambda: secrets_file)
    result = runner.invoke(app, ["vault", "list"])
    assert result.exit_code == 0
    assert "instagram" in result.output


def test_run_invalid_pipeline():
    """`relay run` with an unknown pipeline must exit with code 1."""
    result = runner.invoke(app, ["run", "nonexistent_pipeline", "--url", "https://example.com"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_list_pipelines():
    """`relay list` must exit cleanly and show known pipeline names."""
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "insta_to_youtube" in result.output
    assert "tiktok_to_shorts" in result.output
