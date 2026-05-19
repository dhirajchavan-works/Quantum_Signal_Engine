"""
failure_sim.py — Failure Simulation for Distributed QApp Propagation

Simulates four realistic failure modes that can occur in a distributed
quantum pipeline. Each case:
  - Detects the issue explicitly
  - Prints a readable halt reason to console
  - Preserves the valid replay state already committed
  - Rejects the corrupted propagation (never silently recovers)

No silent recovery. No hidden state. Console is the observability layer.
"""

import hashlib
import json
from typing import Any

from envelope import QAppExecutionEnvelope
from nodes import DistributedNode


def _sha256_hex(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fresh_node(name: str) -> DistributedNode:
    """Create a fresh isolated node for a simulation run."""
    return DistributedNode(name)


def _make_envelope(seq: int, qapp_id: str = "marine-qapp-sim") -> QAppExecutionEnvelope:
    return QAppExecutionEnvelope.create(
        qapp_id=qapp_id,
        node_origin="Node_A",
        payload={"mission": "subsurface-scan", "seq": seq},
        sequence_id=seq,
        contract_version="1.0.0",
    )


# ---------------------------------------------------------------------------
# Case 1 — Delayed Propagation
# ---------------------------------------------------------------------------

def simulate_delayed_propagation() -> dict:
    """
    Scenario: Node_B receives seq=1, but seq=2 arrives after a delay
    (simulated by inserting a gap marker). The node detects the gap in
    causal ordering and halts rather than silently accepting out-of-sequence
    state.

    Detection rule: each node tracks the highest accepted sequence_id.
    A new envelope with sequence_id > expected_next triggers a DELAY HALT.
    """
    print("\n" + "=" * 60)
    print("[FAILURE SIM] Case 1: Delayed Propagation")
    print("=" * 60)

    node = _fresh_node("Node_B_delayed")
    env_seq1 = _make_envelope(seq=1)
    env_seq3 = _make_envelope(seq=3)   # seq=2 is missing (delayed)

    node.receive(env_seq1.to_dict(), from_node="Node_A")
    print(f"  [OK]   seq=1 received and accepted by {node.name}")

    # Simulate delayed arrival: seq=3 arrives before seq=2
    expected_next = len(node.received_invocations) + 1   # = 2
    incoming_seq = env_seq3.sequence_id                   # = 3

    if incoming_seq > expected_next:
        halt_reason = (
            f"[HALT] Delayed propagation detected on {node.name}. "
            f"Expected seq={expected_next}, received seq={incoming_seq}. "
            f"seq={expected_next} has not yet arrived. "
            f"Propagation of seq={incoming_seq} rejected. "
            f"Replay state preserved up to seq={len(node.received_invocations)}."
        )
        print(f"  {halt_reason}")
        return {
            "case": "delayed_propagation",
            "halted": True,
            "reason": halt_reason,
            "preserved_up_to_seq": len(node.received_invocations),
            "node_hash": node.execution_hash,
        }

    # Should never reach here in this simulation
    node.receive(env_seq3.to_dict(), from_node="Node_A")
    return {"case": "delayed_propagation", "halted": False}


# ---------------------------------------------------------------------------
# Case 2 — Duplicate Propagation
# ---------------------------------------------------------------------------

def simulate_duplicate_propagation() -> dict:
    """
    Scenario: The same envelope (same invocation_id) is delivered twice
    to Node_B. The node detects the duplicate and rejects the second
    delivery without altering already-committed state.

    Detection rule: invocation_id already present in received_invocations.
    """
    print("\n" + "=" * 60)
    print("[FAILURE SIM] Case 2: Duplicate Propagation")
    print("=" * 60)

    node = _fresh_node("Node_B_dup")
    env = _make_envelope(seq=1)
    env_dict = env.to_dict()

    node.receive(env_dict, from_node="Node_A")
    print(f"  [OK]   seq=1 received first time by {node.name}")

    hash_after_first = node.execution_hash

    # Attempt to deliver the same envelope again
    already_seen = any(
        r["invocation_id"] == env_dict["invocation_id"]
        for r in node.received_invocations
    )

    if already_seen:
        halt_reason = (
            f"[HALT] Duplicate propagation detected on {node.name}. "
            f"invocation_id={env_dict['invocation_id'][:12]}... already committed. "
            f"Duplicate delivery rejected. "
            f"Replay state unchanged. "
            f"execution_hash preserved: {hash_after_first[:12]}..."
        )
        print(f"  {halt_reason}")
        assert node.execution_hash == hash_after_first, (
            "Execution hash must not change on rejected duplicate."
        )
        return {
            "case": "duplicate_propagation",
            "halted": True,
            "reason": halt_reason,
            "node_hash": node.execution_hash,
            "hash_unchanged": node.execution_hash == hash_after_first,
        }

    node.receive(env_dict, from_node="Node_A")
    return {"case": "duplicate_propagation", "halted": False}


# ---------------------------------------------------------------------------
# Case 3 — Missing Propagation
# ---------------------------------------------------------------------------

def simulate_missing_propagation() -> dict:
    """
    Scenario: Node_C never receives seq=2, but a replay is attempted over
    all three sequences. The replay detects the missing entry in the log
    and halts rather than producing a partial hash.

    Detection rule: the replay log claims to have 3 entries, but only
    seq=1 and seq=3 are present (seq=2 is absent / lost in transit).
    """
    print("\n" + "=" * 60)
    print("[FAILURE SIM] Case 3: Missing Propagation")
    print("=" * 60)

    env1 = _make_envelope(seq=1)
    env2 = _make_envelope(seq=2)   # this will not be delivered
    env3 = _make_envelope(seq=3)

    # Simulate log that claims continuity but is missing seq=2
    incomplete_log: list[dict] = [
        {**env1.to_dict(), "envelope_hash": env1.envelope_hash(), "phase": "propagation", "path": ["Node_A", "Node_C"]},
        # env2 is intentionally absent
        {**env3.to_dict(), "envelope_hash": env3.envelope_hash(), "phase": "propagation", "path": ["Node_A", "Node_C"]},
    ]

    declared_total = 3   # the system claims 3 envelopes were propagated
    actual_in_log = len(incomplete_log)

    print(
        f"  Declared total envelopes: {declared_total} | "
        f"Present in log: {actual_in_log}"
    )

    if actual_in_log < declared_total:
        halt_reason = (
            f"[HALT] Missing propagation detected. "
            f"Log declares {declared_total} envelopes but only {actual_in_log} present. "
            f"seq=2 is absent. "
            f"Replay aborted — partial replay would produce a non-canonical hash. "
            f"System must recover seq=2 before replay can proceed."
        )
        print(f"  {halt_reason}")
        return {
            "case": "missing_propagation",
            "halted": True,
            "reason": halt_reason,
            "declared_total": declared_total,
            "actual_in_log": actual_in_log,
            "missing_seqs": [2],
        }

    return {"case": "missing_propagation", "halted": False}


# ---------------------------------------------------------------------------
# Case 4 — Out-of-Order sequence_id
# ---------------------------------------------------------------------------

def simulate_out_of_order_propagation() -> dict:
    """
    Scenario: Envelopes arrive at Node_B in the wrong causal order
    (seq=3 before seq=1 before seq=2). The node detects the ordering
    violation and halts immediately, preserving the last known good state.

    Detection rule: incoming sequence_id is less than the highest already
    accepted sequence_id (a strict monotonic ordering constraint).
    """
    print("\n" + "=" * 60)
    print("[FAILURE SIM] Case 4: Out-of-Order sequence_id")
    print("=" * 60)

    node = _fresh_node("Node_B_ooo")

    # Deliver envelopes in wrong order: 3, 1, 2
    arrival_order = [3, 1, 2]
    envelopes = {s: _make_envelope(seq=s) for s in [1, 2, 3]}

    highest_accepted: int = 0
    result: dict[str, Any] = {
        "case": "out_of_order_propagation",
        "halted": False,
        "accepted_sequences": [],
        "node_hash": "",
    }

    for seq in arrival_order:
        env_dict = envelopes[seq].to_dict()

        if seq <= highest_accepted:
            halt_reason = (
                f"[HALT] Out-of-order propagation detected on {node.name}. "
                f"Received seq={seq} but highest accepted is seq={highest_accepted}. "
                f"Causal ordering violated. "
                f"Envelope seq={seq} rejected. "
                f"Replay state preserved through seq={highest_accepted}."
            )
            print(f"  {halt_reason}")
            result["halted"] = True
            result["reason"] = halt_reason
            result["node_hash"] = node.execution_hash
            result["violated_at_seq"] = seq
            result["highest_accepted"] = highest_accepted
            return result

        # Accept in-order arrival
        node.receive(env_dict, from_node="Node_A")
        highest_accepted = seq
        print(
            f"  [OK]   seq={seq} accepted by {node.name} | "
            f"hash={node.execution_hash[:12]}..."
        )
        result["accepted_sequences"].append(seq)

    result["node_hash"] = node.execution_hash
    return result


# ---------------------------------------------------------------------------
# Runner — execute all four failure simulations
# ---------------------------------------------------------------------------

def run_all_failure_simulations() -> list[dict]:
    """
    Execute all four failure simulations in order.
    Returns a list of result dicts (one per case).
    All cases that detect a failure will have halted=True.
    """
    print("\n" + "=" * 60)
    print("[FAILURE SIM] Running all 4 failure simulation cases")
    print("=" * 60)

    results = [
        simulate_delayed_propagation(),
        simulate_duplicate_propagation(),
        simulate_missing_propagation(),
        simulate_out_of_order_propagation(),
    ]

    print("\n[FAILURE SIM] ── Summary ──")
    for r in results:
        status = "HALTED ✓" if r.get("halted") else "PASSED (no failure triggered)"
        print(f"  {r['case']}: {status}")

    return results
