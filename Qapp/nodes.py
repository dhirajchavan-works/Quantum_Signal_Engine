"""
nodes.py — Distributed Node Objects

Three node participants in the Marine Intelligence quantum propagation
network. Each node tracks its own received invocations, replay log,
execution hash, and propagated events using plain Python dicts/lists.
No databases, no external state, no hidden mutation.
"""

import hashlib
import json
from typing import Any


def _sha256_hex(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DistributedNode:
    """
    A single participant node in the QApp propagation network.

    State is intentionally simple and fully inspectable:
      received_invocations — every envelope dict this node accepted
      replay_log           — append-only ordered record of events
      execution_hash       — rolling SHA-256 over accepted invocations
      propagated_events    — events this node forwarded to peers
    """

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.received_invocations: list[dict] = []
        self.replay_log: list[dict] = []
        self.execution_hash: str = _sha256_hex(f"init:{name}")
        self.propagated_events: list[dict] = []

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def receive(self, envelope_dict: dict, from_node: str = "external") -> None:
        """
        Accept an envelope from another node or external caller.
        Updates the rolling execution_hash deterministically.
        Appends to received_invocations and replay_log (append-only).
        """
        self.received_invocations.append(envelope_dict)

        log_entry: dict[str, Any] = {
            "event": "received",
            "node": self.name,
            "from": from_node,
            "invocation_id": envelope_dict["invocation_id"],
            "sequence_id": envelope_dict["sequence_id"],
            "timestamp": envelope_dict["timestamp"],
        }
        self.replay_log.append(log_entry)

        self.execution_hash = _sha256_hex(
            self.execution_hash,
            json.dumps(envelope_dict, sort_keys=True),
        )

    def record_propagation(self, envelope_dict: dict, to_nodes: list[str]) -> None:
        """
        Record an outbound propagation event (called by Node_A only).
        Does NOT re-hash — propagation is a side-effect, not state.
        """
        event: dict[str, Any] = {
            "event": "propagated",
            "from": self.name,
            "to": to_nodes,
            "invocation_id": envelope_dict["invocation_id"],
            "sequence_id": envelope_dict["sequence_id"],
            "timestamp": envelope_dict["timestamp"],
        }
        self.propagated_events.append(event)
        self.replay_log.append(event)

    def snapshot(self) -> dict:
        """Return a full, inspectable snapshot of this node's state."""
        return {
            "node": self.name,
            "execution_hash": self.execution_hash,
            "received_count": len(self.received_invocations),
            "propagated_count": len(self.propagated_events),
            "replay_log_length": len(self.replay_log),
            "received_invocations": self.received_invocations,
            "replay_log": self.replay_log,
            "propagated_events": self.propagated_events,
        }

    def reset(self) -> None:
        """
        Hard-reset all node state. Used before determinism replay tests
        to ensure a clean slate.
        """
        self.received_invocations = []
        self.replay_log = []
        self.execution_hash = _sha256_hex(f"init:{self.name}")
        self.propagated_events = []

    def __repr__(self) -> str:
        return (
            f"DistributedNode(name={self.name!r}, "
            f"received={len(self.received_invocations)}, "
            f"hash={self.execution_hash[:12]}...)"
        )


# ---------------------------------------------------------------------------
# The three canonical nodes in the Marine Intelligence propagation network
# ---------------------------------------------------------------------------

Node_A = DistributedNode("Node_A")   # Originator / propagator
Node_B = DistributedNode("Node_B")   # Downstream receiver
Node_C = DistributedNode("Node_C")   # Downstream receiver
