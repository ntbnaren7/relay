"""Server-Sent Events (SSE) broadcaster subscribing to the Relay EventBus."""

import asyncio
import json
from typing import AsyncIterator
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


class SSEBroadcaster:
    """Subscribes to EventBus topics and streams formatted SSE data frames to active API clients."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._queues: set[tuple[asyncio.Queue[str], str | None]] = set()
        self._subscribe_all()

    def _subscribe_all(self) -> None:
        self.event_bus.subscribe("job.*", self)
        self.event_bus.subscribe("step.*", self)
        self.event_bus.subscribe("log.*", self)

    async def __call__(self, event: BaseEvent) -> None:
        """Handle event broadcast to all queued subscriber streams."""
        job_id = getattr(event, "job_id", None)
        payload = {
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "job_id": job_id,
        }

        if isinstance(event, JobStarted):
            payload.update({"workflow_name": event.workflow_name, "total_steps": event.total_steps})
        elif isinstance(event, (StepStarted, StepCompleted, StepFailed)):
            payload.update({"step_name": event.step_name})
            if isinstance(event, StepCompleted):
                payload["output_count"] = event.output_count
                payload["duration_seconds"] = event.duration_seconds
            elif isinstance(event, StepFailed):
                payload["error_message"] = event.error_message
                payload["will_retry"] = event.will_retry
        elif isinstance(event, ProgressUpdated):
            payload.update({
                "step_name": event.step_name,
                "progress_percentage": event.progress_percentage,
                "message": event.message,
            })
        elif isinstance(event, (JobCompleted, JobFailed)):
            payload["workflow_name"] = event.workflow_name
            if isinstance(event, JobCompleted):
                payload["duration_seconds"] = event.duration_seconds
            else:
                payload["failed_step"] = event.failed_step
                payload["error_message"] = event.error_message
        elif isinstance(event, LogEvent):
            payload.update({"level": event.level, "message": event.message})

        frame = f"event: {event.event_type}\ndata: {json.dumps(payload)}\n\n"

        for queue, target_job_id in list(self._queues):
            if target_job_id is None or target_job_id == job_id:
                await queue.put(frame)

    async def stream_events(self, target_job_id: str | None = None) -> AsyncIterator[str]:
        """Yield SSE frames for a specific job ID or all active jobs."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        entry = (queue, target_job_id)
        self._queues.add(entry)
        try:
            while True:
                frame = await queue.get()
                yield frame
        except asyncio.CancelledError:
            pass
        finally:
            self._queues.discard(entry)
