"""Unit tests for deterministic mathematical solvers."""

import unittest

from apex_deepagents_matrix.solvers import (
    AllocationItem,
    KnapsackResourceAllocator,
    ScheduledTask,
    TopologicalTaskScheduler,
)


class TestSolvers(unittest.TestCase):
    def test_knapsack_allocator(self) -> None:
        items = [
            AllocationItem(item_id="gpu_task_1", weight=20, value=100.0),
            AllocationItem(item_id="gpu_task_2", weight=30, value=120.0),
            AllocationItem(item_id="gpu_task_3", weight=10, value=60.0),
        ]
        # Total capacity 50GB VRAM -> Best: task 1 (20) + task 2 (30) = 220.0 OR task 1 + task 2 = 220.0
        val, selected, us = KnapsackResourceAllocator.allocate(items, capacity=50)
        self.assertEqual(val, 220.0)
        self.assertEqual(len(selected), 2)
        self.assertLess(us, 5000.0)  # Microsecond latency assertion

    def test_topological_scheduler(self) -> None:
        tasks = [
            ScheduledTask(task_id="extract_logs", duration_estimate=2.0),
            ScheduledTask(task_id="parse_traces", duration_estimate=1.5, dependencies=["extract_logs"]),
            ScheduledTask(task_id="generate_fix", duration_estimate=3.0, dependencies=["parse_traces"]),
        ]
        order, makespan, has_cycle = TopologicalTaskScheduler.schedule(tasks)
        self.assertFalse(has_cycle)
        self.assertEqual(order, ["extract_logs", "parse_traces", "generate_fix"])
        self.assertAlmostEqual(makespan, 6.5)

    def test_cycle_detection(self) -> None:
        tasks = [
            ScheduledTask(task_id="a", duration_estimate=1.0, dependencies=["b"]),
            ScheduledTask(task_id="b", duration_estimate=1.0, dependencies=["a"]),
        ]
        _, _, has_cycle = TopologicalTaskScheduler.schedule(tasks)
        self.assertTrue(has_cycle)


if __name__ == "__main__":
    unittest.main()
