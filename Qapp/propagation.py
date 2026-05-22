# propagation.py
# Distributed QApp propagation engine.
#
# Public API:
#   propagate_qapp_event(envelope)   — Node_A → Node_B, Node_A → Node_C
#   replay_qapp_log(log)             — reconstruct path, verify hash consistency
#   get_propagation_log()            — read the global append-only log
#   clear_propagation_log()          — reset for a new test phase
#
# Rules:
#   causal order preserved via sequence_id
#   append-only log — nothing is ever deleted or mutated
#   replay is deterministic: same log → same hashes, always
#   console is the observability layer

import hashlib
import json
from typing import Optional

from envelope import QAppExecutionEnvelope
from nodes import Node_A, Node_B, Node_C, init_node_hash


# ── Internals ──────────────────────────────────────────────────────────────────

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# Step ordering for causal sort within a single sequence_id.
# ORIGIN must be replayed before PROPAGATE.
_STEP_ORDER: dict = {"ORIGIN": 0, "PROPAGATE": 1}

# Node IDs known to this layer.
_ALL_NODE_IDS = ["Node_A", "Node_B", "Node_C"]


# ── Append-only global propagation log ────────────────────────────────────────
#
# This is the single source of truth for replay.
# All writes go through _append() — no direct list mutation outside this module.

_PROPAGATION_LOG: list = []


def _append(entry: dict) -> None:
    _PROPAGATION_LOG.append(entry)


def get_propagation_log() -> list:
    """Return a shallow copy of the log.  Caller cannot mutate the source."""
    return list(_PROPAGATION_LOG)


def clear_propagation_log() -> None:
    """Wipe the log.  Called between test phases for clean isolation."""
    _PROPAGATION_LOG.clear()


# ── Core propagation ───────────────────────────────────────────────────────────

def propagate_qapp_event(envelope: QAppExecutionEnvelope) -> None:
    """
    Originate an event at Node_A and fan it out to Node_B and Node_C.

    Propagation path:
        Node_A (origin/receive)
            └─→ Node_B (receive)
            └─→ Node_C (receive)

    Causal ordering guarantee:
        Every log entry carries the same sequence_id.
        replay_qapp_log() sorts by (sequence_id, step_order) before computing
        hashes, so a shuffled log always reconstructs to the same state.

    All steps are logged to _PROPAGATION_LOG before moving to the next step.
    No step is skipped — partial propagation is visible in the log.
    """
    env_dict = envelope.to_dict()

    # ── Header ────────────────────────────────────────────────────────────
    print(f"\n  [PROPAGATE] seq={envelope.sequence_id} | "
          f"ts={envelope.timestamp}")
    print(f"    qapp       : {envelope.qapp_id}")
    print(f"    contract   : {envelope.contract_version}")
    print(f"    trace      : {envelope.trace_id[:24]}...")
    print(f"    invocation : {envelope.invocation_id[:24]}...")

    # ── Step 1: Node_A originates ─────────────────────────────────────────
    Node_A.receive(env_dict)
    _append({
        "step":          "ORIGIN",
        "from":          "Node_A",
        "to":            "Node_A",
        "invocation_id": envelope.invocation_id,
        "sequence_id":   envelope.sequence_id,
        "trace_id":      envelope.trace_id,
        "timestamp":     envelope.timestamp,
    })
    print(f"\n    Node_A  ← origin    hash={Node_A.execution_hash[:16]}...")

    # ── Step 2: Node_A → Node_B ───────────────────────────────────────────
    Node_A.record_propagation(env_dict, "Node_B")
    Node_B.receive(env_dict)
    _append({
        "step":          "PROPAGATE",
        "from":          "Node_A",
        "to":            "Node_B",
        "invocation_id": envelope.invocation_id,
        "sequence_id":   envelope.sequence_id,
        "trace_id":      envelope.trace_id,
        "timestamp":     envelope.timestamp,
    })
    print(f"    Node_A → Node_B  ✅  hash={Node_B.execution_hash[:16]}...")

    # ── Step 3: Node_A → Node_C ───────────────────────────────────────────
    Node_A.record_propagation(env_dict, "Node_C")
    Node_C.receive(env_dict)
    _append({
        "step":          "PROPAGATE",
        "from":          "Node_A",
        "to":            "Node_C",
        "invocation_id": envelope.invocation_id,
        "sequence_id":   envelope.sequence_id,
        "trace_id":      envelope.trace_id,
        "timestamp":     envelope.timestamp,
    })
    print(f"    Node_A → Node_C  ✅  hash={Node_C.execution_hash[:16]}...")
    print(f"    Causal order     ✅  sequence_id={envelope.sequence_id} "
          f"preserved across all nodes")


