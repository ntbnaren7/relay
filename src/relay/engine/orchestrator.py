"""Orchestrator driving DAG execution across topological layers with concurrency and checkpointing."""

import asyncio
import time
from typing import Any
from relay.contracts.step import StepStatus
from relay.contracts.storage import IRepository
from relay.domain.context import JobContext, StepContext
from relay.domain.events import JobCompleted, JobFailed, JobStarted
from relay.engine.event_bus import EventBus
from relay.engine.executor import StepExecutor
from relay.engine.plugin_registry import PluginRegistry
from relay.engine.retry import RetryPolicy
from relay.engine.state import StateManager
from relay.workflow.compiler import CompiledDAG


class OrchestrationError(Exception):
    """Raised when the orchestrator encounters fatal execution errors."""
    pass


class Orchestrator:
    """Core DAG engine executing workflow batches, handling data flow and checkpoints."""

    def __init__(
        self,
        event_bus: EventBus,
        plugin_registry: PluginRegistry,
        repository: IRepository,
        artifact_store: Any = None,
        browser_manager: Any = None,
        vault: Any = None,
    ):
        self.event_bus = event_bus
        self.plugin_registry = plugin_registry
        self.repository = repository
        self.artifact_store = artifact_store
        self.browser_manager = browser_manager
        self.vault = vault
        self.state_manager = StateManager(repository)
        self.executor = StepExecutor(event_bus)

    async def run_workflow(
        self,
        dag: CompiledDAG,
        job_id: str,
        variable_overrides: dict[str, Any] | None = None,
        account_ids: dict[str, str] | None = None,
    ) -> JobContext:
        """Execute a compiled DAG from start to finish."""
        merged_variables = dict(dag.variables)
        if variable_overrides:
            merged_variables.update(variable_overrides)

        job_context = JobContext(
            job_id=job_id,
            workflow_name=dag.name,
            variables=merged_variables,
            account_ids=account_ids or {},
        )

        total_steps = len(dag.nodes)
        start_time = time.monotonic()

        await self.event_bus.publish(
            JobStarted(job_id=job_id, workflow_name=dag.name, total_steps=total_steps)
        )
        await self.state_manager.init_job(job_id, dag.name, total_steps)

        shared_scratch: dict[str, Any] = {}

        for layer in dag.execution_layers:
            # We run all independent steps in the current topological layer concurrently
            async def _run_layer_step(step_name: str) -> tuple[str, Any, float]:
                step_ast = dag.nodes[step_name]
                step_cls = self.plugin_registry.get_step(step_ast.uses)
                if not step_cls:
                    raise OrchestrationError(
                        f"Step '{step_name}' references unregistered plugin step: '{step_ast.uses}'"
                    )

                step_instance = step_cls()

                # Collect output artifacts from all prerequisite parent steps
                inputs = []
                for parent_name in dag.reverse_adjacency.get(step_name, []):
                    inputs.extend(job_context.artifacts.get(parent_name, []))

                step_ctx = StepContext(
                    job_id=job_id,
                    workflow_name=dag.name,
                    step_name=step_name,
                    config=step_ast.with_args,
                    inputs=inputs,
                    variables=merged_variables,
                    account_ids=job_context.account_ids,
                    scratch_data=shared_scratch,
                    event_bus=self.event_bus,
                    storage=self.artifact_store,
                    browser=self.browser_manager,
                    vault=self.vault,
                )

                retry_policy = None
                if step_ast.retry_policy:
                    retry_policy = RetryPolicy.model_validate(step_ast.retry_policy)

                step_start = time.monotonic()
                res = await self.executor.execute_step(
                    step_instance, step_ctx, retry_policy=retry_policy
                )
                step_duration = time.monotonic() - step_start
                return step_name, res, step_duration

            layer_tasks = [_run_layer_step(name) for name in layer]
            results = await asyncio.gather(*layer_tasks, return_exceptions=True)

            for item in results:
                if isinstance(item, Exception):
                    err_msg = f"Unhandled exception in step execution layer: {item}"
                    await self.state_manager.complete_job(job_id, "FAILED", err_msg)
                    await self.event_bus.publish(
                        JobFailed(
                            job_id=job_id,
                            workflow_name=dag.name,
                            failed_step="unknown",
                            error_message=err_msg,
                        )
                    )
                    raise OrchestrationError(err_msg) from item

                step_name, result, duration = item
                await self.state_manager.record_step_result(job_id, step_name, result, duration)

                if result.status != StepStatus.SUCCESS:
                    err_msg = result.error_message or f"Step '{step_name}' failed."
                    await self.state_manager.complete_job(job_id, "FAILED", err_msg)
                    await self.event_bus.publish(
                        JobFailed(
                            job_id=job_id,
                            workflow_name=dag.name,
                            failed_step=step_name,
                            error_message=err_msg,
                        )
                    )
                    return job_context

                job_context.add_step_artifacts(step_name, result.output_artifacts)

        total_duration = time.monotonic() - start_time
        await self.state_manager.complete_job(job_id, "SUCCESS")
        await self.event_bus.publish(
            JobCompleted(
                job_id=job_id,
                workflow_name=dag.name,
                duration_seconds=total_duration,
            )
        )
        return job_context
