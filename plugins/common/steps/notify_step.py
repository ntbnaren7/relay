"""Step implementation for sending webhook and local notifications (`common.notify`)."""

from relay.contracts.plugin import step
from relay.contracts.step import Permission, Step, StepResult, StepStatus
from relay.domain.context import StepContext
from relay.domain.events import LogEvent
from relay.utils.http import HttpClient


@step(name="common.notify", version="1.0.0", permissions=[Permission.NETWORK])
class NotifyStep(Step):
    """Sends HTTP webhook notifications (e.g. Discord, Slack) or emits structured log entries."""

    async def validate_inputs(self, context: StepContext) -> bool:
        # Requires message or webhook_url in config or inputs
        return bool(context.config.get("message") or context.config.get("webhook_url"))

    async def execute(self, context: StepContext) -> StepResult:
        message = context.config.get("message", "Relay workflow notification")
        webhook_url = context.config.get("webhook_url")

        # Emit structured log event on the event bus
        await context.event_bus.publish(
            LogEvent(
                job_id=context.job_id,
                level="INFO",
                message=f"[NOTIFICATION]: {message}",
                context_data={"inputs_count": len(context.inputs)},
            )
        )

        status_meta = {"notified": True, "message": message}

        if webhook_url and webhook_url.startswith("http"):
            client = HttpClient()
            try:
                await client.post(webhook_url, json={"content": message, "job_id": context.job_id})
                status_meta["webhook_sent"] = True
            except Exception as e:
                status_meta["webhook_sent"] = False
                status_meta["error"] = str(e)

        return StepResult(status=StepStatus.SUCCESS, metadata=status_meta)
