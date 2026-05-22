# nodes.py
# Distributed node objects for QApp propagation.
#
# Three nodes: Node_A (origin), Node_B, Node_C (downstream receivers).
# Each tracks:
#   received_invocations  — every envelope dict received, in order
#   replay_log            — append-only audit trail of all events
#   execution_hash        — rolling SHA-256 chain over received invocation_ids
#   propagated_events     — outbound propagation records (Node_A only in practice)
#
# No databases. No I/O. No hidden state.
# Everything is a plain Python list or dict — fully inspectable at any time.

import hashlib


# ── Hash helpers ───────────────────────────────────────────────────────────────

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def init_node_hash(node_id: str) -> str:
    """Deterministic genesis hash for a node.  Used by nodes and replay alike."""
    return _sha256(f"INIT:{node_id}")


# ── Node class ─────────────────────────────────────────────────────────────────

class DistributedNode:
    """
    A single participant in the QApp propagation graph.

    State model
    -----------
    execution_hash
        Starts at init_node_hash(node_id).
        Updated on every call to receive():
            new_hash = SHA-256( f"{current_hash}:{invocation_id}" )
        This creates a tamper-evident chain: any insertion, deletion, or
        reordering of received events produces a different final hash.

    received_invocations
        List of raw envelope dicts — one entry per receive().
        Append-only.  Never mutated after append.

    replay_log
        List of structured log entries covering both RECEIVED and PROPAGATED
        events.  The authoritative audit trail for this node.
        Append-only.

    propagated_events
        Lightweight records of what this node forwarded, and to whom.
        Populated by record_propagation() — called by the origin node only.
    """

    def __init__(self, node_id: str) -> None:
        self.node_id: str = node_id
        self.received_invocations: list = []
        self.replay_log: list = []
        self.execution_hash: str = init_node_hash(node_id)
        self.propagated_events: list = []

    # ── Inbound ───────────────────────────────────────────────────────────

    def receive(self, envelope_dict: dict) -> None:
        """
        Record receipt of a propagated envelope.
        Appends to received_invocations and replay_log.
        Updates execution_hash — call order matters.
        """
        self.received_invocations.append(dict(envelope_dict))
        self.replay_log.append({
            "event":         "RECEIVED",
            "node":          self.node_id,
            "invocation_id": envelope_dict["invocation_id"],
            "sequence_id":   envelope_dict["sequence_id"],
            "trace_id":      envelope_dict["trace_id"],
            "from_node":     envelope_dict["node_origin"],
            "timestamp":     envelope_dict["timestamp"],
        })
        self._update_hash(envelope_dict["invocation_id"])

    # ── Outbound ──────────────────────────────────────────────────────────

    def record_propagation(self, envelope_dict: dict, to_node: str) -> None:
        """
        Record that this node forwarded an event to another node.
        Does NOT update execution_hash — propagation is structural, not receipt.
        """
        self.propagated_events.append({
            "to_node":       to_node,
            "invocation_id": envelope_dict["invocation_id"],
            "sequence_id":   envelope_dict["sequence_id"],
            "trace_id":      envelope_dict["trace_id"],
        })
        self.replay_log.append({
            "event":         "PROPAGATED",
            "node":          self.node_id,
            "invocation_id": envelope_dict["invocation_id"],
            "sequence_id":   envelope_dict["sequence_id"],
            "to_node":       to_node,
        })

    # ── Internal ──────────────────────────────────────────────────────────

    def _update_hash(self, invocation_id: str) -> None:
        self.execution_hash = _sha256(f"{self.execution_hash}:{invocation_id}")

    # ── Reset ─────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """
        Return node to initial state.
        Called between test phases to ensure clean isolation.
        """
        self.received_invocations = []
        self.replay_log = []
        self.execution_hash = init_node_hash(self.node_id)
        self.propagated_events = []

    # ── Inspection ────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Full observable status — no hidden fields."""
        return {
            "node_id":          self.node_id,
            "received_count":   len(self.received_invocations),
            "propagated_count": len(self.propagated_events),
            "execution_hash":   self.execution_hash,
            "replay_log_count": len(self.replay_log),
        }

    def received_invocation_ids(self) -> list:
        """Ordered list of invocation_ids this node received."""
        return [e["invocation_id"] for e in self.received_invocations]

    def __repr__(self) -> str:
        return (
            f"DistributedNode({self.node_id!r}, "
            f"recv={len(self.received_invocations)}, "
            f"hash={self.execution_hash[:12]}...)"
        )


# ── Singletons ─────────────────────────────────────────────────────────────────

Node_A = DistributedNode("Node_A")
Node_B = DistributedNode("Node_B")
Node_C = DistributedNode("Node_C")

ALL_NODES: dict = {
    "Node_A": Node_A,
    "Node_B": Node_B,
    "Node_C": Node_C,
}


def reset_all_nodes() -> None:
    """Reset all three nodes to genesis state.  Used between test phases."""
    for node in ALL_NODES.values():
        node.reset()
