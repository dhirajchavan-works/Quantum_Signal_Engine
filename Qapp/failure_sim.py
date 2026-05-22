# failure_sim.py
# Failure simulation for the distributed QApp propagation layer.
#
# 4 cases:
#   1. Delayed propagation       — causal gap exceeds threshold; accepted with flag
#   2. Duplicate propagation     — same invocation_id seen twice; rejected hard
#   3. Missing propagation       — node never received the envelope; consensus fails
#   4. Out-of-order sequence_id  — non-monotonic sequence; halts until reordered
#
# Rules:
#   Every failure prints a readable halt reason before raising or returning.
#   Valid replay state is always preserved — corrupted state is always rejected.
#   No silent recovery.  No swallowed exceptions.  No automatic retry.
#
# This module has NO imports from other local files — fully standalone.

import hashlib
import json


# ── Utilities ──────────────────────────────────────────────────────────────────

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ── Exception ─────────────────────────────────────────────────────────────────

class PropagationFailure(Exception):
    """
    Raised when a propagation failure cannot be automatically resolved.

    Callers MUST catch this.  It is never raised silently — the reason is
    always printed to console before the exception is raised.
    """
    pass


# ── Console formatting ─────────────────────────────────────────────────────────

def _header(case_num: int, name: str) -> None:
    print(f"\n  ┌─ Failure Case {case_num}: {name}")


def _halt(reason: str) -> None:
    """Print a structured halt notice.  Caller raises PropagationFailure next."""
    print(f"  │  ❌ HALT  : {reason}")
    print(f"  │  Action  : Propagation REJECTED. Replay state preserved.")
    print(f"  └──────────────────────────────────────────────────────────")


def _accept_flagged(msg: str) -> None:
    """Print an accept-with-flag notice.  No exception raised."""
    print(f"  │  ⚠️  FLAG  : {msg}")
    print(f"  │  Action  : Accepted with causal delay flag. Logged for audit.")
    print(f"  └──────────────────────────────────────────────────────────")


def _ok(msg: str) -> None:
    """Print a clean-pass notice (used in non-failing legs of each case)."""
    print(f"  │  ✅ OK    : {msg}")
    print(f"  └──────────────────────────────────────────────────────────")


# ══════════════════════════════════════════════════════════════════════════════
# Case 1 — Delayed Propagation
# ══════════════════════════════════════════════════════════════════════════════

DELAY_THRESHOLD = 3   # max tolerable gap in sequence_ids before flagging


