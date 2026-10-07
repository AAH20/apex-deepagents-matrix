"""End-to-End Walkthrough: SWE Benchmark Evaluation & Evolution in apex-deepagents-matrix.

Demonstrates how to evaluate agents against SWE tasks, run multi-turn E2E trajectory
testing with fault injection, and dynamically evolve agent parameters.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apex_deepagents_matrix.eval import (
    DynamicAgentEvolutionEngine,
    E2EAgenticTestingFramework,
    SWEEvaluationHarness,
    build_standard_e2e_test_suite,
    create_standard_swe_benchmark_dataset,
)


def main():
    print("=" * 72)
    print(" Apex_DeepAgents_Matrix: SWE Benchmark & E2E Testing Walkthrough")
    print("=" * 72)

    # Step 1: Run SWE Benchmark Suite
    print("\n[Step 1] Running SWE-bench Style Evaluation...")
    swe_harness = SWEEvaluationHarness()
    issues = create_standard_swe_benchmark_dataset()

    def agent_patch_synthesizer(issue):
        print(f"  -> Agent tackling issue: {issue.issue_id} - '{issue.problem_statement[:45]}...'")
        if "KNAPSACK" in issue.issue_id:
            diff = "--- a/allocator.py\n+++ b/allocator.py\n@@ -2,2 +2,2 @@\n-    return item_weight < remaining_cap\n+    return item_weight <= remaining_cap\n"
            files = {"allocator.py": "def can_allocate(item_weight, remaining_cap):\n    return item_weight <= remaining_cap\n"}
            return diff, files
        elif "DAG" in issue.issue_id:
            files = {"dag.py": """def has_cycle(nodes, edges):
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
"""}
            return "diff_dag", files
        elif "ROLLBACK" in issue.issue_id:
            files = {"rollback.py": "def get_rollback_sequence(actions):\n    return list(reversed(actions))\n"}
            return "diff_rollback", files
        return "", {}

    summary = swe_harness.run_benchmark_suite(issues, agent_patch_synthesizer, k_attempts=1)
    print(f"  SWE Benchmark Pass@1: {summary.pass_at_1 * 100:.1f}%")
    print(f"  SWE Rollback Rate on Bad Patches: {summary.rollback_rate * 100:.1f}%")
    print(f"  Mean Evaluation Latency: {summary.mean_resolution_time_ms:.3f} ms")

    # Step 2: Run Agentic E2E Testing Suite
    print("\n[Step 2] Executing Agentic Multi-Turn E2E Testing Scenarios...")
    framework = E2EAgenticTestingFramework(default_max_blast_radius=25.0)
    scenarios = build_standard_e2e_test_suite()

    for sc_id, name, steps, invariants in scenarios:
        rep = framework.run_scenario(sc_id, name, steps, invariants)
        status = "PASSED" if rep.passed else "FAILED"
        print(f"  [{status}] {sc_id}: {name}")
        print(f"       Steps: {rep.completed_steps}/{rep.total_steps} | Rollback Fidelity: {rep.rollback_fidelity * 100:.1f}% | Latency: {rep.total_duration_ms:.3f} ms")

    # Step 3: Dynamic Evolution Engine
    print("\n[Step 3] Running Dynamic Agent Evolution Engine (5 Generations)...")
    evolution = DynamicAgentEvolutionEngine(seed=42)
    best_genome, history = evolution.run_evolution_loop(generations=5, population_size=4, mutation_rate=0.35)

    print(f"  Optimal Genome: {best_genome.genome_id}")
    print(f"  Composite Fitness: {best_genome.fitness_score:.4f}")
    print(f"  Tuned Max Blast Radius: {best_genome.max_blast_radius}")
    print(f"  Evolved Guidance Prompt: {best_genome.prompt_guidance}")
    print("=" * 72)


if __name__ == "__main__":
    main()
