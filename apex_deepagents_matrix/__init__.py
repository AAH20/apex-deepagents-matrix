"""Apex_DeepAgents_Matrix: Turnkey Deterministic Kernel & Rollback Harness for LangChain.

Pure Python 3.10+ standard library. Zero external dependencies.
Incubated under Apex Growth Systems LLC - Sole Managing Member: Ahmed Hassan.
"""

from apex_deepagents_matrix.eval import (
    AgentGenome,
    DynamicAgentEvolutionEngine,
    E2EAgenticTestingFramework,
    E2EScenarioReport,
    E2EStep,
    E2EStepResult,
    EvolutionProgress,
    SWEEvalSummary,
    SWEEvaluationHarness,
    SWEIssue,
    SWEPatchResult,
    VirtualRepoSandbox,
    build_standard_e2e_test_suite,
    create_standard_swe_benchmark_dataset,
)
from apex_deepagents_matrix.harness import (
    DeepAgentsMatrixHarness,
    SubAgentTaskResult,
)
from apex_deepagents_matrix.middleware import (
    BlastRadiusExceededError,
    DestructiveActionBlockedError,
    MatrixValidationHook,
)
from apex_deepagents_matrix.rollback import (
    CompensatoryRollbackMiddleware,
    TransactionalAction,
)
from apex_deepagents_matrix.solvers import (
    AllocationItem,
    KnapsackResourceAllocator,
    ScheduledTask,
    TopologicalTaskScheduler,
)

__version__ = "1.1.0"
__author__ = "Ahmed Hassan"
__company__ = "Apex Growth Systems LLC"

__all__ = [
    "__version__",
    "__author__",
    "__company__",
    "DeepAgentsMatrixHarness",
    "SubAgentTaskResult",
    "MatrixValidationHook",
    "BlastRadiusExceededError",
    "DestructiveActionBlockedError",
    "CompensatoryRollbackMiddleware",
    "TransactionalAction",
    "KnapsackResourceAllocator",
    "TopologicalTaskScheduler",
    "AllocationItem",
    "ScheduledTask",
    # Evaluation & Evolution
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
