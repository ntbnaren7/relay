"""Pytest configuration and test fixtures (`tests/conftest.py`)."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_profile_dir(tmp_path: Path) -> Path:
    """Provide a temporary profile directory for browser session tests."""
    return tmp_path / "profiles"


@pytest.fixture
def tmp_media_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for media download and transcode tests."""
    return tmp_path / "media"
