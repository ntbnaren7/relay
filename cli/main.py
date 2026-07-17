"""Relay CLI (`cli/main.py`).

Pragmatic terminal entry point built with Typer and Rich.
Supports listing available pipelines, executing workflows directly,
and managing local credentials.
"""

import asyncio
import importlib
import json
import sys
from pathlib import Path

import keyring
import typer
from rich.console import Console
from rich.table import Table

from cli.update import check_for_updates, perform_self_update
from cli.version import __version__

app = typer.Typer(
    name="relay",
    help="Relay: Open-source, local-first workflow automation platform.",
    add_completion=False,
)
vault_app = typer.Typer(help="Manage local secret credentials (`relay vault`).")
app.add_typer(vault_app, name="vault")

console = Console()


# ---------------------------------------------------------------------------
# Credential Vault Helpers
# ---------------------------------------------------------------------------

def _get_secrets_path() -> Path:
    path = Path.home() / ".relay" / "secrets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _migrate_legacy_secrets() -> None:
    """Automatically migrate plaintext credentials from ~/.relay/secrets.json into Keyring."""
    path = _get_secrets_path()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or not data:
            return
        migrated_any = False
        for service, keys in data.items():
            if isinstance(keys, dict):
                for key, val in keys.items():
                    if isinstance(val, str):
                        try:
                            keyring.set_password(f"relay.{service}", key, val)
                            migrated_any = True
                        except Exception:
                            return  # If keyring fails, keep secrets.json for fallback
        if migrated_any:
            path.unlink(missing_ok=True)
            console.print("[dim green]✔ Migrated legacy plaintext secrets to secure OS Keyring.[/]")
    except Exception:
        pass


def _save_secret(service: str, key: str, value: str) -> bool:
    """Save secret to secure OS Keyring, falling back to local file if keyring is unavailable."""
    _migrate_legacy_secrets()
    try:
        keyring.set_password(f"relay.{service}", key, value)
        return True
    except Exception:
        path = _get_secrets_path()
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except Exception:
                data = {}
        data.setdefault(service, {})[key] = value
        path.write_text(json.dumps(data, indent=2))
        path.chmod(0o600)
        return False


def _get_secret(service: str, key: str) -> str | None:
    """Retrieve secret from secure OS Keyring, falling back to local file if needed."""
    _migrate_legacy_secrets()
    try:
        val = keyring.get_password(f"relay.{service}", key)
        if val is not None:
            return val
    except Exception:
        pass

    path = _get_secrets_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data.get(service, {}).get(key)
        except Exception:
            pass
    return None


def _list_all_secrets() -> dict[str, list[str]]:
    """Return a mapping of service -> list of keys from the OS Keyring and/or fallback file."""
    results: dict[str, list[str]] = {}

    # Collect from fallback file
    path = _get_secrets_path()
    if path.exists():
        try:
            data = json.loads(path.read_text())
            for svc, keys in data.items():
                if isinstance(keys, dict):
                    results.setdefault(svc, []).extend(keys.keys())
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# Playwright Browser Check
# ---------------------------------------------------------------------------

