"""Exponential backoff and retry policy execution utilities."""

import asyncio
import random
from typing import Any, Awaitable, Callable, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class RetryPolicy(BaseModel):
    """Configuration model for step retry behavior."""

    max_attempts: int = Field(default=3, ge=1, description="Maximum total execution attempts.")
    base_delay_seconds: float = Field(default=1.0, ge=0.0, description="Initial backoff delay in seconds.")
    max_delay_seconds: float = Field(default=60.0, ge=0.0, description="Maximum backoff delay ceiling.")
    exponential_base: float = Field(default=2.0, ge=1.0, description="Base multiplier for exponential backoff.")
    jitter: bool = Field(default=True, description="Whether to apply randomized jitter to backoff delay.")

    def get_delay(self, attempt: int) -> float:
        """Calculate the backoff sleep duration before the given retry attempt (1-indexed)."""
        if attempt <= 1:
            return 0.0
        delay = self.base_delay_seconds * (self.exponential_base ** (attempt - 2))
        delay = min(delay, self.max_delay_seconds)
        if self.jitter and delay > 0:
            # Full jitter: random between 0.5*delay and delay
            delay = random.uniform(delay * 0.5, delay)
        return delay


async def execute_with_retry(
    action: Callable[[], Awaitable[T]],
    retry_policy: RetryPolicy,
    on_retry: Callable[[int, Exception, float], Awaitable[None] | None] | None = None,
) -> T:
    """Execute an async action with exponential backoff and retries."""
    last_exception: Exception | None = None

    for attempt in range(1, retry_policy.max_attempts + 1):
        try:
            return await action()
        except Exception as e:
            last_exception = e
            if attempt >= retry_policy.max_attempts:
                break

            delay = retry_policy.get_delay(attempt + 1)
            if on_retry:
                res = on_retry(attempt, e, delay)
                if asyncio.iscoroutine(res):
                    await res
            if delay > 0:
                await asyncio.sleep(delay)

    assert last_exception is not None
    raise last_exception
