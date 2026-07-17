"""Relay CLI (`cli/main.py`).

Pragmatic terminal entry point built with Typer and Rich.
Supports listing available pipelines, executing workflows directly,
and managing local credentials.
"""

import asyncio
import importlib
import json
from pathlib import Path

import keyring
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="relay",
    help="Relay: Open-source, local-first workflow automation platform.",
    add_completion=False,
)
vault_app = typer.Typer(help="Manage local secret credentials (`relay vault`).")
app.add_typer(vault_app, name="vault")

console = Console()


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


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Relay interactive workflow starter when run with no arguments."""
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
            f"[yellow]⚠️ Keyring unavailable. Secret saved to local file (`~/.relay/secrets.json`) for \\[{service}] -> {key}[/]"
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


if __name__ == "__main__":
    app()
