"""Typer CLI main application for Relay workflow runtime and secret management."""

import asyncio
import os
from pathlib import Path
from typing import Any
import typer
from rich.console import Console
from rich.table import Table
from relay.adapters.browser.manager import PlaywrightManager
from relay.adapters.secrets.vault import LocalVault
from relay.adapters.storage.artifact_store import LocalArtifactStore
from relay.adapters.storage.repository import SQLRepository
from relay.engine.event_bus import EventBus
from relay.engine.orchestrator import Orchestrator
from relay.engine.plugin_registry import PluginRegistry
from relay.surfaces.cli.progress import RichProgressSubscriber
from relay.workflow.compiler import compile_workflow
from relay.workflow.parser import parse_workflow_file

app = typer.Typer(name="relay", help="Relay Workflow Automation & Runtime CLI")
vault_app = typer.Typer(help="Manage secure credentials and API keys in the local vault.")
app.add_typer(vault_app, name="vault")
console = Console()


@vault_app.command("set")
def vault_set_cmd(
    service: str = typer.Argument(..., help="Platform or service identifier (e.g., 'instagram')"),
    key: str = typer.Argument(..., help="Secret key name (e.g., 'session_id')"),
    value: str = typer.Argument(..., help="Secret value to store securely"),
):
    """Store a secret credential in the local vault."""
    async def _run():
        vault = LocalVault()
        await vault.set_secret(service, key, value)
        console.print(f"[bold green]✔ Saved secret '[cyan]{key}[/cyan]' for service '[cyan]{service}[/cyan]'[/bold green]")

    asyncio.run(_run())


@vault_app.command("get")
def vault_get_cmd(
    service: str = typer.Argument(..., help="Platform or service identifier"),
    key: str = typer.Argument(..., help="Secret key name"),
):
    """Retrieve and display a stored secret from the local vault."""
    async def _run():
        vault = LocalVault()
        val = await vault.get_secret(service, key)
        if val is None:
            console.print(f"[bold red]✖ No secret found for '[cyan]{service}.{key}[/cyan]'[/bold red]")
            raise typer.Exit(code=1)
        console.print(f"[bold blue]{service}.{key}:[/bold blue] {val}")

    asyncio.run(_run())


@app.command("run")
def run_cmd(
    workflow_path: Path = typer.Argument(..., help="Path to the workflow YAML definition file"),
    job_id: str | None = typer.Option(None, "--job-id", "-j", help="Custom job identifier string"),
    var: list[str] | None = typer.Option(None, "--var", "-v", help="Override variable in key=value format"),
    account: list[str] | None = typer.Option(None, "--account", "-a", help="Set platform account mapping platform=profile_id"),
    db_url: str = typer.Option("sqlite+aiosqlite:///relay_state.db", "--db-url", help="SQLAlchemy async database connection URL"),
    artifact_dir: Path = typer.Option(Path("./artifacts"), "--artifacts", help="Base directory to store generated artifacts"),
):
    """Compile and execute a workflow definition file."""
    if not workflow_path.exists():
        console.print(f"[bold red]✖ Workflow file not found:[/bold red] {workflow_path}")
        raise typer.Exit(code=1)

    import uuid
    actual_job_id = job_id or f"job_{uuid.uuid4().hex[:8]}"

    # Parse overrides
    var_overrides: dict[str, Any] = {}
    if var:
        for v in var:
            if "=" not in v:
                console.print(f"[yellow]Ignoring invalid var override format '{v}' (expected key=val)[/yellow]")
                continue
            k, val = v.split("=", 1)
            var_overrides[k.strip()] = val.strip()

    account_mappings: dict[str, str] = {}
    if account:
        for a in account:
            if "=" not in a:
                continue
            k, val = a.split("=", 1)
            account_mappings[k.strip()] = val.strip()

    async def _run_async():
        # Parse and compile
        ast = parse_workflow_file(workflow_path)
        dag = compile_workflow(ast)

        # Initialize infrastructure and plugins
        import plugins.instagram.plugin
        import plugins.youtube.plugin
        import plugins.common.plugin
        plugins.instagram.plugin.InstagramPlugin()
        plugins.youtube.plugin.YouTubePlugin()
        plugins.common.plugin.CommonPlugin()

        registry = PluginRegistry()
        registry.discover_from_decorators()

        event_bus = EventBus()
        subscriber = RichProgressSubscriber(console=console)
        subscriber.subscribe_to_bus(event_bus)

        repo = SQLRepository(db_url=db_url)
        await repo.init_db()

        store = LocalArtifactStore(base_dir=artifact_dir)
        browser_mgr = PlaywrightManager()
        vault = LocalVault()

        orchestrator = Orchestrator(
            event_bus=event_bus,
            plugin_registry=registry,
            repository=repo,
            artifact_store=store,
            browser_manager=browser_mgr,
            vault=vault,
        )

        try:
            await orchestrator.run_workflow(
                dag=dag,
                job_id=actual_job_id,
                variable_overrides=var_overrides,
                account_ids=account_mappings,
            )
        finally:
            await browser_mgr.shutdown_all()
            await repo.close()

    asyncio.run(_run_async())


@app.command("status")
def status_cmd(
    job_id: str = typer.Argument(..., help="Job ID to query status and step history for"),
    db_url: str = typer.Option("sqlite+aiosqlite:///relay_state.db", "--db-url", help="Database connection URL"),
):
    """Query and display execution status for a job."""
    async def _query():
        repo = SQLRepository(db_url=db_url)
        await repo.init_db()
        try:
            job = await repo.get_job(job_id)
            if not job:
                console.print(f"[bold red]✖ Job ID '{job_id}' not found in database.[/bold red]")
                raise typer.Exit(code=1)

            console.print(f"\n[bold]Job ID:[/bold] {job.job_id}")
            console.print(f"[bold]Workflow:[/bold] {job.workflow_name}")
            status_color = "green" if job.status == "SUCCESS" else ("red" if job.status == "FAILED" else "yellow")
            console.print(f"[bold]Status:[/bold] [{status_color}]{job.status}[/{status_color}]")
            if job.error_message:
                console.print(f"[bold red]Error:[/bold red] {job.error_message}")

            steps = await repo.list_steps(job_id)
            if steps:
                table = Table(title="Step Execution History", show_header=True, header_style="bold magenta")
                table.add_column("Step Name")
                table.add_column("Status")
                table.add_column("Duration (s)", justify="right")
                table.add_column("Error Message")

                for s in steps:
                    sc = "green" if s.status == "SUCCESS" else ("red" if s.status == "FAILED" else "yellow")
                    table.add_row(
                        s.step_name,
                        f"[{sc}]{s.status}[/{sc}]",
                        f"{s.duration_seconds:.2f}" if s.duration_seconds else "-",
                        s.error_message or "",
                    )
                console.print(table)
            else:
                console.print("[dim]No steps recorded for this job.[/dim]")
        finally:
            await repo.close()

    asyncio.run(_query())


if __name__ == "__main__":
    app()
