# run_signal.py — MAIN ENTRY POINT
#
# Usage:  python run_signal.py
#
# Proves: 1 signal → 1 execution → 1 observable state change
# Uses Kanishk's REAL physical engine (MultiZoneExecutor + DeterministicTransitionEngine)
#
# Phases:
#   4 — Single signal execution
#   5 — Failure handling at execution level
#   6 — Determinism proof (5 runs, identical)
#   7 — Observable state proof (before/after + hash chain)
#   8 — Traceability (trace_id end-to-end)

import io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import signal_generator
import execution_engine
import integration_runner
from validator import ValidationError

# ── Inputs ────────────────────────────────────────────────────────────────────
SAMPLE_INPUT = {
    "node_id": "qnode_01", "energy_delta": 0.0001,
    "iterations": 120, "confidence": 0.92, "variance": 0.002,
}

FAILURE_INPUTS = [
    {"label": "Low confidence -> SUSPENDED",
     "payload": {"node_id": "qnode_02", "energy_delta": 0.0003, "iterations": 80, "confidence": 0.55, "variance": 0.003}},
    {"label": "High energy_delta -> DIVERGED",
     "payload": {"node_id": "qnode_03", "energy_delta": 0.05,   "iterations": 200, "confidence": 0.88, "variance": 0.001}},
    {"label": "Missing field -> REJECTED",
     "payload": {"node_id": "qnode_04", "iterations": 50,        "confidence": 0.90, "variance": 0.002}},
    {"label": "confidence out of range -> REJECTED",
     "payload": {"node_id": "qnode_05", "energy_delta": 0.0002, "iterations": 60, "confidence": 1.5, "variance": 0.001}},
]

def _sep(title=""):
    line = "-" * 60
    if title: print(f"\n{line}\n  {title}\n{line}")
    else:      print(line)

def run():
    print("\n" + "=" * 60)
    print("  Quantum Signal Generator — Integrated with Kanishk's Engine")
    print("  Marine Intelligence System | BHIV Core Interface")
    print("=" * 60)

    # ── PHASE 4 — Single Execution ────────────────────────────────
    _sep("PHASE 4 -- Single Execution (Signal Generator)")
    print("\nInput:")
    print(json.dumps(SAMPLE_INPUT, indent=2))
    event = signal_generator.generate_state_event(SAMPLE_INPUT)
    print("\nSignal Output:")
    print(json.dumps(event, indent=2))

    # ── PHASE 5 — Failure Handling ────────────────────────────────
    _sep("PHASE 5 -- Failure Handling (Execution Level)")
    execution_engine.reset_state()
    for case in FAILURE_INPUTS:
        print(f"\n  >>  {case['label']}")
        result = integration_runner.run_integration(case["payload"], trace_id="test-failure")
        print(f"      action={result['execution']['action']}  final_state={result['final_state']}")

    # ── PHASE 6 — Determinism Proof ───────────────────────────────
    _sep("PHASE 6 -- Determinism Proof (5 runs, same input)")
    execution_engine.reset_state()
    results = []
    for i in range(1, 6):
        execution_engine.reset_state()
        e = signal_generator.generate_state_event(SAMPLE_INPUT)
        results.append(json.dumps(e, sort_keys=True))
        print(f"  Run {i}: transition={e['transition']['next']!r:<12}  sigma={e['uncertainty_envelope']['sigma']}  ts={e['transition']['ts']}")
    all_same = all(r == results[0] for r in results)
    print()
    print(f"  [{'PASS' if all_same else 'FAIL'}] All 5 outputs IDENTICAL -- determinism {'CONFIRMED' if all_same else 'FAILED'}.")

    # ── PHASE 7 — Observable State Proof ─────────────────────────
    _sep("PHASE 7 -- Observable State Proof (Kanishk's Engine)")
    execution_engine.reset_state()

    pre_hash  = execution_engine.get_global_hash()
    pre_state = execution_engine.get_state()

    print(f"\n  Before execution:")
    print(f"    state[bow].corrosion_depth  = {pre_state['bow']['corrosion_depth']}")
    print(f"    state[bow].coating_thickness= {pre_state['bow']['coating_thickness']}")
    print(f"    state[bow].risk_score       = {pre_state['bow']['risk_score']}")
    print(f"    global_hash = {pre_hash[:32]}...")

    result = integration_runner.run_integration(SAMPLE_INPUT, trace_id="test-trace-001", target_zone="bow")

    post_hash  = execution_engine.get_global_hash()
    post_state = execution_engine.get_state()

    print(f"\n  After execution:")
    print(f"    state[bow].corrosion_depth  = {post_state['bow']['corrosion_depth']}")
    print(f"    state[bow].coating_thickness= {post_state['bow']['coating_thickness']}")
    print(f"    state[bow].risk_score       = {post_state['bow']['risk_score']}")
    print(f"    global_hash = {post_hash[:32]}...")

    hash_changed  = pre_hash != post_hash
    state_changed = pre_state['bow']['corrosion_depth'] != post_state['bow']['corrosion_depth']

    print(f"\n  Hash changed:  {hash_changed}")
    print(f"  State changed: {state_changed}")
    print(f"  [{'PASS' if (hash_changed and state_changed) else 'FAIL'}] Observable state change CONFIRMED in Kanishk's engine.")

    # ── PHASE 8 — Traceability ────────────────────────────────────
    _sep("PHASE 8 -- Traceability (trace_id end-to-end)")
    execution_engine.reset_state()
    result = integration_runner.run_integration(SAMPLE_INPUT, trace_id="test-trace-001", target_zone="bow")

    print(f"\n  trace_id   : {result['trace_id']}")
    print(f"  node_id    : {result['node_id']}")
    print(f"  final_state: {result['final_state']}")
    if result['execution'].get('zone_state'):
        zs = result['execution']['zone_state']
        print(f"  zone_state : bow → corrosion={zs['corrosion_depth']:.8f}  risk={zs['risk_score']:.8f}")

    trace_ok = (
        result["trace_id"]    == "test-trace-001"
        and result["node_id"] == "qnode_01"
        and result["final_state"] == "CONVERGED"
    )
    print(f"\n  [{'PASS' if trace_ok else 'FAIL'}] trace_id + node_id + final_state all present and correct.")

    # ── Summary ────────────────────────────────────────────────────
    _sep()
    overall = all_same and hash_changed and state_changed and trace_ok
    print(f"\n  EXECUTION COMPLETE  |  Overall: {'PASS ✅' if overall else 'FAIL ❌'}")
    print()
    sys.exit(0 if overall else 1)

if __name__ == "__main__":
    run()
