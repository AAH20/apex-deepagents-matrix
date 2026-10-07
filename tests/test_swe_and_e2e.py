"""Unit tests for SWE Benchmark and Agentic E2E Testing Framework in apex-deepagents-matrix.

Pure Python 3.10+ standard library. Zero external dependencies.
Incubated under Apex Growth Systems LLC - Sole Managing Member: Ahmed Hassan.
"""

from __future__ import annotations

import unittest
from typing import Dict, Tuple

from apex_deepagents_matrix.eval.e2e_framework import (
    E2EAgenticTestingFramework,
    E2EStep,
    build_standard_e2e_test_suite,
)
from apex_deepagents_matrix.eval.evolution import (
    AgentGenome,
    DynamicAgentEvolutionEngine,
)
from apex_deepagents_matrix.eval.swe_harness import (
    SWEEvalSummary,
    SWEEvaluationHarness,
    SWEIssue,
    VirtualRepoSandbox,
    create_standard_swe_benchmark_dataset,
)


class TestVirtualRepoSandbox(unittest.TestCase):
    """Test virtual filesystem operations and rollbacks."""

    def test_apply_and_rollback(self):
        sandbox = VirtualRepoSandbox({"main.py": "def foo(): return 1\n"})
        self.assertEqual(sandbox.files["main.py"], "def foo(): return 1\n")

        sandbox.apply_file_content("main.py", "def foo(): return 2\n")
        self.assertEqual(sandbox.files["main.py"], "def foo(): return 2\n")
        self.assertIn("-def foo(): return 1", sandbox.get_diff())

        sandbox.rollback_to_snapshot()
        self.assertEqual(sandbox.files["main.py"], "def foo(): return 1\n")
        self.assertEqual(sandbox.get_diff(), "")


class TestSWEEvaluationHarness(unittest.TestCase):
    """Test SWE-bench task execution and verification engine."""

    def setUp(self):
        self.harness = SWEEvaluationHarness()
        self.issues = create_standard_swe_benchmark_dataset()

    def test_benchmark_dataset_loaded(self):
        self.assertGreaterEqual(len(self.issues), 3)
        issue_ids = [i.issue_id for i in self.issues]
        self.assertIn("SWE-001-KNAPSACK-BOUNDARY", issue_ids)
        self.assertIn("SWE-002-DAG-DIAMOND-CYCLE", issue_ids)
        self.assertIn("SWE-003-ROLLBACK-LIFO-INVERSION", issue_ids)

    def test_evaluate_successful_patches(self):
        def perfect_solver(issue: SWEIssue) -> Tuple[str, Dict[str, str]]:
            if "KNAPSACK" in issue.issue_id:
                return ("diff_1", {"allocator.py": "def can_allocate(item_weight, remaining_cap):\n    return item_weight <= remaining_cap\n"})
            elif "DAG" in issue.issue_id:
                return ("diff_2", {"dag.py": """def has_cycle(nodes, edges):
    from collections import deque, defaultdict
    in_deg = {n: 0 for n in nodes}
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        in_deg[v] = in_deg.get(v, 0) + 1
    q = deque([n for n in nodes if in_deg[n] == 0])
    visited = 0
    while q:
        u = q.popleft()
        visited += 1
        for v in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                q.append(v)
    return visited < len(nodes)
"""})
            elif "ROLLBACK" in issue.issue_id:
                return ("diff_3", {"rollback.py": "def get_rollback_sequence(actions):\n    return list(reversed(actions))\n"})
            return ("empty", {})

        summary = self.harness.run_benchmark_suite(self.issues, perfect_solver, k_attempts=1)
        self.assertEqual(summary.total_issues, len(self.issues))
        self.assertEqual(summary.resolved_count, len(self.issues))
        self.assertEqual(summary.pass_at_1, 1.0)
        self.assertEqual(summary.rollback_rate, 0.0)

    def test_evaluate_broken_patch_triggers_rollback(self):
        def bad_solver(issue: SWEIssue) -> Tuple[str, Dict[str, str]]:
            # Deliberate bad patch that fails tests
            return ("bad_diff", {"allocator.py": "def can_allocate(item_weight, remaining_cap):\n    return False\n"})

        issue = self.issues[0]
        result = self.harness.evaluate_patch(issue, bad_solver)
        self.assertFalse(result.resolved)
        self.assertTrue(result.rollback_occurred)

    def test_syntax_error_patch_rejection(self):
        def syntax_error_solver(issue: SWEIssue) -> Tuple[str, Dict[str, str]]:
            return ("syntax_err", {"allocator.py": "def broken(:"})

        issue = self.issues[0]
        result = self.harness.evaluate_patch(issue, syntax_error_solver)
        self.assertFalse(result.resolved)
        self.assertFalse(result.syntax_valid)
        self.assertTrue(result.rollback_occurred)


