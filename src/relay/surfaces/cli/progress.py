"""Rich live progress bar and console event subscriber for CLI runs."""

from typing import Any
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from relay.domain.events import (
    BaseEvent,
    JobCompleted,
    JobFailed,
    JobStarted,
    LogEvent,
    ProgressUpdated,
    StepCompleted,
    StepFailed,
    StepStarted,
)
from relay.engine.event_bus import EventBus


class RichProgressSubscriber:
    """Subscribes to Relay EventBus events to display live execution progress in terminal."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
        )
        self.task_ids: dict[str, Any] = {}
        self.job_task_id: Any | None = None

    async def __call__(self, event: BaseEvent) -> None:
        """Handle incoming workflow events."""
        if isinstance(event, JobStarted):
            self.progress.start()
            self.job_task_id = self.progress.add_task(
                f"[bold cyan]Workflow: {event.workflow_name}", total=event.total_steps
            )

        elif isinstance(event, StepStarted):
            self.task_ids[event.step_name] = self.progress.add_task(
                f"Step: {event.step_name}", total=100.0
            )

        elif isinstance(event, ProgressUpdated):
            if event.step_name in self.task_ids:
                msg = f"Step: {event.step_name} ({event.message})" if event.message else f"Step: {event.step_name}"
                self.progress.update(
                    self.task_ids[event.step_name],
                    completed=event.progress_percentage,
                    description=msg,
                )

        elif isinstance(event, StepCompleted):
            if event.step_name in self.task_ids:
                self.progress.update(
                    self.task_ids[event.step_name],
                    completed=100.0,
                    description=f"[green]✔ Step: {event.step_name} ({event.output_count} artifacts)",
                )
            if self.job_task_id is not None:
                self.progress.advance(self.job_task_id, 1)

        elif isinstance(event, StepFailed):
            if event.step_name in self.task_ids:
                status_txt = "[yellow]↻ Retrying" if event.will_retry else "[red]✖ Failed"
                self.progress.update(
                    self.task_ids[event.step_name],
                    description=f"{status_txt}: {event.step_name} - {event.error_message}",
                )

        elif isinstance(event, (JobCompleted, JobFailed)):
            self.progress.stop()
            if isinstance(event, JobCompleted):
                self.console.print(
                    f"\n[bold green]✔ Workflow '{event.workflow_name}' completed in {event.duration_seconds:.2f}s![/bold green]"
                )
            else:
                self.console.print(
                    f"\n[bold red]✖ Workflow '{event.workflow_name}' failed at step '{event.failed_step}': {event.error_message}[/bold red]"
                )

        elif isinstance(event, LogEvent):
            color = {"ERROR": "red", "WARNING": "yellow", "INFO": "blue"}.get(event.level, "white")
            self.console.print(f"[{color}][{event.level}] {event.message}[/{color}]")

    def subscribe_to_bus(self, event_bus: EventBus) -> None:
        """Subscribe this progress handler to all relevant event topics."""
        event_bus.subscribe("job.*", self)
        event_bus.subscribe("step.*", self)
        event_bus.subscribe("log.*", self)
