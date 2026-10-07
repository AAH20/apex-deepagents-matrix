"""Unit tests for the master DeepAgents harness and rollback middleware."""

import unittest

from apex_deepagents_matrix.harness import DeepAgentsMatrixHarness
from apex_deepagents_matrix.middleware import (
    BlastRadiusExceededError,
    DestructiveActionBlockedError,
)
from apex_deepagents_matrix.solvers import AllocationItem, ScheduledTask


class TestHarness(unittest.TestCase):
    def setUp(self) -> None:
        self.harness = DeepAgentsMatrixHarness(max_blast_radius=20.0)

    def test_plan_workflow(self) -> None:
        tasks = [
            ScheduledTask(task_id="t1", duration_estimate=1.0),
            ScheduledTask(task_id="t2", duration_estimate=2.0, dependencies=["t1"]),
        ]
        res = self.harness.plan_workflow(tasks)
        self.assertTrue(res["deadlock_free"])
        self.assertEqual(res["execution_order"], ["t1", "t2"])

    def test_compute_allocation(self) -> None:
        items = [
            AllocationItem(item_id="i1", weight=10, value=50.0),
            AllocationItem(item_id="i2", weight=15, value=70.0),
        ]
        res = self.harness.allocate_compute(items, total_capacity=20)
        self.assertEqual(res["optimal_value"], 70.0)
        self.assertEqual(res["allocated_items_count"], 1)

    def test_guarded_action_and_rollback(self) -> None:
        res = self.harness.execute_guarded_action(
            tool_name="cordon_node",
            target_resource_id="node_01",
            payload={"reason": "maintenance"},
            simulated_blast_radius=5.0,
        )
        self.assertEqual(res["status"], "executed")

        # Rollback sequence generated in reverse
        rb_seq = self.harness.rollback_all()
        self.assertEqual(len(rb_seq), 1)
        self.assertEqual(rb_seq[0]["tool_name"], "uncordon_node")
        self.assertEqual(rb_seq[0]["target_resource_id"], "node_01")

    def test_blast_radius_exceeded(self) -> None:
        with self.assertRaises(BlastRadiusExceededError):
            self.harness.execute_guarded_action(
                tool_name="cordon_node",
                target_resource_id="node_01",
                payload={},
                simulated_blast_radius=50.0,  # Exceeds max 20.0
            )

    def test_destructive_action_blocked(self) -> None:
        with self.assertRaises(DestructiveActionBlockedError):
            self.harness.execute_guarded_action(
                tool_name="drop_database",
                target_resource_id="db_prod",
                payload={},
                simulated_blast_radius=1.0,
            )


if __name__ == "__main__":
    unittest.main()
