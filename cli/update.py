"""Self-updating mechanism for standalone binaries (`cli/update.py`)."""
import json
import os
import platform
import stat
import sys
import time
from pathlib import Path

import httpx
from rich.console import Console

from cli.version import __version__

console = Console()
GITHUB_API = "https://api.github.com/repos/ntbnaren7/relay/releases/latest"
CACHE_FILE = Path.home() / ".relay" / "update_cache.json"
CACHE_TTL = 86400  # 24 hours


def _get_platform_identifier() -> str:
    """Return the architecture string expected in GitHub Release assets."""
    sys_os = platform.system().lower()
    sys_arch = platform.machine().lower()

    if sys_os == "darwin":
        sys_os = "macos"
    elif sys_os == "windows":
        sys_os = "windows"
    
    if sys_arch in ("x86_64", "amd64"):
        sys_arch = "x64"
    elif sys_arch in ("arm64", "aarch64"):
        sys_arch = "arm64"
        
    return f"{sys_os}-{sys_arch}"


def check_for_updates() -> str | None:
    """Return the new version string if an update is available, else None."""
    now = time.time()
    
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text())
            if now - cache.get("timestamp", 0) < CACHE_TTL:
                latest = cache.get("latest_version")
                if latest and latest.lstrip("v") > __version__.lstrip("v"):
                    return latest
                return None
        except Exception:
            pass

    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(GITHUB_API)
            if resp.status_code == 200:
                latest = resp.json().get("tag_name", "")
                CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(json.dumps({
                    "timestamp": now,
                    "latest_version": latest
                }))
                if latest and latest.lstrip("v") > __version__.lstrip("v"):
                    return latest
    except Exception:
        pass
    return None


def perform_self_update() -> None:
    """Download and replace the current executing binary with the latest release."""
    if not getattr(sys, "frozen", False):
        console.print("[yellow]⚠️ Cannot self-update a python script. Use `git pull` or `uv` to update.[/]")
        return

    latest = check_for_updates()
    if not latest:
        console.print(f"[green]✔ You are already on the latest version (v{__version__}).[/]")
        return

    arch_id = _get_platform_identifier()
    asset_name = f"relay-{arch_id}"
    if platform.system().lower() == "windows":
        asset_name += ".exe"

    download_url = f"https://github.com/ntbnaren7/relay/releases/download/{latest}/{asset_name}"
    current_exe = Path(sys.executable)
    temp_exe = current_exe.with_suffix(".tmp")
    old_exe = current_exe.with_suffix(".old")

    try:
        console.print(f"[cyan]Downloading Relay {latest} for {arch_id}...[/]")
        with httpx.Client(follow_redirects=True) as client:
            with client.stream("GET", download_url) as resp:
                if resp.status_code != 200:
                    console.print(f"[red]❌ Failed to download update: HTTP {resp.status_code} ({download_url})[/]")
                    return
                with open(temp_exe, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        if platform.system().lower() != "windows":
            temp_exe.chmod(temp_exe.stat().st_mode | stat.S_IEXEC)

        if platform.system().lower() == "windows":
            if old_exe.exists():
                old_exe.unlink(missing_ok=True)
            current_exe.rename(old_exe)
            temp_exe.rename(current_exe)
        else:
            temp_exe.replace(current_exe)

        CACHE_FILE.unlink(missing_ok=True)
        console.print(f"[bold green]🎉 Relay successfully updated to {latest}![/]")

    except Exception as e:
        console.print(f"[red]❌ Update failed: {e}[/]")
        if temp_exe.exists():
            temp_exe.unlink(missing_ok=True)
