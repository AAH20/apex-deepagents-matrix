"""Apex_DeepAgents_Matrix Evaluation and Evolution Suite.

Pure Python 3.10+ standard library. Zero external dependencies.
Incubated under Apex Growth Systems LLC - Sole Managing Member: Ahmed Hassan.
"""

from apex_deepagents_matrix.eval.e2e_framework import (
    E2EAgenticTestingFramework,
    E2EScenarioReport,
    E2EStep,
    E2EStepResult,
    build_standard_e2e_test_suite,
)
from apex_deepagents_matrix.eval.evolution import (
    AgentGenome,
    DynamicAgentEvolutionEngine,
    EvolutionProgress,
)
from apex_deepagents_matrix.eval.swe_harness import (
    SWEEvalSummary,
    SWEEvaluationHarness,
    SWEIssue,
    SWEPatchResult,
    VirtualRepoSandbox,
    create_standard_swe_benchmark_dataset,
)

__all__ = [
    "SWEIssue",
    "SWEPatchResult",
    "SWEEvalSummary",
    "VirtualRepoSandbox",
    "SWEEvaluationHarness",
    "create_standard_swe_benchmark_dataset",
    "E2EStep",
    "E2EStepResult",
    "E2EScenarioReport",
    "E2EAgenticTestingFramework",
    "build_standard_e2e_test_suite",
    "AgentGenome",
    "EvolutionProgress",
    "DynamicAgentEvolutionEngine",
]
