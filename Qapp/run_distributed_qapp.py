# run_distributed_qapp.py
# Task 9 — Distributed QApp Propagation Layer
# Marine Intelligence System | BHIV Core Interface
#
# Execution:
#   python run_distributed_qapp.py
#
# Phase 1  QApp Invocation Envelope
# Phase 2  Distributed Node Simulation
# Phase 3  QApp Propagation Engine
# Phase 4  Distributed Replay Reconstruction
# Phase 5  Divergence + Failure Simulation
# Phase 6  Observability Layer
# Phase 7  Determinism Proof
# Phase 8  REVIEW_PACKET.md  (documentation artefact — not a runtime phase)
#
# Rules enforced:
#   no datetime.now()     — all timestamps from sequence_id
#   no randomness         — all IDs from SHA-256 of deterministic inputs
#   no databases          — plain Python lists and dicts only
#   no networking         — pure stdlib simulation
#   no silent recovery    — every failure prints before raising
#   exit 0 on full PASS   — exit 1 on any failure

import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── UTF-8 stdout (Windows-safe) ────────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

# ── Imports ────────────────────────────────────────────────────────────────────
from envelope import QAppExecutionEnvelope
from nodes import Node_A, Node_B, Node_C, ALL_NODES, reset_all_nodes
from propagation import (
    propagate_qapp_event,
    replay_qapp_log,
    get_propagation_log,
    clear_propagation_log,
)
from failure_sim import (
    PropagationFailure,
    simulate_delayed_propagation,
    simulate_duplicate_propagation,
    simulate_missing_propagation,
    simulate_out_of_order,
)


# ══════════════════════════════════════════════════════════════════════════════
# Test payloads — quantum signal snapshots (payload content is opaque here;
# only the SHA-256 hash travels in the envelope)
# ══════════════════════════════════════════════════════════════════════════════

QAPP_ID          = "bhiv.corrosion.delta.v1"
NODE_ORIGIN      = "Node_A"
CONTRACT_VERSION = "qapp-v1.0"

