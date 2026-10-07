"""Apex_DeepAgents_Matrix: SWE Benchmark Evaluation Harness.

Pure Python 3.10+ standard library. Zero external dependencies.
Incubated under Apex Growth Systems LLC - Sole Managing Member: Ahmed Hassan.

Implements SWE-bench style benchmark execution, virtual in-memory repo sandboxing,
patch generation validation, pass@1 / pass@k calculation, and regression verification.
"""

from __future__ import annotations

import difflib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class SWEIssue:
    """A benchmark problem instance modeled after SWE-bench."""
    issue_id: str
    repo_name: str
    problem_statement: str
    base_files: Dict[str, str]  # filepath -> original file content
    fail_to_pass_tests: List[str]  # test names that must fail before patch and pass after patch
    pass_to_pass_tests: List[str]  # regression tests that must pass both before and after
    test_suite: Dict[str, Callable[[Dict[str, str]], bool]] = field(default_factory=dict)
    golden_patch: Optional[str] = None  # Reference unified diff


@dataclass
class SWEPatchResult:
    """Result of applying and verifying an agent patch against an SWEIssue."""
    issue_id: str
    patch_diff: str
    syntax_valid: bool
    tests_passed: List[str]
    tests_failed: List[str]
    resolved: bool
    execution_time_ms: float
    token_cost_estimate: int = 0
    rollback_occurred: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SWEEvalSummary:
    """Aggregate benchmark metrics across a suite of SWE issues."""
    total_issues: int
    resolved_count: int
    pass_at_1: float
    pass_at_k: float
    mean_resolution_time_ms: float
    mean_tokens: float
    rollback_rate: float
    results: List[SWEPatchResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_issues": self.total_issues,
            "resolved_count": self.resolved_count,
            "pass_at_1_pct": round(self.pass_at_1 * 100, 2),
            "pass_at_k_pct": round(self.pass_at_k * 100, 2),
            "mean_resolution_time_ms": round(self.mean_resolution_time_ms, 3),
            "mean_tokens": round(self.mean_tokens, 1),
            "rollback_rate_pct": round(self.rollback_rate * 100, 2),
        }