def simulate_delayed_propagation(
    envelope_dict: dict,
    last_acknowledged_seq: int,
) -> dict:
    """
    Detect when an envelope arrives with a large sequence_id gap relative
    to the last acknowledged envelope on this node.

    Policy:
        gap <= DELAY_THRESHOLD  → accepted normally (no flag)
        gap >  DELAY_THRESHOLD  → accepted with CAUSAL_DELAY flag
        (delayed-but-valid data should be logged, not silently dropped)

    The flag is embedded in the return dict so callers can log it to the
    replay audit trail.  No exception is raised.

    Args:
        envelope_dict:          Envelope being evaluated.
        last_acknowledged_seq:  Last sequence_id this node confirmed receipt of.

    Returns:
        dict with status, invocation_id, sequence_id, gap, [flag], accepted.
    """
    _header(1, "Delayed Propagation")

    current_seq = envelope_dict["sequence_id"]
    # gap = number of sequence steps skipped (0 = consecutive, fine)
    gap = current_seq - last_acknowledged_seq - 1

    if gap > DELAY_THRESHOLD:
        _accept_flagged(
            f"seq={current_seq} arrived after seq={last_acknowledged_seq}. "
            f"Gap={gap} steps (threshold={DELAY_THRESHOLD}). "
            f"Invocation {envelope_dict['invocation_id'][:16]}... "
            f"accepted with flag=CAUSAL_DELAY."
        )
        return {
            "status":        "DELAYED",
            "invocation_id": envelope_dict["invocation_id"],
            "sequence_id":   current_seq,
            "gap":           gap,
            "flag":          "CAUSAL_DELAY",
            "accepted":      True,
        }

    # Normal arrival — no issue.
    _ok(
        f"seq={current_seq}, gap={gap} within threshold={DELAY_THRESHOLD}. "
        f"No delay detected."
    )
    return {
        "status":        "OK",
        "invocation_id": envelope_dict["invocation_id"],
        "sequence_id":   current_seq,
        "gap":           gap,
        "accepted":      True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Case 2 — Duplicate Propagation
# ══════════════════════════════════════════════════════════════════════════════

def simulate_duplicate_propagation(
    envelope_dict: dict,
    seen_invocations: set,
) -> dict:
    """
    Detect and hard-reject duplicate invocation_ids.

    An invocation_id is the SHA-256 of (trace_id, payload_hash, sequence_id).
    If the same ID appears twice, this is either:
        - A network re-delivery (must be idempotent-rejected, not re-applied)
        - A replay attack
        - A bug in the origin node

    In all cases: REJECT.  Replay log is NOT modified.
    The seen_invocations set is NOT modified either (already has the ID).

    Args:
        envelope_dict:      Envelope being evaluated.
        seen_invocations:   Mutable set maintained by the caller.  Updated on
                            first receipt; untouched on duplicate.

    Returns:
        dict with status and invocation_id on clean pass.

    Raises:
        PropagationFailure  on duplicate.
    """
    _header(2, "Duplicate Propagation")

    inv_id = envelope_dict["invocation_id"]

    if inv_id in seen_invocations:
        reason = (
            f"invocation_id={inv_id[:24]}... "
            f"is already present in the propagation log. "
            f"Idempotency violation detected. "
            f"Replay log UNCHANGED. Duplicate discarded."
        )
        _halt(reason)
        raise PropagationFailure(f"Duplicate invocation: {inv_id[:24]}...")

    seen_invocations.add(inv_id)
    _ok(f"invocation_id={inv_id[:24]}... is new. Added to seen set. Accepted.")
    return {"status": "OK", "invocation_id": inv_id}


# ══════════════════════════════════════════════════════════════════════════════
# Case 3 — Missing Propagation
# ══════════════════════════════════════════════════════════════════════════════

def simulate_missing_propagation(
    expected_nodes: list,
    received_by_nodes: list,
    envelope_dict: dict,
) -> dict:
    """
    Detect when one or more expected downstream nodes never received an envelope.

    Consensus in this 3-node system requires all nodes to hold the same
    invocations.  If any node is missing a delivery, the consensus hash will
    diverge — and no autonomous action can be taken.

    Policy:
        All expected nodes received it  → OK
        One or more missing             → HALT.  PropagationFailure raised.

    The valid partial state (nodes that DID receive it) is preserved.
    The missing nodes' states are left unchanged and flagged.

    Args:
        expected_nodes:     All nodes that should have received the envelope.
        received_by_nodes:  Nodes confirmed to have received it.
        envelope_dict:      The envelope in question.

    Returns:
        dict with status on clean pass.

    Raises:
        PropagationFailure  if any expected node is missing.
    """
    _header(3, "Missing Propagation")

    missing = sorted(set(expected_nodes) - set(received_by_nodes))

    if missing:
        reason = (
            f"invocation_id={envelope_dict['invocation_id'][:24]}... "
            f"was NOT delivered to: {missing}. "
            f"Full consensus requires all nodes to receive every envelope. "
            f"Nodes that received it: {sorted(received_by_nodes)}. "
            f"Their replay states are preserved and valid. "
            f"Consensus CANNOT be reached until gap is resolved."
        )
        _halt(reason)
        raise PropagationFailure(
            f"Missing propagation to {missing} for "
            f"invocation {envelope_dict['invocation_id'][:24]}..."
        )

    _ok(
        f"All expected nodes received invocation "
        f"{envelope_dict['invocation_id'][:24]}...: {expected_nodes}"
    )
    return {"status": "OK", "received_by": received_by_nodes}


# ══════════════════════════════════════════════════════════════════════════════
# Case 4 — Out-of-Order Sequence ID
# ══════════════════════════════════════════════════════════════════════════════

def simulate_out_of_order(envelopes: list) -> dict:
    """
    Detect non-monotonic sequence_ids in a batch of envelopes.

    Sequence IDs must be strictly increasing.  A lower-or-equal ID arriving
    after a higher one signals a causal ordering violation — the dependent
    computation cannot be applied before its dependencies.

    Processing halts at the first violation.  The caller must reorder the
    batch and re-submit before any envelope in the batch can be applied.

    Note:
        replay_qapp_log() automatically sorts by sequence_id before replaying,
        so a shuffled LOG is safe to replay.  This case covers the scenario
        where an upstream router delivers envelopes in wrong order and the
        receiving node must detect the problem before applying them.

    Args:
        envelopes:  List of envelope dicts to validate.

    Returns:
        dict with status and order on clean pass.

    Raises:
        PropagationFailure  at the first out-of-order entry.
    """
    _header(4, "Out-of-Order Sequence ID")

    ids = [e["sequence_id"] for e in envelopes]

    for i in range(1, len(ids)):
        if ids[i] <= ids[i - 1]:
            reason = (
                f"sequence_id={ids[i]} at position {i} is not greater than "
                f"previous sequence_id={ids[i - 1]} at position {i - 1}. "
                f"Causal ordering VIOLATED. "
                f"Downstream computation depends on earlier sequences being applied first. "
                f"Batch processing HALTED at position {i}. "
                f"Reorder and re-submit before any entry in this batch can proceed."
            )
            _halt(reason)
            raise PropagationFailure(
                f"Out-of-order at index {i}: "
                f"seq={ids[i]} arrived after seq={ids[i - 1]}"
            )

    _ok(f"All {len(ids)} sequence_ids are strictly monotonic: {ids}")
    return {"status": "OK", "order": ids}