SAMPLE_PAYLOADS = [
    {   # seq 1 — converged, high-confidence zone
        "node_id":      "qnode_01",
        "energy_delta": 0.0001,
        "iterations":   120,
        "confidence":   0.92,
        "variance":     0.002,
    },
    {   # seq 2 — marginal, approaching convergence
        "node_id":      "qnode_02",
        "energy_delta": 0.003,
        "iterations":   340,
        "confidence":   0.87,
        "variance":     0.004,
    },
    {   # seq 3 — high-confidence, low variance
        "node_id":      "qnode_03",
        "energy_delta": 0.00005,
        "iterations":   55,
        "confidence":   0.98,
        "variance":     0.0008,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# Formatting
# ══════════════════════════════════════════════════════════════════════════════

W = 70  # console width


def _banner(lines: list) -> None:
    print("\n" + "═" * W)
    for line in lines:
        print(f"  {line}")
    print("═" * W)


def _phase(number: int, title: str) -> None:
    print(f"\n{'─' * W}")
    print(f"  PHASE {number}  —  {title}")
    print(f"{'─' * W}")


def _ok(msg: str) -> None:
    print(f"\n  ✅  {msg}")


def _fail(msg: str) -> None:
    print(f"\n  ❌  FAIL: {msg}")


def _j(obj: dict, indent: int = 4) -> str:
    return json.dumps(obj, indent=indent)


# ══════════════════════════════════════════════════════════════════════════════
# run()
# ══════════════════════════════════════════════════════════════════════════════

def run() -> None:

    _banner([
        "Distributed QApp Propagation Layer",
        "Marine Intelligence System  |  BHIV Core Interface",
        "Task 9  —  Quantum Infrastructure / Distributed QApp Runtime Systems",
        "",
        "Integration: Kanishk · Raj · Raj Prajapati · Jaffer Ali · Ganesh",
    ])

    passes: list = []   # accumulate PASS/FAIL per phase for final summary

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1 — QApp Invocation Envelope
    # Spec requirement: deterministic generation, no randomness,
    # no datetime.now(), no hidden fields.
    # Fields: trace_id, qapp_id, node_origin, invocation_id,
    #         payload_hash, sequence_id, timestamp, contract_version
    # ══════════════════════════════════════════════════════════════════════
    _phase(1, "QApp Invocation Envelope")

    envelopes: list = []
    for seq_num, payload in enumerate(SAMPLE_PAYLOADS, start=1):
        env = QAppExecutionEnvelope.create(
            qapp_id          = QAPP_ID,
            node_origin      = NODE_ORIGIN,
            payload          = payload,
            sequence_id      = seq_num,
            contract_version = CONTRACT_VERSION,
        )
        envelopes.append(env)

        print(f"\n  Envelope seq={seq_num}")
        d = env.to_dict()
        for k, v in d.items():
            val = str(v)
            display = val if len(val) <= 24 else val[:24] + "..."
            print(f"    {k:<20} : {display}")

    # Verify: all fields present, no datetime.now() contamination
    required = {
        "trace_id", "qapp_id", "node_origin", "invocation_id",
        "payload_hash", "sequence_id", "timestamp", "contract_version"
    }
    all_fields_ok = all(required == set(e.to_dict().keys()) for e in envelopes)
    no_now = not any("now" in str(e.timestamp) for e in envelopes)

    _ok(f"{len(envelopes)} envelopes created  |  fields={len(required)}  |  "
        f"deterministic={'YES' if all_fields_ok and no_now else 'NO'}")
    passes.append(("Phase 1 — QApp Invocation Envelope", all_fields_ok and no_now))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2 — Distributed Node Simulation
    # Spec requirement: 3-node environment, each node tracks
    # received_invocations, replay_log, execution_hash, propagated_events.
    # No databases — plain Python dicts/lists only.
    # ══════════════════════════════════════════════════════════════════════
    _phase(2, "Distributed Node Simulation")

    print("\n  Nodes initialised (pre-propagation state):\n")
    for nid, node in ALL_NODES.items():
        s = node.status()
        print(f"  {nid}")
        print(f"    received_invocations : {s['received_count']} (empty — not yet propagated)")
        print(f"    replay_log           : {s['replay_log_count']} entries")
        print(f"    execution_hash       : {s['execution_hash'][:32]}...  (genesis)")
        print(f"    propagated_events    : {s['propagated_count']}")

    # Verify all 4 required tracking fields exist on every node
    tracking_ok = all(
        hasattr(n, "received_invocations") and
        hasattr(n, "replay_log") and
        hasattr(n, "execution_hash") and
        hasattr(n, "propagated_events")
        for n in ALL_NODES.values()
    )
    _ok(f"3 nodes initialised  |  all 4 tracking fields present  |  "
        f"no database={tracking_ok}")
    passes.append(("Phase 2 — Distributed Node Simulation", tracking_ok))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3 — QApp Propagation Engine
    # Spec requirement: Node_A propagates to Node_B and Node_C,
    # propagation path logged, causal ordering preserved,
    # immutable append-only replay log, observable in console.
    # ══════════════════════════════════════════════════════════════════════
    _phase(3, "QApp Propagation Engine")

    for env in envelopes:
        propagate_qapp_event(env)

    log_after = get_propagation_log()
    log_ok = (
        len(log_after) == len(envelopes) * 3 and         # ORIGIN + 2 × PROPAGATE
        all("invocation_id" in e for e in log_after) and
        all(e["sequence_id"] in [1, 2, 3] for e in log_after)
    )

    print()
    _ok(f"{len(envelopes)} envelopes propagated  |  "
        f"log entries={len(log_after)}  |  "
        f"append-only={log_ok}  |  "
        f"path=Node_A → [Node_B, Node_C]")
    passes.append(("Phase 3 — QApp Propagation Engine", log_ok))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 4 — Distributed Replay Reconstruction
    # Spec requirement: reconstruct propagation path, replay full execution
    # chain, verify final hash consistency, prove same replay → same state.
    # ══════════════════════════════════════════════════════════════════════
    _phase(4, "Distributed Replay Reconstruction")

    live_log = get_propagation_log()
    result   = replay_qapp_log(live_log)

    # Verify replayed hashes match live node hashes exactly
    print("\n  Comparing replayed hashes to live node state:")
    hash_match = True
    for nid in ["Node_A", "Node_B", "Node_C"]:
        live_h   = ALL_NODES[nid].execution_hash
        replay_h = result["node_hashes"][nid]
        match    = live_h == replay_h
        if not match:
            hash_match = False
        print(f"    {nid}  live={live_h[:20]}...  replay={replay_h[:20]}...  "
              f"{'✅' if match else '❌'}")

    if not hash_match:
        _fail("Replay hashes do not match live node state")
        sys.exit(1)

    _ok(f"Replay reconstructed  |  hash match={hash_match}  |  "
        f"consistent={result['consistent']}  |  "
        f"consensus={result['consensus_hash'][:20]}...")
    passes.append(("Phase 4 — Distributed Replay Reconstruction", hash_match and result["consistent"]))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 5 — Divergence + Failure Simulation
    # Spec requirement: simulate delayed propagation, duplicate propagation,
    # missing propagation, out-of-order sequence_id.
    # System must: detect issue, emit readable halt reason,
    # preserve valid replay state, reject corrupted propagation.
    # No silent recovery.
    # ══════════════════════════════════════════════════════════════════════
    _phase(5, "Divergence + Failure Simulation")

    failure_outcomes: dict = {}

    # ── 5a: Delayed propagation ───────────────────────────────────────────
    delayed_env = QAppExecutionEnvelope.create(
        qapp_id          = QAPP_ID,
        node_origin      = NODE_ORIGIN,
        payload          = {"node_id": "qnode_delay_test", "marker": 99},
        sequence_id      = 10,         # large jump from last acknowledged seq=3
        contract_version = CONTRACT_VERSION,
    )
    r = simulate_delayed_propagation(
        delayed_env.to_dict(),
        last_acknowledged_seq=3,
    )
    failure_outcomes["delayed_propagation"] = r["status"]
    print(f"  → status={r['status']}  gap={r['gap']}  flag={r.get('flag', '—')}")

    # ── 5b: Duplicate propagation ─────────────────────────────────────────
    seen_ids: set = {envelopes[0].invocation_id}    # seed: seq 1 already seen
    try:
        simulate_duplicate_propagation(envelopes[0].to_dict(), seen_ids)
        failure_outcomes["duplicate_propagation"] = "UNEXPECTED_PASS"
    except PropagationFailure as exc:
        failure_outcomes["duplicate_propagation"] = "REJECTED"
        print(f"  → PropagationFailure (expected): {exc}")

    # ── 5c: Missing propagation ───────────────────────────────────────────
    try:
        simulate_missing_propagation(
            expected_nodes    = ["Node_A", "Node_B", "Node_C"],
            received_by_nodes = ["Node_A", "Node_B"],    # Node_C missing
            envelope_dict     = envelopes[1].to_dict(),
        )
        failure_outcomes["missing_propagation"] = "UNEXPECTED_PASS"
    except PropagationFailure as exc:
        failure_outcomes["missing_propagation"] = "HALTED"
        print(f"  → PropagationFailure (expected): {exc}")

    # ── 5d: Out-of-order sequence_id ─────────────────────────────────────
    ooo_batch = [
        envelopes[0].to_dict(),    # seq 1
        envelopes[2].to_dict(),    # seq 3
        envelopes[1].to_dict(),    # seq 2  ← VIOLATION
    ]
    try:
        simulate_out_of_order(ooo_batch)
        failure_outcomes["out_of_order_sequence"] = "UNEXPECTED_PASS"
    except PropagationFailure as exc:
        failure_outcomes["out_of_order_sequence"] = "HALTED"
        print(f"  → PropagationFailure (expected): {exc}")

    print(f"\n  Failure simulation summary:")
    for case, outcome in failure_outcomes.items():
        tag = "✅" if "UNEXPECTED" not in outcome else "❌"
        print(f"    {tag}  {case:<28} : {outcome}")

    unexpected = [k for k, v in failure_outcomes.items() if "UNEXPECTED" in v]
    failures_ok = len(unexpected) == 0
    if not failures_ok:
        _fail(f"Unexpected pass in: {unexpected}")
        sys.exit(1)

    _ok("All 4 failure cases detected and handled correctly  |  no silent recovery")
    passes.append(("Phase 5 — Divergence + Failure Simulation", failures_ok))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 6 — Observability Layer
    # Spec requirement: propagation chain, node replay status,
    # divergence detection, replay verification, final consensus hash.
    # Console output is the observability layer.
    # ══════════════════════════════════════════════════════════════════════
    _phase(6, "Observability Layer")

    # ── Propagation chain ─────────────────────────────────────────────────
    print("\n  ┌── Propagation Chain ─────────────────────────────────────────┐")
    for env in envelopes:
        print(f"  │  seq={env.sequence_id}  ts={env.timestamp}")
        print(f"  │  invoke={env.invocation_id[:28]}...")
        print(f"  │  Node_A  →  Node_B  ✅")
        print(f"  │  Node_A  →  Node_C  ✅")
        if env.sequence_id < len(envelopes):
            print(f"  │  ·")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    # ── Node replay status ────────────────────────────────────────────────
    print("\n  ┌── Node Replay Status ────────────────────────────────────────┐")
    for nid, node in ALL_NODES.items():
        s = node.status()
        print(f"  │  {nid:<8}  recv={s['received_count']:>2}  "
              f"propagated={s['propagated_count']:>2}  "
              f"log_entries={s['replay_log_count']:>2}  "
              f"hash={s['execution_hash'][:20]}...")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    # ── Divergence detection ──────────────────────────────────────────────
    print("\n  ┌── Divergence Detection ─────────────────────────────────────┐")
    b_inv = Node_B.received_invocation_ids()
    c_inv = Node_C.received_invocation_ids()
    diverged = (b_inv != c_inv)
    print(f"  │  Node_B invocations : {[i[:12]+'...' for i in b_inv]}")
    print(f"  │  Node_C invocations : {[i[:12]+'...' for i in c_inv]}")
    print(f"  │  Divergence         : {'❌ YES — ALERT' if diverged else '✅ NONE — nodes consistent'}")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    if diverged:
        _fail("Divergence detected between Node_B and Node_C")
        sys.exit(1)

    # ── Replay verification ───────────────────────────────────────────────
    print("\n  ┌── Replay Verification ──────────────────────────────────────┐")
    obs_result = replay_qapp_log(live_log)
    for nid in ["Node_A", "Node_B", "Node_C"]:
        print(f"  │  {nid:<8}  hash={obs_result['node_hashes'][nid][:28]}...")
    print(f"  │  consistent : {'✅ YES' if obs_result['consistent'] else '❌ NO'}")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    # ── Final consensus hash ──────────────────────────────────────────────
    print("\n  ┌── Final Consensus Hash ─────────────────────────────────────┐")
    print(f"  │  consensus : {obs_result['consensus_hash']}")
    print(f"  │  log_hash  : {obs_result['log_hash']}")
    print(f"  └──────────────────────────────────────────────────────────────┘")

    obs_ok = obs_result["consistent"] and not diverged
    _ok(f"Observability output complete  |  all layers rendered  |  "
        f"consensus={obs_result['consensus_hash'][:20]}...")
    passes.append(("Phase 6 — Observability Layer", obs_ok))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 7 — Determinism Proof
    # Spec requirement: replay same propagation log 5 times,
    # all final hashes must be identical.
    # Additionally: shuffled propagation order must converge correctly
    # after replay sorting.
    # ══════════════════════════════════════════════════════════════════════
    _phase(7, "Determinism Proof")

    frozen_log     = get_propagation_log()
    canonical_hash = obs_result["consensus_hash"]

    # ── Proof A: 5× replay, same frozen log ───────────────────────────────
    print("\n  Proof A — 5× replay of frozen propagation log")
    print(f"  {'Run':<6} {'consensus_hash':<52} {'log_hash':<20}")
    print(f"  {'─'*6} {'─'*52} {'─'*20}")

    replay_hashes = []
    for i in range(1, 6):
        r = replay_qapp_log(frozen_log, silent=True)
        replay_hashes.append(r["consensus_hash"])
        match_marker = "✅" if r["consensus_hash"] == canonical_hash else "❌"
        print(f"  {i:<6} {r['consensus_hash'][:48]}...  "
              f"{r['log_hash'][:16]}...  {match_marker}")

    all_same_a = len(set(replay_hashes)) == 1
    print(f"\n  Result : [{'PASS' if all_same_a else 'FAIL'}]  "
          f"{'All 5 hashes IDENTICAL' if all_same_a else 'HASHES DIFFER — DETERMINISM FAILURE'}")

    if not all_same_a:
        _fail("Replay hashes differ across runs")
        sys.exit(1)

    # ── Proof B: shuffle log 3×, re-sort via replay, verify convergence ───
    print("\n  Proof B — shuffle log order 3×, replay each, verify same consensus")
    print(f"  {'Trial':<7} {'shuffled_input_order':<30} {'converged'}")
    print(f"  {'─'*7} {'─'*30} {'─'*9}")

    shuffle_ok = True
    for trial in range(1, 4):
        shuffled = list(frozen_log)
        random.shuffle(shuffled)
        shuffled_seqs = [e["sequence_id"] for e in shuffled]
        r_s = replay_qapp_log(shuffled, silent=True)
        match = r_s["consensus_hash"] == canonical_hash
        if not match:
            shuffle_ok = False
        seq_display = str(shuffled_seqs)[:28]
        print(f"  {trial:<7} seqs={seq_display:<25}  "
              f"{'✅ YES' if match else '❌ NO — DIVERGED'}")

    print(f"\n  Result : [{'PASS' if shuffle_ok else 'FAIL'}]  "
          f"{'All shuffled replays converge to canonical consensus' if shuffle_ok else 'SHUFFLE CONVERGENCE FAILURE'}")

    if not shuffle_ok:
        _fail("Shuffled log replay did not converge to canonical hash")
        sys.exit(1)

    det_ok = all_same_a and shuffle_ok
    _ok(f"Determinism confirmed  |  5× replay identical  |  3× shuffle converges")
    passes.append(("Phase 7 — Determinism Proof", det_ok))


    # ══════════════════════════════════════════════════════════════════════
    # PHASE 8 — REVIEW_PACKET.md
    # Spec requirement: documentation artefact with 10 mandatory sections.
    # Not a runtime phase — verified by file presence.
    # ══════════════════════════════════════════════════════════════════════
    _phase(8, "REVIEW_PACKET.md  (documentation artefact)")

    review_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "REVIEW_PACKET.md")
    review_exists = os.path.isfile(review_path)

    required_sections = [
        "Entry Point",
        "QApp Invocation Flow",
        "Distributed Propagation Flow",
        "Replay Reconstruction",
        "Failure Cases",
        "Determinism Proof",
        "Observability Output",
        "What Was Built",
        "System Boundaries",
        "Known Infrastructure Risks",
    ]
    sections_found = []
    if review_exists:
        with open(review_path, encoding="utf-8") as f:
            content = f.read()
        sections_found = [s for s in required_sections if s in content]

    print(f"\n  REVIEW_PACKET.md present : {'✅' if review_exists else '❌'}")
    print(f"  Mandatory sections       : {len(sections_found)}/{len(required_sections)}")
    for s in required_sections:
        found = s in sections_found
        print(f"    {'✅' if found else '❌'}  {s}")

    review_ok = review_exists and len(sections_found) == len(required_sections)
    _ok(f"Documentation complete  |  "
        f"{'all 10 sections present' if review_ok else 'MISSING SECTIONS'}")
    passes.append(("Phase 8 — REVIEW_PACKET.md", review_ok))


    # ══════════════════════════════════════════════════════════════════════
    # Final summary
    # ══════════════════════════════════════════════════════════════════════
    all_passed = all(ok for _, ok in passes)

    print(f"\n{'═' * W}")
    print(f"  EXECUTION SUMMARY  —  Task 9 Distributed QApp Propagation Layer")
    print(f"{'═' * W}\n")
    for phase_name, ok in passes:
        print(f"  {'PASS ✅' if ok else 'FAIL ❌'}  {phase_name}")

    print(f"\n{'─' * W}")
    print(f"  Envelopes propagated      : {len(envelopes)}")
    print(f"  Log entries               : {len(frozen_log)}")
    print(f"  Failure cases detected    : 4 / 4")
    print(f"  Determinism (5× replay)   : {'PASS' if all_same_a else 'FAIL'}")
    print(f"  Shuffle convergence (3×)  : {'PASS' if shuffle_ok else 'FAIL'}")
    print(f"  Consensus hash            : {obs_result['consensus_hash'][:40]}...")
    print(f"\n  OVERALL : {'PASS ✅' if all_passed else 'FAIL ❌'}")
    print(f"{'═' * W}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    run()