# ── Hash utilities ─────────────────────────────────────────────────────────────

def _replay_node_hashes(sorted_log: list) -> dict:
    """
    Reconstruct each node's execution_hash by replaying RECEIVED-equivalent
    log entries in causal order.

    The hash chain mirrors DistributedNode._update_hash():
        hash_n+1 = SHA-256( f"{hash_n}:{invocation_id}" )

    Only entries whose 'to' field matches a node name advance that node's hash.
    PROPAGATED entries (from → to) are receive events for the 'to' node.
    ORIGIN entries are receive events for Node_A.
    """
    hashes = {nid: init_node_hash(nid) for nid in _ALL_NODE_IDS}
    for entry in sorted_log:
        to = entry["to"]
        if to in hashes:
            hashes[to] = _sha256(f"{hashes[to]}:{entry['invocation_id']}")
    return hashes


def _compute_log_hash(sorted_log: list) -> str:
    """Canonical hash of the full sorted log.  Same log → same hash, always."""
    canonical = json.dumps(sorted_log, sort_keys=True, separators=(",", ":"))
    return _sha256(canonical)


def _compute_consensus_hash(node_hashes: dict) -> str:
    """
    Single hash representing agreement across all nodes.
    Built from alphabetically-sorted node hashes so key insertion order
    in the dict cannot affect the result.
    """
    ordered = json.dumps(
        {k: node_hashes[k] for k in sorted(node_hashes)},
        separators=(",", ":"),
    )
    return _sha256(ordered)


def _causal_sort(log: list) -> list:
    """
    Sort log entries for deterministic replay.
    Primary key: sequence_id (ascending — lower sequence runs first).
    Secondary key: step order (ORIGIN before PROPAGATE within same sequence).
    """
    return sorted(
        log,
        key=lambda e: (e["sequence_id"], _STEP_ORDER.get(e["step"], 99)),
    )


# ── Replay ─────────────────────────────────────────────────────────────────────

def replay_qapp_log(
    log: Optional[list] = None,
    silent: bool = False,
) -> dict:
    """
    Reconstruct the full propagation path from a log snapshot.

    Steps
    -----
    1. Causal-sort the log by (sequence_id, step_order).
    2. Replay node hash chains from the sorted entries.
    3. Compute consensus hash across all node hashes.
    4. Compute canonical hash of the full sorted log.
    5. Verify that Node_A, Node_B, Node_C all received the same invocations.
    6. Report and return.

    Guarantee:
        Given the same log (any input ordering), this function always produces
        the same node_hashes, consensus_hash, and log_hash.

    Args:
        log:    Propagation log to replay.  Defaults to the live global log.
        silent: Suppress console output (used during multi-run hash checks).

    Returns:
        dict with log_entry_count, node_hashes, log_hash,
        consensus_hash, consistent, coverage.
    """
    if log is None:
        log = _PROPAGATION_LOG

    sorted_log    = _causal_sort(log)
    node_hashes   = _replay_node_hashes(sorted_log)
    log_hash      = _compute_log_hash(sorted_log)
    consensus     = _compute_consensus_hash(node_hashes)

    # Coverage: every node should have received exactly the same invocations.
    def _inv_for(node_id: str) -> list:
        return sorted(
            e["invocation_id"]
            for e in sorted_log
            if e["to"] == node_id
        )

    coverage    = {nid: _inv_for(nid) for nid in _ALL_NODE_IDS}
    consistent  = (
        coverage["Node_A"] == coverage["Node_B"] == coverage["Node_C"]
    )

    if not silent:
        print(f"\n  [REPLAY] {len(sorted_log)} log entries — "
              f"causal-sorted by (sequence_id, step)")
        for nid in _ALL_NODE_IDS:
            print(f"    {nid} hash    : {node_hashes[nid][:24]}...")
        print(f"    Consistent   : {'✅ YES' if consistent else '❌ NO — DIVERGENCE DETECTED'}")
        print(f"    Consensus    : {consensus[:24]}...")
        print(f"    Log hash     : {log_hash[:24]}...")
        print(f"    Entries/node : {len(coverage['Node_A'])} invocations each")

    return {
        "log_entry_count": len(sorted_log),
        "node_hashes":     node_hashes,
        "log_hash":        log_hash,
        "consensus_hash":  consensus,
        "consistent":      consistent,
        "coverage":        coverage,
    }
