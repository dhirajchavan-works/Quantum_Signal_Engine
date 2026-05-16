import hashlib
import sys
from core import QAppExecutionEnvelope, QAppNode, PropagationEngine
from engine import (
    sort_envelopes,
    reconstruct_chronological,
    deterministic_replay_verify,
    simulate_failure_corrupted_hash,
    simulate_failure_sequence_gap,
    propagate_ordered,
    SequenceGapError,
    CorruptedHashError,
    ReplayDivergenceError,
)

SEP = "-" * 64
HEADER = "=" * 64


def h(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def make_envelope(trace_id, qapp_id, origin, inv_id, payload, seq, ts, ver="2.0"):
    return QAppExecutionEnvelope(
        trace_id=trace_id,
        qapp_id=qapp_id,
        node_origin=origin,
        invocation_id=inv_id,
        payload_hash=h(payload),
        sequence_id=seq,
        timestamp=ts,
        contract_version=ver,
    )


def print_section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def build_nodes():
    return {
        "Node_A": QAppNode("Node_A"),
        "Node_B": QAppNode("Node_B"),
        "Node_C": QAppNode("Node_C"),
    }


def run():
    print(f"\n{HEADER}")
    print("  Distributed QApp Propagation Layer")
    print("  Marine Intelligence System | Task 9")
    print(HEADER)

    # ── PHASE 1: Standard Propagation ────────────────────────
    print_section("PHASE 1 -- Standard Propagation")

    nodes = build_nodes()
    engine = PropagationEngine(nodes)

    env1 = make_envelope("trace-001", "qapp-marine-01", "Node_A", "inv-001", "payload_alpha", 1, 100)
    env2 = make_envelope("trace-001", "qapp-marine-01", "Node_A", "inv-002", "payload_beta",  2, 200)
    env3 = make_envelope("trace-001", "qapp-marine-01", "Node_A", "inv-003", "payload_gamma", 3, 300)

    for env in [env1, env2, env3]:
        nodes["Node_A"].log_and_compute(env)

    path = []
    engine.propagate(env1, path)
    engine.propagate(env2, path)
    engine.propagate(env3, path)

    print(f"  Node_A replay_log entries : {len(nodes['Node_A'].replay_log)}")
    print(f"  Node_B received_invocations: {len(nodes['Node_B'].received_invocations)}")
    print(f"  Node_C received_invocations: {len(nodes['Node_C'].received_invocations)}")
    print(f"  Node_A execution_hash      : {nodes['Node_A'].execution_hash[:20]}...")
    print(f"  Propagation path           : {path}")

    # ── PHASE 2: Duplicate Suppression ───────────────────────
    print_section("PHASE 2 -- Duplicate / Replay Suppression")

    pre = len(nodes["Node_B"].received_invocations)
    nodes["Node_B"].log_and_compute(env1)
    nodes["Node_B"].log_and_compute(env1)
    post = len(nodes["Node_B"].received_invocations)
    status = "PASS" if pre == post else "FAIL"
    print(f"  Node_B invocations before duplicate inject : {pre}")
    print(f"  Node_B invocations after  duplicate inject : {post}")
    print(f"  Duplicate suppression                      : [{status}]")

    # ── PHASE 3: Out-of-Order Sorting Convergence ────────────
    print_section("PHASE 3 -- Out-of-Order Sort Convergence Proof")

    nodes2 = build_nodes()
    engine2 = PropagationEngine(nodes2)

    scrambled = [env3, env1, env2]
    print(f"  Input order  : {[e.sequence_id for e in scrambled]}")
    sorted_envs = sort_envelopes(scrambled)
    print(f"  Sorted order : {[e.sequence_id for e in sorted_envs]}")

    for env in sorted_envs:
        nodes2["Node_A"].log_and_compute(env)

    path2 = propagate_ordered(engine2, scrambled)
    print(f"  Propagation path (sorted)  : {path2}")

    ordered_log = reconstruct_chronological(nodes2["Node_A"])
    seqs = [e.sequence_id for e in ordered_log]
    expected = sorted(seqs)
    status = "PASS" if seqs == expected else "FAIL"
    print(f"  Chronological reconstruction: {seqs}")
    print(f"  Sort convergence            : [{status}]")

    # ── PHASE 4: Deterministic Replay Verification (5x) ──────
    print_section("PHASE 4 -- Deterministic Replay Verification (5 runs)")

    for node_id in ["Node_A", "Node_B", "Node_C"]:
        node = nodes["Node_A"] if node_id == "Node_A" else nodes2["Node_A"] if node_id == "Node_A" else nodes2.get(node_id, nodes[node_id])
        target_node = nodes["Node_A"] if node_id == "Node_A" else nodes[node_id]
        try:
            result_hash = deterministic_replay_verify(target_node, runs=5)
            print(f"  {node_id} | 5-run replay hash : {result_hash[:20]}... | [PASS]")
        except ReplayDivergenceError as ex:
            print(f"  {node_id} | [FAIL] {ex}")

    # ── PHASE 5: Failure Injection — Corrupted Hash ───────────
    print_section("PHASE 5 -- Failure Injection: Corrupted Payload Hash")

    env_corrupt = make_envelope("trace-999", "qapp-marine-01", "Node_A", "inv-corrupt", "real_payload", 99, 999)
    try:
        simulate_failure_corrupted_hash(nodes, engine, env_corrupt, "TAMPERED_PAYLOAD")
        print("  [FAIL] CorruptedHashError not raised")
    except CorruptedHashError as ex:
        print(f"  CorruptedHashError caught (expected):")
        print(f"    {ex}")
        print(f"  [PASS]")

    # ── PHASE 6: Failure Injection — Sequence Gap ─────────────
    print_section("PHASE 6 -- Failure Injection: Sequence Gap Detection")

    env_gap_1 = make_envelope("trace-002", "qapp-marine-02", "Node_A", "inv-g1", "payload_1", 1, 10)
    env_gap_2 = make_envelope("trace-002", "qapp-marine-02", "Node_A", "inv-g2", "payload_2", 3, 30)

    gap_node = QAppNode("Node_Gap")
    gap_node.log_and_compute(env_gap_1)
    gap_node.log_and_compute(env_gap_2)

    try:
        simulate_failure_sequence_gap(gap_node, gap_node.replay_log)
        print("  [FAIL] SequenceGapError not raised")
    except SequenceGapError as ex:
        print(f"  SequenceGapError caught (expected):")
        print(f"    {ex}")
        print(f"  [PASS]")

    # ── PHASE 7: Full Replay Consistency Across Nodes ─────────
    print_section("PHASE 7 -- Cross-Node Replay Hash Consistency")

    nodes3 = build_nodes()
    engine3 = PropagationEngine(nodes3)
    test_envs = [
        make_envelope("trace-003", "qapp-marine-03", "Node_A", f"inv-x{i}", f"payload_{i}", i, i * 100)
        for i in range(1, 4)
    ]
    for env in test_envs:
        nodes3["Node_A"].log_and_compute(env)
    path3 = []
    for env in test_envs:
        engine3.propagate(env, path3)

    inv_sets = {}
    for node_id in ["Node_B", "Node_C"]:
        h_val = deterministic_replay_verify(nodes3[node_id], runs=5)
        print(f"  {node_id} | 5-run replay hash : {h_val[:20]}... | [PASS]")
        inv_sets[node_id] = set(nodes3[node_id].received_invocations.keys())

    consistent = inv_sets["Node_B"] == inv_sets["Node_C"]
    print(f"  Node_B invocations : {sorted(inv_sets['Node_B'])}")
    print(f"  Node_C invocations : {sorted(inv_sets['Node_C'])}")
    print(f"  Cross-node invocation set parity: [{'PASS' if consistent else 'FAIL'}]")

    print(f"\n{HEADER}")
    print("  EXECUTION COMPLETE")
    print(HEADER)
    print()
    sys.exit(0)


if __name__ == "__main__":
    run()
