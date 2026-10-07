"""Quickstart walkthrough for apex-deepagents-matrix."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apex_deepagents_matrix import (
    AllocationItem,
    DeepAgentsMatrixHarness,
    ScheduledTask,
)

# 1. Initialize master harness
harness = DeepAgentsMatrixHarness(max_blast_radius=25.0)

# 2. Plan a multi-step task DAG with zero-deadlock guarantee
tasks = [
    ScheduledTask(task_id="collect_telemetry", duration_estimate=1.2),
    ScheduledTask(task_id="analyze_bottlenecks", duration_estimate=2.0, dependencies=["collect_telemetry"]),
    ScheduledTask(task_id="apply_patch", duration_estimate=0.8, dependencies=["analyze_bottlenecks"]),
]
plan = harness.plan_workflow(tasks)
print(f"Workflow Order: {plan['execution_order']}")
print(f"Makespan: {plan['estimated_makespan_sec']}s | Deadlock Free: {plan['deadlock_free']}")

# 3. Optimize resource allocation (Knapsack)
demands = [
    AllocationItem(item_id="gpu_agent_1", weight=16, value=90.0),
    AllocationItem(item_id="gpu_agent_2", weight=32, value=150.0),
    AllocationItem(item_id="gpu_agent_3", weight=8, value=40.0),
]
alloc = harness.allocate_compute(demands, total_capacity=40)
print(f"Allocated Agents: {alloc['selected_item_ids']} (Yield: {alloc['optimal_value']}, Time: {alloc['solver_latency_us']} µs)")

# 4. Execute guarded action with automatic rollback journal
result = harness.execute_guarded_action(
    tool_name="cordon_node",
    target_resource_id="bm_h100_node_04",
    payload={"reason": "thermal_throttle"},
    simulated_blast_radius=6.5,
)
print(f"Action Executed: {result['transaction_id']} (Overhead: {result['overhead_ms']} ms)")

# 5. Compensatory rollback sequence
rollback = harness.rollback_all()
print(f"Rollback Sequence: {rollback[0]['tool_name']} on {rollback[0]['target_resource_id']}")
