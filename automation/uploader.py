"""Media upload automation utilities (`automation/uploader.py`).

Provides shared validation checks, chunk progress monitoring,
and local file readiness utilities for platform uploaders.
"""

from pathlib import Path


class FileNotReadyError(Exception):
    """Raised when a local file is missing, empty, or inaccessible for uploading."""
    pass


def verify_file_for_upload(file_path: Path | str, min_size_bytes: int = 100) -> Path:
    """Check that a file exists and meets minimum size requirements before attempting upload."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotReadyError(f"Upload target file '{path}' does not exist.")
    if not path.is_file():
        raise FileNotReadyError(f"Upload target '{path}' is not a file.")
    if path.stat().st_size < min_size_bytes:
        size = path.stat().st_size
        raise FileNotReadyError(
            f"Upload target '{path}' size ({size}B) is below minimum ({min_size_bytes}B)."
        )
    return path


def format_progress_message(step_name: str, current: int, total: int) -> str:
    """Generate standardized progress string for CLI or logging output."""
    if total <= 0:
        return f"[{step_name}] Processing..."
    percentage = min(100.0, (current / total) * 100.0)
    return f"[{step_name}] {percentage:.1f}% ({current}/{total} bytes)"
