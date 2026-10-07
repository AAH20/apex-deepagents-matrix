"""Apex_DeepAgents_Matrix: Master DeepAgents Harness & State Machine.

Binds mathematical solvers, causal digital twins, and rollback middleware
into a turnkey agent harness for LangChain and LangGraph ecosystems.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apex_deepagents_matrix.middleware import (
    BlastRadiusExceededError,
    DestructiveActionBlockedError,
    MatrixValidationHook,
)
from apex_deepagents_matrix.rollback import CompensatoryRollbackMiddleware
from apex_deepagents_matrix.solvers import (
    AllocationItem,
    KnapsackResourceAllocator,
    ScheduledTask,
    TopologicalTaskScheduler,
)


@dataclass
class SubAgentTaskResult:
    """Outcome of an isolated sub-agent task execution."""
    task_id: str
    status: str  # "completed", "rolled_back", "failed"
    result_data: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


class DeepAgentsMatrixHarness:
    """Master agent execution harness extending LangChain / LangGraph."""

    def __init__(
        self,
        harness_name: str = "DeepAgents_Matrix_Harness",
        max_blast_radius: float = 25.0,
    ) -> None:
        self.harness_name = harness_name
        self.validation_hook = MatrixValidationHook(max_allowable_blast_radius=max_blast_radius)
        self.rollback_middleware = CompensatoryRollbackMiddleware()
        self.task_history: List[SubAgentTaskResult] = []

    def plan_workflow(self, tasks: List[ScheduledTask]) -> Dict[str, Any]:
        """Compute mathematically optimal execution order and detect cycles."""
        order, makespan, has_cycle = TopologicalTaskScheduler.schedule(tasks)
        if has_cycle:
            raise ValueError("Dependency deadlock detected: task DAG contains a directed cycle.")
        return {
            "execution_order": order,
            "estimated_makespan_sec": makespan,
            "total_tasks": len(tasks),
            "deadlock_free": True,
        }

    def allocate_compute(
        self,
        demands: List[AllocationItem],
        total_capacity: int,
    ) -> Dict[str, Any]:
        """Solve knapsack resource allocation across agent sub-tasks."""
        optimal_val, selected_items, elapsed_us = KnapsackResourceAllocator.allocate(demands, total_capacity)
        return {
            "optimal_value": optimal_val,
            "allocated_items_count": len(selected_items),
            "selected_item_ids": [it.item_id for it in selected_items],
            "solver_latency_us": round(elapsed_us, 2),
        }

    def execute_guarded_action(
        self,
        tool_name: str,
        target_resource_id: str,
        payload: Dict[str, Any],
        simulated_blast_radius: float = 1.0,
    ) -> Dict[str, Any]:
        """Execute a tool action with pre-condition verification and transaction logging."""
        t0 = time.perf_counter()

        # Step 1: Pre-execution validation
        self.validation_hook.before_tool_execution(
            tool_name=tool_name,
            arguments=payload,
            simulated_blast_radius=simulated_blast_radius,
        )

        # Step 2: Record to transactional rollback journal
        tx = self.rollback_middleware.record_action(
            tool_name=tool_name,
            target_resource_id=target_resource_id,
            payload=payload,
        )

        elapsed = (time.perf_counter() - t0) * 1000.0
        return {
            "status": "executed",
            "transaction_id": tx.action_id,
            "tool_name": tool_name,
            "target": target_resource_id,
            "overhead_ms": round(elapsed, 3),
        }

    def rollback_all(self) -> List[Dict[str, Any]]:
        """Trigger compensatory rollback sequence in reverse chronological order."""
        seq = self.rollback_middleware.generate_rollback_sequence()
        self.rollback_middleware.clear()
        return seq