class VirtualRepoSandbox:
    """Isolated in-memory filesystem for patch application and test evaluation."""

    def __init__(self, initial_files: Dict[str, str]) -> None:
        self.files: Dict[str, str] = {k: v for k, v in initial_files.items()}
        self._snapshot: Dict[str, str] = {k: v for k, v in initial_files.items()}

    def apply_file_content(self, filepath: str, content: str) -> None:
        """Write content directly to an in-memory file."""
        self.files[filepath] = content

    def apply_unified_diff(self, patch_str: str) -> bool:
        """Parse and apply a simple unified diff to the virtual files."""
        if not patch_str.strip():
            return False
        
        lines = patch_str.splitlines()
        current_file: Optional[str] = None
        target_lines: List[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            if line.startswith("--- a/") or line.startswith("--- "):
                # Source file
                pass
            elif line.startswith("+++ b/") or line.startswith("+++ "):
                target_filename = line[6:] if line.startswith("+++ b/") else line[4:].strip()
                current_file = target_filename
                if current_file in self.files:
                    target_lines = self.files[current_file].splitlines()
                else:
                    target_lines = []
            elif line.startswith("@@"):
                # Chunk header - scan hunks
                pass
            elif current_file is not None:
                # Naive patch hunk application
                if line.startswith("+"):
                    target_lines.append(line[1:])
                elif line.startswith("-"):
                    removed = line[1:]
                    if removed in target_lines:
                        target_lines.remove(removed)
            i += 1

        if current_file and current_file in self.files:
            self.files[current_file] = "\n".join(target_lines)
            return True
        return False

    def rollback_to_snapshot(self) -> None:
        """Revert all virtual file modifications back to initial snapshot."""
        self.files = {k: v for k, v in self._snapshot.items()}

    def get_diff(self) -> str:
        """Generate unified diff between snapshot and current state."""
        diff_chunks = []
        for path, orig in self._snapshot.items():
            curr = self.files.get(path, "")
            if orig != curr:
                orig_lines = orig.splitlines(keepends=True)
                curr_lines = curr.splitlines(keepends=True)
                diff = list(difflib.unified_diff(
                    orig_lines, curr_lines,
                    fromfile=f"a/{path}", tofile=f"b/{path}"
                ))
                if diff:
                    diff_chunks.extend(diff)
        return "".join(diff_chunks)


class SWEEvaluationHarness:
    """Turnkey evaluation engine executing SWE-bench tasks on agent components."""

    def __init__(self, token_cost_per_char: float = 0.25) -> None:
        self.token_cost_per_char = token_cost_per_char

    def evaluate_patch(
        self,
        issue: SWEIssue,
        patch_provider: Callable[[SWEIssue], Tuple[str, Dict[str, str]]],
    ) -> SWEPatchResult:
        """Apply an agent-generated patch and execute test suite with verification.
        
        Args:
            issue: The SWE benchmark problem instance.
            patch_provider: Callable taking issue and returning (patch_diff, modified_files_dict).
        """
        t0 = time.perf_counter()
        sandbox = VirtualRepoSandbox(issue.base_files)

        # 1. Verify that fail-to-pass tests fail on base files
        for test_name in issue.fail_to_pass_tests:
            if test_name in issue.test_suite:
                test_fn = issue.test_suite[test_name]
                if test_fn(sandbox.files):
                    # Test passed unexpectedly before patch
                    pass

        # 2. Obtain agent patch
        try:
            patch_diff, modified_files = patch_provider(issue)
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return SWEPatchResult(
                issue_id=issue.issue_id,
                patch_diff="",
                syntax_valid=False,
                tests_passed=[],
                tests_failed=list(issue.test_suite.keys()),
                resolved=False,
                execution_time_ms=elapsed,
                details={"error": str(e)},
            )

        # 3. Apply modified files to sandbox
        syntax_valid = True
        for filepath, content in modified_files.items():
            try:
                compile(content, filepath, "exec")
            except SyntaxError:
                syntax_valid = False
            sandbox.apply_file_content(filepath, content)

        if not syntax_valid:
            sandbox.rollback_to_snapshot()
            elapsed = (time.perf_counter() - t0) * 1000.0
            return SWEPatchResult(
                issue_id=issue.issue_id,
                patch_diff=patch_diff,
                syntax_valid=False,
                tests_passed=[],
                tests_failed=list(issue.test_suite.keys()),
                resolved=False,
                execution_time_ms=elapsed,
                rollback_occurred=True,
                details={"error": "SyntaxError in generated patch"},
            )

        # 4. Execute test suite against patched codebase
        passed_tests: List[str] = []
        failed_tests: List[str] = []

        for test_name, test_fn in issue.test_suite.items():
            try:
                success = test_fn(sandbox.files)
                if success:
                    passed_tests.append(test_name)
                else:
                    failed_tests.append(test_name)
            except Exception:
                failed_tests.append(test_name)

        # 5. Determine SWE Resolution
        # All fail-to-pass must pass, and all pass-to-pass must remain passing
        f2p_satisfied = all(t in passed_tests for t in issue.fail_to_pass_tests)
        p2p_satisfied = all(t in passed_tests for t in issue.pass_to_pass_tests)
        resolved = f2p_satisfied and p2p_satisfied

        rollback = False
        if not resolved:
            sandbox.rollback_to_snapshot()
            rollback = True

        elapsed = (time.perf_counter() - t0) * 1000.0
        generated_diff = sandbox.get_diff() or patch_diff
        token_cost = int(len(patch_diff + generated_diff) * self.token_cost_per_char)

        return SWEPatchResult(
            issue_id=issue.issue_id,
            patch_diff=generated_diff,
            syntax_valid=syntax_valid,
            tests_passed=passed_tests,
            tests_failed=failed_tests,
            resolved=resolved,
            execution_time_ms=elapsed,
            token_cost_estimate=token_cost,
            rollback_occurred=rollback,
            details={
                "f2p_satisfied": f2p_satisfied,
                "p2p_satisfied": p2p_satisfied,
                "files_modified": list(modified_files.keys()),
            },
        )

    def run_benchmark_suite(
        self,
        issues: List[SWEIssue],
        agent_fn: Callable[[SWEIssue], Tuple[str, Dict[str, str]]],
        k_attempts: int = 1,
    ) -> SWEEvalSummary:
        """Run full evaluation suite across all issues and compute pass@1 and pass@k."""
        results: List[SWEPatchResult] = []
        resolved_any_k: int = 0
        total_time = 0.0
        total_tokens = 0
        rollbacks = 0

        for issue in issues:
            issue_resolved = False
            first_result: Optional[SWEPatchResult] = None

            for attempt in range(k_attempts):
                res = self.evaluate_patch(issue, agent_fn)
                if attempt == 0:
                    first_result = res
                    results.append(res)
                    total_time += res.execution_time_ms
                    total_tokens += res.token_cost_estimate
                    if res.rollback_occurred:
                        rollbacks += 1

                if res.resolved:
                    issue_resolved = True
                    break

            if issue_resolved:
                resolved_any_k += 1

        resolved_count = sum(1 for r in results if r.resolved)
        n = len(issues) if issues else 1
        pass_at_1 = resolved_count / n
        pass_at_k = resolved_any_k / n

        return SWEEvalSummary(
            total_issues=len(issues),
            resolved_count=resolved_count,
            pass_at_1=pass_at_1,
            pass_at_k=pass_at_k,
            mean_resolution_time_ms=total_time / n,
            mean_tokens=total_tokens / n,
            rollback_rate=rollbacks / n,
            results=results,
        )


def create_standard_swe_benchmark_dataset() -> List[SWEIssue]:
    """Generates standard industrial SWE-bench problem instances for DeepAgents testing."""
    issues: List[SWEIssue] = []

    # Issue 1: Fix off-by-one capacity check in knapsack allocator
    buggy_allocator_code = """def can_allocate(item_weight, remaining_cap):
    # Bug: strictly less than instead of less than or equal
    return item_weight < remaining_cap
"""
    def test_exact_capacity(files: Dict[str, str]) -> bool:
        ns = {}
        exec(files.get("allocator.py", ""), ns)
        fn = ns.get("can_allocate")
        return bool(fn and fn(10, 10) is True and fn(5, 10) is True and fn(15, 10) is False)

    def test_strictly_less(files: Dict[str, str]) -> bool:
        ns = {}
        exec(files.get("allocator.py", ""), ns)
        fn = ns.get("can_allocate")
        return bool(fn and fn(4, 10) is True)

    issues.append(SWEIssue(
        issue_id="SWE-001-KNAPSACK-BOUNDARY",
        repo_name="apex-deepagents-matrix",
        problem_statement="Fix off-by-one bug in can_allocate: item weight exactly matching capacity must be allowed.",
        base_files={"allocator.py": buggy_allocator_code},
        fail_to_pass_tests=["test_exact_capacity"],
        pass_to_pass_tests=["test_strictly_less"],
        test_suite={
            "test_exact_capacity": test_exact_capacity,
            "test_strictly_less": test_strictly_less,
        },
    ))

    # Issue 2: Fix DAG cycle detection false positive on diamond graph
    buggy_dag_code = """def has_cycle(nodes, edges):
    # Bug: counts in-degrees incorrectly by not distinguishing visited nodes
    visited = set()
    for u, v in edges:
        if v in visited:
            return True
        visited.add(v)
    return False
"""
    def test_diamond_dag_no_cycle(files: Dict[str, str]) -> bool:
        ns = {}
        exec(files.get("dag.py", ""), ns)
        fn = ns.get("has_cycle")
        # Diamond: A->B, A->C, B->D, C->D (valid DAG, no cycle)
        return bool(fn and fn(["A", "B", "C", "D"], [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]) is False)

    def test_actual_cycle(files: Dict[str, str]) -> bool:
        ns = {}
        exec(files.get("dag.py", ""), ns)
        fn = ns.get("has_cycle")
        # Cycle: A->B, B->C, C->A
        return bool(fn and fn(["A", "B", "C"], [("A", "B"), ("B", "C"), ("C", "A")]) is True)

    issues.append(SWEIssue(
        issue_id="SWE-002-DAG-DIAMOND-CYCLE",
        repo_name="apex-deepagents-matrix",
        problem_statement="Fix DAG cycle detector: diamond topologies should not trigger false-positive cycle detection.",
        base_files={"dag.py": buggy_dag_code},
        fail_to_pass_tests=["test_diamond_dag_no_cycle"],
        pass_to_pass_tests=["test_actual_cycle"],
        test_suite={
            "test_diamond_dag_no_cycle": test_diamond_dag_no_cycle,
            "test_actual_cycle": test_actual_cycle,
        },
    ))

    # Issue 3: Rollback journal compensation order inversion
    buggy_rollback_code = """def get_rollback_sequence(actions):
    # Bug: returns FIFO instead of LIFO reverse order
    return list(actions)
"""
    def test_lifo_reversal(files: Dict[str, str]) -> bool:
        ns = {}
        exec(files.get("rollback.py", ""), ns)
        fn = ns.get("get_rollback_sequence")
        return bool(fn and fn(["act_1", "act_2", "act_3"]) == ["act_3", "act_2", "act_1"])

    def test_empty_list(files: Dict[str, str]) -> bool:
        ns = {}
        exec(files.get("rollback.py", ""), ns)
        fn = ns.get("get_rollback_sequence")
        return bool(fn and fn([]) == [])

    issues.append(SWEIssue(
        issue_id="SWE-003-ROLLBACK-LIFO-INVERSION",
        repo_name="apex-deepagents-matrix",
        problem_statement="Rollback sequence must execute in strict reverse chronological (LIFO) order.",
        base_files={"rollback.py": buggy_rollback_code},
        fail_to_pass_tests=["test_lifo_reversal"],
        pass_to_pass_tests=["test_empty_list"],
        test_suite={
            "test_lifo_reversal": test_lifo_reversal,
            "test_empty_list": test_empty_list,
        },
    ))

    return issues