class TestE2EAgenticTestingFramework(unittest.TestCase):
    """Test agentic multi-turn scenario execution, invariants, and rollback fidelity."""

    def setUp(self):
        self.framework = E2EAgenticTestingFramework(default_max_blast_radius=25.0)
        self.scenarios = build_standard_e2e_test_suite()

    def test_standard_scenarios_all_pass(self):
        for sc_id, name, steps, invariants in self.scenarios:
            report = self.framework.run_scenario(
                scenario_id=sc_id,
                name=name,
                steps=steps,
                invariants=invariants,
            )
            self.assertTrue(report.passed, f"Scenario {sc_id} failed: {report.invariant_violations}")
            if report.rollback_triggered:
                self.assertEqual(report.rollback_fidelity, 1.0, f"Scenario {sc_id} had incomplete rollback fidelity")

    def test_fault_injection_rollback_fidelity(self):
        # Explicit test for 100% compensatory rollback fidelity
        steps = [
            E2EStep(
                step_id="act_1",
                action_type="execute_guarded_action",
                payload={"tool_name": "provision_vm", "target": "vm_1"},
                simulated_blast_radius=2.0,
            ),
            E2EStep(
                step_id="act_2",
                action_type="execute_guarded_action",
                payload={"tool_name": "mount_storage", "target": "vol_1"},
                simulated_blast_radius=3.0,
            ),
            E2EStep(
                step_id="act_3",
                action_type="execute_guarded_action",
                payload={"tool_name": "exceed_blast_threshold", "target": "core_switch"},
                inject_fault="blast_breach",
                expected_status="rolled_back",
            ),
        ]
        report = self.framework.run_scenario("FAULT-001", "Fault Injection Fidelity Test", steps)
        self.assertTrue(report.passed)
        self.assertTrue(report.rollback_triggered)
        self.assertEqual(report.rollback_fidelity, 1.0)
        self.assertEqual(report.completed_steps, 2)


class TestDynamicAgentEvolutionEngine(unittest.TestCase):
    """Test agent parameter mutation, fitness evaluation, and multi-generation loop."""

    def setUp(self):
        self.engine = DynamicAgentEvolutionEngine(seed=123)

    def test_genome_mutation_bounds(self):
        parent = AgentGenome(genome_id="g_root", generation=0, max_blast_radius=25.0)
        child = parent.mutate(mutation_rate=1.0)

        self.assertEqual(child.generation, 1)
        self.assertGreaterEqual(child.max_blast_radius, 10.0)
        self.assertLessEqual(child.max_blast_radius, 50.0)
        self.assertGreaterEqual(child.solver_capacity_multiplier, 0.75)
        self.assertLessEqual(child.solver_capacity_multiplier, 1.5)

    def test_single_genome_evaluation(self):
        genome = AgentGenome(genome_id="g_eval", generation=0, max_blast_radius=30.0)
        fitness = self.engine.evaluate_genome(genome)

        self.assertGreater(fitness, 0.5)
        self.assertEqual(genome.swe_pass_rate, 1.0)
        self.assertEqual(genome.e2e_pass_rate, 1.0)
        self.assertEqual(genome.rollback_fidelity, 1.0)

    def test_multi_generation_evolution_loop(self):
        best_genome, history = self.engine.run_evolution_loop(
            generations=3,
            population_size=3,
            mutation_rate=0.4,
        )

        self.assertEqual(len(history), 3)
        self.assertIsNotNone(best_genome)
        self.assertGreaterEqual(best_genome.fitness_score, 0.8)
        self.assertIn("Core Invariant", best_genome.prompt_guidance)


if __name__ == "__main__":
    unittest.main()
