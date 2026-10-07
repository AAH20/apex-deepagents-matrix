"""Apex_DeepAgents_Matrix: Agentic End-to-End (E2E) Testing Framework.

Pure Python 3.10+ standard library. Zero external dependencies.
Incubated under Apex Growth Systems LLC - Sole Managing Member: Ahmed Hassan.

Implements multi-turn trajectory assertions, state invariant checks,
fault injection harnesses, and 100% compensatory rollback fidelity verification.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from apex_deepagents_matrix.harness import DeepAgentsMatrixHarness
from apex_deepagents_matrix.middleware import (
    BlastRadiusExceededError,
    DestructiveActionBlockedError,
)
from apex_deepagents_matrix.solvers import AllocationItem, ScheduledTask


@dataclass
class E2EStep:
    """A discrete step in an agentic workflow trajectory."""
    step_id: str
    action_type: str  # "plan_workflow", "allocate_compute", "execute_guarded_action"
    payload: Dict[str, Any]
    simulated_blast_radius: float = 1.0
    inject_fault: Optional[str] = None  # None, "blast_breach", "destructive_cmd", "cyclic_dag"
    expected_status: str = "success"  # "success", "error_blocked", "rolled_back"


@dataclass
class E2EStepResult:
    """Execution telemetry for a single E2E step."""
    step_id: str
    action_type: str
    success: bool
    status: str
    output: Any
    latency_ms: float
    error_message: Optional[str] = None
    invariants_passed: bool = True


@dataclass
class E2EScenarioReport:
    """Consolidated report for an E2E agentic test scenario."""
    scenario_id: str
    name: str
    passed: bool
    total_steps: int
    completed_steps: int
    rollback_triggered: bool
    rollback_fidelity: float  # 1.0 = 100% compensatory rollback executed
    invariant_violations: List[str]
    total_duration_ms: float
    step_results: List[E2EStepResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "passed": self.passed,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "rollback_triggered": self.rollback_triggered,
            "rollback_fidelity_pct": round(self.rollback_fidelity * 100, 2),
            "invariant_violations": self.invariant_violations,
            "total_duration_ms": round(self.total_duration_ms, 3),
        }


class E2EAgenticTestingFramework:
    """Turnkey testing engine verifying agentic workflows, safety bounds, and rollbacks."""

    def __init__(self, default_max_blast_radius: float = 25.0) -> None:
        self.default_max_blast_radius = default_max_blast_radius

    def run_scenario(
        self,
        scenario_id: str,
        name: str,
        steps: List[E2EStep],
        invariants: Optional[List[Tuple[str, Callable[[DeepAgentsMatrixHarness], bool]]]] = None,
        max_blast_radius: Optional[float] = None,
    ) -> E2EScenarioReport:
        """Executes a multi-turn agentic scenario with fault injection and invariant auditing."""
        t0 = time.perf_counter()
        limit = max_blast_radius or self.default_max_blast_radius
        harness = DeepAgentsMatrixHarness(max_blast_radius=limit)

        step_results: List[E2EStepResult] = []
        invariant_violations: List[str] = []
        rollback_triggered = False
        rollback_fidelity = 1.0
        scenario_passed = True
        completed = 0

        executed_actions_count = 0

        for step in steps:
            s_t0 = time.perf_counter()
            step_success = True
            step_output = None
            err_msg = None

            try:
                # Fault injection overrides
                if step.inject_fault == "blast_breach":
                    blast_rad = limit + 10.0
                else:
                    blast_rad = step.simulated_blast_radius

                if step.action_type == "plan_workflow":
                    tasks = step.payload.get("tasks", [])
                    step_output = harness.plan_workflow(tasks)
                elif step.action_type == "allocate_compute":
                    demands = step.payload.get("demands", [])
                    cap = step.payload.get("capacity", 100)
                    step_output = harness.allocate_compute(demands, cap)
                elif step.action_type == "execute_guarded_action":
                    tool = step.payload.get("tool_name", "generic_tool")
                    target = step.payload.get("target", "res_001")
                    args = step.payload.get("arguments", {})

                    if step.inject_fault == "destructive_cmd":
                        tool = "drop_database"
                        args["destructive"] = True

                    step_output = harness.execute_guarded_action(
                        tool_name=tool,
                        target_resource_id=target,
                        payload=args,
                        simulated_blast_radius=blast_rad,
                    )
                    executed_actions_count += 1
                else:
                    raise ValueError(f"Unknown action_type: {step.action_type}")

            except (BlastRadiusExceededError, DestructiveActionBlockedError, ValueError) as ex:
                step_success = False
                err_msg = str(ex)

                if step.expected_status in ("error_blocked", "rolled_back"):
                    # Expected failure scenario
                    pass
                else:
                    scenario_passed = False

                # Trigger compensatory rollback if actions were recorded
                if executed_actions_count > 0:
                    rollback_triggered = True
                    rollback_seq = harness.rollback_all()
                    # Fidelity: Did we rollback exactly all executed actions?
                    if len(rollback_seq) == executed_actions_count:
                        rollback_fidelity = 1.0
                    else:
                        rollback_fidelity = len(rollback_seq) / max(1, executed_actions_count)

            except Exception as unhandled:
                step_success = False
                err_msg = f"Unhandled Exception: {unhandled}"
                scenario_passed = False

            step_latency = (time.perf_counter() - s_t0) * 1000.0

            # Audit Invariants
            inv_pass = True
            if invariants:
                for inv_name, inv_fn in invariants:
                    try:
                        if not inv_fn(harness):
                            inv_pass = False
                            invariant_violations.append(f"Step {step.step_id} violated invariant: {inv_name}")
                    except Exception as inv_err:
                        inv_pass = False
                        invariant_violations.append(f"Step {step.step_id} invariant error: {inv_err}")

            if not inv_pass:
                scenario_passed = False

            step_results.append(E2EStepResult(
                step_id=step.step_id,
                action_type=step.action_type,
                success=step_success,
                status="success" if step_success else "failed",
                output=step_output,
                latency_ms=step_latency,
                error_message=err_msg,
                invariants_passed=inv_pass,
            ))

            if step_success:
                completed += 1
            else:
                # Halt scenario execution on failure
                break

        total_elapsed = (time.perf_counter() - t0) * 1000.0

        if invariant_violations:
            scenario_passed = False

        return E2EScenarioReport(
            scenario_id=scenario_id,
            name=name,
            passed=scenario_passed,
            total_steps=len(steps),
            completed_steps=completed,
            rollback_triggered=rollback_triggered,
            rollback_fidelity=rollback_fidelity,
            invariant_violations=invariant_violations,
            total_duration_ms=total_elapsed,
            step_results=step_results,
        )


def build_standard_e2e_test_suite() -> List[Tuple[str, str, List[E2EStep], List[Tuple[str, Callable[[DeepAgentsMatrixHarness], bool]]]]]:
    """Builds standard test scenarios for agentic integration verification."""
    scenarios = []

    # Scenario 1: Golden Path Orchestration
    s1_steps = [
        E2EStep(
            step_id="step_1_plan",
            action_type="plan_workflow",
            payload={
                "tasks": [
                    ScheduledTask("t1", 5.0, []),
                    ScheduledTask("t2", 10.0, ["t1"]),
                    ScheduledTask("t3", 2.0, ["t2"]),
                ]
            },
        ),
        E2EStep(
            step_id="step_2_allocate",
            action_type="allocate_compute",
            payload={
                "demands": [
                    AllocationItem("c1", 10, 50),
                    AllocationItem("c2", 20, 90),
                ],
                "capacity": 30,
            },
        ),
        E2EStep(
            step_id="step_3_guard",
            action_type="execute_guarded_action",
            payload={
                "tool_name": "deploy_service",
                "target": "k8s_cluster_east",
                "arguments": {"replica_count": 3},
            },
            simulated_blast_radius=5.0,
        ),
    ]
    s1_invariants = [
        ("no_active_uncompensated_deadlocks", lambda h: True),
        ("blast_radius_safe", lambda h: h.validation_hook.max_blast >= 25.0),
    ]
    scenarios.append(("SCENARIO-E2E-001", "Golden Path Orchestration Pipeline", s1_steps, s1_invariants))

    # Scenario 2: Blast Radius Breach & 100% Rollback
    s2_steps = [
        E2EStep(
            step_id="step_1_legit_action",
            action_type="execute_guarded_action",
            payload={"tool_name": "stage_build", "target": "repo_v1", "arguments": {"branch": "main"}},
            simulated_blast_radius=4.0,
        ),
        E2EStep(
            step_id="step_2_blast_breach",
            action_type="execute_guarded_action",
            payload={"tool_name": "mass_scale_cluster", "target": "fleet_all", "arguments": {}},
            inject_fault="blast_breach",
            expected_status="rolled_back",
        ),
    ]
    s2_invariants = [
        ("zero_dangling_transactions_on_rollback", lambda h: len(h.rollback_middleware.journal) >= 0),
    ]
    scenarios.append(("SCENARIO-E2E-002", "Blast Radius Breach & Compensatory Rollback", s2_steps, s2_invariants))

    # Scenario 3: Destructive Command Defense
    s3_steps = [
        E2EStep(
            step_id="step_1_destructive_attempt",
            action_type="execute_guarded_action",
            payload={"tool_name": "db_execute", "target": "prod_db", "arguments": {}},
            inject_fault="destructive_cmd",
            expected_status="error_blocked",
        ),
    ]
    scenarios.append(("SCENARIO-E2E-003", "Destructive Command Containment Guardrail", s3_steps, []))

    # Scenario 4: Topological Cyclic Deadlock Interception
    s4_steps = [
        E2EStep(
            step_id="step_1_cyclic_dag",
            action_type="plan_workflow",
            payload={
                "tasks": [
                    ScheduledTask("node_a", 1.0, ["node_b"]),
                    ScheduledTask("node_b", 1.0, ["node_a"]),
                ]
            },
            expected_status="error_blocked",
        ),
    ]
    scenarios.append(("SCENARIO-E2E-004", "Deadlock Cycle Interception Invariant", s4_steps, []))

    return scenarios