def _ensure_playwright_browsers() -> None:
    """Detect if Playwright Chromium is installed; install it automatically if not.

    End-users downloading the standalone binary will not have Chromium installed.
    This uses Playwright's own bundled Node.js driver (via `compute_driver_executable`)
    rather than `sys.executable -m playwright`, which fails inside a PyInstaller binary
    because `sys.executable` points to the compiled binary itself, not Python.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            chromium_path = Path(p.chromium.executable_path)
            if chromium_path.exists():
                return  # Already installed — nothing to do
    except Exception:
        pass

    # Chromium not found — install it using Playwright's own bundled Node driver
    console.print(
        "\n[bold yellow]Playwright Chromium browser not found on this machine.[/]"
    )
    console.print(
        "[dim]Relay needs Chromium to automate login and upload. "
        "This is a one-time download (~130 MB).[/]"
    )
    console.print("[cyan]Installing Chromium browser...[/]\n")

    import subprocess
    try:
        from playwright.__main__ import compute_driver_executable
        node_path, cli_js_path = compute_driver_executable()
        result = subprocess.run(
            [str(node_path), str(cli_js_path), "install", "chromium"],
            capture_output=False,  # Stream output directly to terminal
        )
    except Exception as e:
        console.print(f"[bold red]Failed to locate Playwright driver: {e}[/]")
        result = type("R", (), {"returncode": 1})()  # Fake failed result

    if result.returncode != 0:
        console.print(
            "[bold red]Failed to install Playwright Chromium automatically.[/]\n"
            "[dim]Please run manually:[/] [cyan]playwright install chromium[/]"
        )
        raise typer.Exit(code=1)

    console.print("\n[bold green]Chromium installed successfully! Starting pipeline...[/]\n")


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

@app.command("list")
def list_pipelines() -> None:
    """List all available automation pipelines in `pipelines/`."""
    table = Table(title="Available Relay Pipelines")
    table.add_column("Pipeline Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    pipelines_dir = Path(__file__).parent.parent / "pipelines"
    if pipelines_dir.exists():
        for file_path in sorted(pipelines_dir.glob("*.py")):
            if file_path.name.startswith("_") or file_path.name == "custom.py":
                continue
            name = file_path.stem
            doc = ""
            try:
                mod = importlib.import_module(f"pipelines.{name}")
                doc = (mod.__doc__ or "").strip().split("\n")[0]
            except Exception:
                doc = "Workflow script"
            table.add_row(name, doc)

    console.print(table)


# IMPORTANT: version_callback must be defined BEFORE @app.callback
# because it is referenced at decoration-time as an eager Typer option.
def version_callback(value: bool) -> None:
    if value:
        console.print(f"Relay version {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
) -> None:
    """Relay: Open-source, local-first workflow automation platform."""
    if ctx.invoked_subcommand is None:
        console.print("[bold magenta]⚡ Welcome to Relay Workflow Engine![/]\n")
        console.print("Select a workflow to launch:")
        console.print("  [cyan][1][/] Instagram Reel → YouTube Studio (`insta_to_youtube`)")
        console.print("  [cyan][2][/] TikTok Video → YouTube Shorts (`tiktok_to_shorts`)")
        try:
            choice = console.input("\n[bold white]Enter choice (1/2):[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/]")
            raise typer.Exit(code=0) from None

        if choice == "1":
            pipeline = "insta_to_youtube"
        elif choice == "2":
            pipeline = "tiktok_to_shorts"
        else:
            console.print("[bold red]Invalid selection. Exiting.[/]")
            raise typer.Exit(code=1) from None

        try:
            url = console.input(f"[bold cyan]🔗 Paste URL for {pipeline}:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/]")
            raise typer.Exit(code=0) from None

        if not url:
            console.print("[bold red]Error:[/] URL cannot be empty.")
            raise typer.Exit(code=1) from None

        run_pipeline(
            pipeline=pipeline,
            url=url,
            profile="default",
            privacy="private",
            headless=False,
        )


@app.command("run")
def run_pipeline(
    pipeline: str = typer.Argument(
        ..., help="Name of pipeline (`insta_to_youtube` or `tiktok_to_shorts`)"
    ),
    url: str | None = typer.Option(
        None, "--url", "-u", help="Source media URL (Instagram Reel or TikTok URL)"
    ),
    profile: str = typer.Option(
        "default", "--profile", "-p", help="Browser profile name for isolation"
    ),
    privacy: str = typer.Option(
        "private", "--privacy", help="YouTube Studio target privacy setting"
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Run browser in background headless mode"
    ),
) -> None:
    """Execute a pipeline directly by name (`relay run insta_to_youtube --url <url>`)."""
    if not url:
        try:
            url = console.input(f"[bold cyan]🔗 Paste URL for {pipeline}:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/]")
            raise typer.Exit(code=0) from None
        if not url:
            console.print("[bold red]Error:[/] URL cannot be empty.")
            raise typer.Exit(code=1) from None

    try:
        mod = importlib.import_module(f"pipelines.{pipeline}")
    except ImportError as e:
        console.print(
            f"[bold red]Error:[/] Pipeline '{pipeline}' not found in `pipelines/` ({e})."
        )
        raise typer.Exit(code=1) from None

    if not hasattr(mod, "run"):
        console.print(
            f"[bold red]Error:[/] Pipeline '{pipeline}' has no `async def run(...)` entry."
        )
        raise typer.Exit(code=1) from None

    # Ensure Chromium is installed before launching any browser pipeline
    _ensure_playwright_browsers()

    console.print(
        f"[bold green]Starting Relay pipeline:[/] [cyan]{pipeline}[/] -> {url}"
    )

    def _on_progress(msg: str) -> None:
        console.print(f"  [dim]{msg}[/]")

    try:
        result = asyncio.run(
            mod.run(
                url=url,
                profile_name=profile,
                privacy=privacy,
                progress_callback=_on_progress,
                headless=headless,
            )
        )
        console.print("[bold green]✔ Pipeline completed successfully![/]")
        console.print_json(data=result)
    except Exception as e:
        console.print(f"[bold red]✖ Pipeline failed:[/] {e}")
        raise typer.Exit(code=1) from None


# ---------------------------------------------------------------------------
# Vault Commands
# ---------------------------------------------------------------------------

@vault_app.command("set")
def vault_set(
    service: str = typer.Argument(..., help="Service identifier (e.g. `youtube` or `instagram`)"),
    key: str = typer.Argument(..., help="Credential key (e.g. `username` or `api_key`)"),
    value: str = typer.Argument(..., help="Secret value to store"),
) -> None:
    """Save a secret credential locally via secure OS Keyring (macOS Keychain, etc.)."""
    secure = _save_secret(service, key, value)
    if secure:
        console.print(f"[green]✔ Secret saved to secure OS Keyring for \\[{service}] -> {key}[/]")
    else:
        console.print(
            f"[yellow]⚠️ Keyring unavailable. Secret saved to local file (`~/.relay/secrets.json`) "
            f"for \\[{service}] -> {key}[/]"
        )


@vault_app.command("get")
def vault_get(
    service: str = typer.Argument(..., help="Service identifier"),
    key: str = typer.Argument(..., help="Credential key"),
) -> None:
    """Retrieve a stored secret credential from OS Keyring or local fallback."""
    val = _get_secret(service, key)
    if val is not None:
        console.print(f"[cyan]{val}[/]")
        return
    console.print(f"[yellow]No secret found for \\[{service}] -> {key}[/]")
    raise typer.Exit(code=1)


@vault_app.command("list")
def vault_list() -> None:
    """List all stored credential services and keys (values are never shown)."""
    secrets = _list_all_secrets()
    if not secrets:
        console.print("[yellow]No credentials stored yet. Use `relay vault set` to add one.[/]")
        return
    table = Table(title="Stored Relay Credentials")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Keys", style="white")
    for service, keys in sorted(secrets.items()):
        table.add_row(service, ", ".join(sorted(keys)))
    console.print(table)


# ---------------------------------------------------------------------------
# Update Command
# ---------------------------------------------------------------------------

@app.command("update")
def update_cli() -> None:
    """Update Relay to the latest standalone binary version."""
    perform_self_update()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        app()
    finally:
        # Non-blocking update notification for standalone binaries only
        if getattr(sys, "frozen", False):
            import threading

            def _notify() -> None:
                try:
                    latest = check_for_updates()
                    if latest:
                        console.print(
                            f"\n[dim]✨ A new version of Relay is available! "
                            f"({__version__} → {latest}). Run 'relay update' to upgrade.[/]"
                        )
                except Exception:
                    pass

            t = threading.Thread(target=_notify, daemon=True)
            t.start()
            t.join(timeout=0.1)


if __name__ == "__main__":
    main()
