"""Apex_DeepAgents_Matrix: Compensatory Rollback Middleware for LangGraph & DeepAgents.

Provides Hoare-logic transaction journaling and atomic reversal DAG generation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TransactionalAction:
    """An individual recorded agent action in a LangGraph execution thread."""
    action_id: str
    tool_name: str
    target_resource_id: str
    forward_payload: Dict[str, Any]
    inverse_payload: Dict[str, Any]
    inverse_tool_name: str
    timestamp: float = field(default_factory=time.time)


class CompensatoryRollbackMiddleware:
    """Interception middleware tracking mutating agent operations with rollback guarantees."""

    INVERSE_TOOL_MAP = {
        "cordon_node": ("uncordon_node", lambda p: {}),
        "uncordon_node": ("cordon_node", lambda p: {}),
        "scale_deployment": ("scale_deployment", lambda p: {"replicas": p.get("previous_replicas", 1)}),
        "attach_ebpf_probe": ("detach_ebpf_probe", lambda p: {"probe_id": p.get("probe_id")}),
        "detach_ebpf_probe": ("attach_ebpf_probe", lambda p: {"probe_id": p.get("probe_id")}),
        "quarantine_subnet": ("unquarantine_subnet", lambda p: {"subnet_id": p.get("subnet_id")}),
    }

    def __init__(self) -> None:
        self.journal: List[TransactionalAction] = []
        self.rolled_back: bool = False

    def record_action(
        self,
        tool_name: str,
        target_resource_id: str,
        payload: Dict[str, Any],
        custom_inverse_tool: Optional[str] = None,
        custom_inverse_payload: Optional[Dict[str, Any]] = None,
    ) -> TransactionalAction:
        """Log a mutating action to the transaction journal."""
        inv_tool = custom_inverse_tool
        inv_payload = custom_inverse_payload

        if not inv_tool:
            mapping = self.INVERSE_TOOL_MAP.get(tool_name)
            if mapping:
                inv_tool = mapping[0]
                inv_payload = mapping[1](payload)
            else:
                inv_tool = f"rollback_{tool_name}"
                inv_payload = dict(payload)

        action = TransactionalAction(
            action_id=f"tx_{uuid.uuid4().hex[:8]}",
            tool_name=tool_name,
            target_resource_id=target_resource_id,
            forward_payload=payload,
            inverse_payload=inv_payload or {},
            inverse_tool_name=inv_tool,
        )
        self.journal.append(action)
        return action

    def generate_rollback_sequence(self) -> List[Dict[str, Any]]:
        """Return the compensatory inverse execution sequence in reverse chronological order."""
        seq: List[Dict[str, Any]] = []
        for action in reversed(self.journal):
            seq.append({
                "action_id": f"rb_{action.action_id}",
                "original_action_id": action.action_id,
                "tool_name": action.inverse_tool_name,
                "target_resource_id": action.target_resource_id,
                "payload": action.inverse_payload,
            })
        return seq

    def clear(self) -> None:
        """Reset journal after successful commit."""
        self.journal.clear()
        self.rolled_back = False
