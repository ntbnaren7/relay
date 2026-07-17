"""StepExecutor wrapping step invocation with validation, timeout enforcement, retries, and events."""

import asyncio
import time
from relay.contracts.step import Step, StepResult, StepStatus
from relay.domain.context import StepContext
from relay.domain.events import StepCompleted, StepFailed, StepStarted
from relay.engine.event_bus import EventBus
from relay.engine.retry import RetryPolicy, execute_with_retry


class StepExecutionError(Exception):
    """Raised when a step fails validation or throws an unhandled exception during execution."""
    pass


class StepExecutor:
    """Executes atomic Step instances within a StepContext, emitting lifecycle events."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def execute_step(
        self,
        step_instance: Step,
        context: StepContext,
        retry_policy: RetryPolicy | None = None,
        timeout_seconds: float | None = None,
    ) -> StepResult:
        """Run step validation and execution, handling timeouts, retries, and events."""
        await self.event_bus.publish(
            StepStarted(job_id=context.job_id, step_name=context.step_name)
        )

        # 1. Validate inputs
        try:
            is_valid = await step_instance.validate_inputs(context)
            if not is_valid:
                error_msg = f"Step '{context.step_name}' failed pre-execution input validation."
                await self.event_bus.publish(
                    StepFailed(job_id=context.job_id, step_name=context.step_name, error_message=error_msg)
                )
                return StepResult(status=StepStatus.FAILED, error_message=error_msg)
        except Exception as e:
            error_msg = f"Input validation raised exception: {e}"
            await self.event_bus.publish(
                StepFailed(job_id=context.job_id, step_name=context.step_name, error_message=error_msg)
            )
            return StepResult(status=StepStatus.FAILED, error_message=error_msg)

        # 2. Execution action with optional timeout
        async def _run_once() -> StepResult:
            if timeout_seconds and timeout_seconds > 0:
                res = await asyncio.wait_for(step_instance.execute(context), timeout=timeout_seconds)
            else:
                res = await step_instance.execute(context)
            if res.status == StepStatus.FAILED and res.should_retry:
                raise StepExecutionError(res.error_message or "Step requested retry upon failure.")
            return res

        policy = retry_policy or RetryPolicy(max_attempts=1)
        start_time = time.monotonic()

        async def _on_retry(attempt: int, exc: Exception, delay: float) -> None:
            await self.event_bus.publish(
                StepFailed(
                    job_id=context.job_id,
                    step_name=context.step_name,
                    error_message=f"Attempt {attempt} failed ({exc}). Retrying in {delay:.1f}s...",
                    will_retry=True,
                    attempt=attempt,
                )
            )

        try:
            result = await execute_with_retry(_run_once, policy, on_retry=_on_retry)
            duration = time.monotonic() - start_time

            if result.status == StepStatus.SUCCESS:
                await self.event_bus.publish(
                    StepCompleted(
                        job_id=context.job_id,
                        step_name=context.step_name,
                        output_count=len(result.output_artifacts),
                        duration_seconds=duration,
                    )
                )
            else:
                await self.event_bus.publish(
                    StepFailed(
                        job_id=context.job_id,
                        step_name=context.step_name,
                        error_message=result.error_message or "Step returned non-success status.",
                        will_retry=False,
                    )
                )
            return result

        except Exception as e:
            duration = time.monotonic() - start_time
            error_msg = f"Step execution failed after retries: {e}"
            await self.event_bus.publish(
                StepFailed(
                    job_id=context.job_id,
                    step_name=context.step_name,
                    error_message=error_msg,
                    will_retry=False,
                )
            )
            return StepResult(status=StepStatus.FAILED, error_message=error_msg)
