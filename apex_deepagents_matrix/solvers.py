"""Apex_DeepAgents_Matrix: Deterministic Mathematical Solvers & Optimization Kernels.

Pure Python 3.10+ standard library. Zero external dependencies.
Replaces hallucinated LLM planning loops with exact mathematical algorithms.
Incubated under Apex Growth Systems LLC - Sole Managing Member: Ahmed Hassan.
"""

from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class AllocationItem:
    """Resource demand item to be packed or scheduled."""
    item_id: str
    weight: int  # e.g., GPU VRAM in GB, CPU cores, or token capacity
    value: float  # e.g., task priority, throughput SLA, or revenue yield
    metadata: Dict[str, Any] = field(default_factory=dict)


class KnapsackResourceAllocator:
    """Exact 0/1 Knapsack dynamic programming solver for agent compute allocation."""

    @classmethod
    def allocate(
        cls,
        items: List[AllocationItem],
        capacity: int,
    ) -> Tuple[float, List[AllocationItem], float]:
        """Compute optimal resource subset under hard capacity constraints.

        Returns (optimal_value, selected_items, execution_time_us).
        """
        t0 = time.perf_counter()
        n = len(items)
        if n == 0 or capacity <= 0:
            return 0.0, [], (time.perf_counter() - t0) * 1_000_000.0

        # Memory-efficient 1D DP array
        dp = [0.0] * (capacity + 1)
        # Track items for reconstruction: item_index -> capacity -> bool
        keep = [[False] * (capacity + 1) for _ in range(n)]

        for i in range(n):
            w = items[i].weight
            v = items[i].value
            for c in range(capacity, w - 1, -1):
                if dp[c - w] + v > dp[c]:
                    dp[c] = dp[c - w] + v
                    keep[i][c] = True

        # Reconstruct selected items
        selected: List[AllocationItem] = []
        rem_cap = capacity
        for i in range(n - 1, -1, -1):
            if keep[i][rem_cap]:
                selected.append(items[i])
                rem_cap -= items[i].weight

        elapsed_us = (time.perf_counter() - t0) * 1_000_000.0
        return dp[capacity], selected, elapsed_us


@dataclass
class ScheduledTask:
    """Sub-agent task node in a dependency DAG."""
    task_id: str
    duration_estimate: float
    dependencies: List[str] = field(default_factory=list)


class TopologicalTaskScheduler:
    """Deterministic scheduling kernel calculating critical path and topological task order."""

    @classmethod
    def schedule(cls, tasks: List[ScheduledTask]) -> Tuple[List[str], float, bool]:
        """Kahn's algorithm with critical path calculation.

        Returns (topological_order, makespan, has_cycle).
        """
        task_map = {t.task_id: t for t in tasks}
        in_degree = {t.task_id: 0 for t in tasks}
        dependents: Dict[str, List[str]] = collections.defaultdict(list)

        for t in tasks:
            for dep in t.dependencies:
                if dep in task_map:
                    in_degree[t.task_id] += 1
                    dependents[dep].append(t.task_id)

        queue = collections.deque([tid for tid, deg in in_degree.items() if deg == 0])
        order: List[str] = []
        earliest_finish = {tid: 0.0 for tid in task_map}

        while queue:
            curr = queue.popleft()
            order.append(curr)
            curr_task = task_map[curr]
            curr_finish = earliest_finish[curr] + curr_task.duration_estimate

            for dep in dependents[curr]:
                in_degree[dep] -= 1
                if curr_finish > earliest_finish[dep]:
                    earliest_finish[dep] = curr_finish
                if in_degree[dep] == 0:
                    queue.append(dep)

        has_cycle = len(order) < len(tasks)
        makespan = max((earliest_finish[tid] + task_map[tid].duration_estimate for tid in task_map), default=0.0)
        return order, makespan, has_cycle
