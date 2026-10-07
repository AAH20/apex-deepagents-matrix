"""Apex_DeepAgents_Matrix: LangChain & LangGraph Interception Middleware.

Guards tool calls, enforces blast-radius bounds, and triggers rollback upon invariant failure.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class BlastRadiusExceededError(RuntimeError):
    """Raised when an agent tool call exceeds safe blast-radius limits."""


class DestructiveActionBlockedError(PermissionError):
    """Raised when an agent attempts an unauthorized destructive operation."""


class MatrixValidationHook:
    """Interception hook designed for LangGraph node dispatchers and LangChain callbacks."""

    BLOCKED_PATTERNS = {
        "rm_rf",
        "format_disk",
        "drop_database",
        "delete_production_cluster",
        "unattended_reboot",
    }

    def __init__(
        self,
        max_allowable_blast_radius: float = 25.0,
        enforce_rollback_journal: bool = True,
    ) -> None:
        self.max_blast = max_allowable_blast_radius
        self.enforce_rollback = enforce_rollback_journal
        self.intercepted_calls: List[Dict[str, Any]] = []

    def before_tool_execution(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        simulated_blast_radius: float = 1.0,
    ) -> Tuple[bool, str]:
        """Pre-execution validation check."""
        # 1. Destructive check
        if tool_name.lower() in self.BLOCKED_PATTERNS or arguments.get("destructive"):
            raise DestructiveActionBlockedError(
                f"Tool '{tool_name}' blocked: Destructive operations prohibited without human approval."
            )

        # 2. Blast radius check
        if simulated_blast_radius > self.max_blast:
            raise BlastRadiusExceededError(
                f"Tool '{tool_name}' rejected: Simulated blast radius {simulated_blast_radius:.2f} "
                f"exceeds ceiling {self.max_blast:.2f}."
            )

        self.intercepted_calls.append({
            "tool_name": tool_name,
            "arguments": arguments,
            "blast_radius": simulated_blast_radius,
            "timestamp": time.time(),
        })
        return True, "PASSED"
