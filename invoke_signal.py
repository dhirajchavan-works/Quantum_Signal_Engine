# invoke_signal.py
# External Invocation Demo — generate_signal()
#
# This file demonstrates exactly how any external system
# (BHIV Core, TANTRA, or any other consumer) calls the signal generator.
#
# THIS FILE DOES NOT:
#   - Call any execution engine
#   - Control batching or ordering
#   - Make execution decisions
#   - Perform orchestration
#
# THIS FILE ONLY:
#   - Shows external callers how to invoke generate_signal()
#   - Shows how to use validate_contract()
#   - Shows how to use SequenceRegistry for multi-call scenarios
#   - Demonstrates rejection of invalid inputs
#
# Usage:
#   python invoke_signal.py

import io
import json
import os
import sys

# Resolve src/ relative to this file — works from any working directory
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "src"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from signal_generator import generate_signal, SequenceRegistry
from validator import ValidationError, validate_contract


def _sep(title=""):
    line = "-" * 60
    if title:
        print(f"\n{line}\n  {title}\n{line}")
    else:
        print(line)


def main():
    print("\n" + "=" * 60)
    print("  invoke_signal.py — External Invocation Demo")
    print("  Marine Intelligence System | BHIV Core Interface")
    print("=" * 60)

    # ── Demo 1: Single external call ──────────────────────────
    _sep("Demo 1 — Single Call: generate_signal()")

    payload = {
        "node_id":      "qnode_01",
        "energy_delta": 0.0001,
        "iterations":   120,
        "confidence":   0.92,
        "variance":     0.002,
    }

    print("\nInput payload:")
    print(json.dumps(payload, indent=2))

    event = generate_signal(payload)

    print("\nCore-ready signal event:")
    print(json.dumps(event, indent=2))

    # ── Demo 2: Contract Validation ──────────────────────────
    _sep("Demo 2 — Contract Validation: validate_contract()")

    result = validate_contract(event)
    print(f"\n  validate_contract() → {result}")

    if result["status"] == "PASS":
        print("  All required contract fields confirmed present.")
        print("  Event is Core-passable as-is — no transformation required.")
    else:
        print("  CONTRACT FAILURE:")
        for err in result.get("errors", []):
            print(f"    • {err}")
        sys.exit(1)

    # ── Demo 3: SequenceRegistry — multi-call per node ────────
    _sep("Demo 3 — SequenceRegistry: per-node monotonic sequence")

    registry = SequenceRegistry()

    multi_payloads = [
        {"node_id": "qnode_01", "energy_delta": 0.0001,
         "iterations": 120, "confidence": 0.92, "variance": 0.002},
        {"node_id": "qnode_01", "energy_delta": 0.0002,
         "iterations": 200, "confidence": 0.91, "variance": 0.003},
        {"node_id": "qnode_02", "energy_delta": 0.0005,
         "iterations": 80,  "confidence": 0.88, "variance": 0.004},
    ]

    print("\n  Generating 3 signals with shared SequenceRegistry:\n")
    for p in multi_payloads:
        e = generate_signal(p, seq_registry=registry)
        print(f"    node_id={e['node_id']:<12}  "
              f"sequence_id={e['transition']['sequence_id']}  "
              f"trace_id={e['trace_id']:<30}  "
              f"next={e['transition']['next']}")

    print(f"\n  Registry snapshot: {registry.snapshot()}")
    print("  qnode_01 → seq 1, 2  (independent, monotonic)")
    print("  qnode_02 → seq 1     (independent counter)")

    # ── Demo 4: Invalid Input Rejection ──────────────────────
    _sep("Demo 4 — Invalid Input Rejection")

    bad_cases = [
        {
            "label": "Missing energy_delta",
            "payload": {
                "node_id": "qnode_bad",
                "iterations": 10,
                "confidence": 0.80,
                "variance": 0.001,
            },
        },
        {
            "label": "confidence out of range (1.5)",
            "payload": {
                "node_id": "qnode_bad2",
                "energy_delta": 0.0002,
                "iterations": 5,
                "confidence": 1.5,
                "variance": 0.001,
            },
        },
        {
            "label": "negative variance",
            "payload": {
                "node_id": "qnode_bad3",
                "energy_delta": 0.0001,
                "iterations": 10,
                "confidence": 0.90,
                "variance": -0.001,
            },
        },
    ]

    for case in bad_cases:
        print(f"\n  [{case['label']}]")
        try:
            generate_signal(case["payload"])
            print("    [UNEXPECTED PASS — should have been rejected]")
        except ValidationError as exc:
            print(f"    -> ValidationError (expected): {exc}")

    # ── Demo 5: SUSPENDED and DIVERGED states ────────────────
    _sep("Demo 5 — State Variants (SUSPENDED / DIVERGED)")

    state_cases = [
        {
            "label": "SUSPENDED — low confidence",
            "payload": {
                "node_id": "qnode_03",
                "energy_delta": 0.0003,
                "iterations": 80,
                "confidence": 0.55,
                "variance": 0.003,
            },
        },
        {
            "label": "DIVERGED — high energy_delta",
            "payload": {
                "node_id": "qnode_04",
                "energy_delta": 0.05,
                "iterations": 200,
                "confidence": 0.88,
                "variance": 0.001,
            },
        },
    ]

    for case in state_cases:
        e = generate_signal(case["payload"])
        contract = validate_contract(e)
        print(f"\n  [{case['label']}]")
        print(f"    next={e['transition']['next']:<12}  "
              f"cause={e['transition']['cause'][:50]}...")
        print(f"    contract={contract['status']}")

    _sep()
    print("\n  External invocation demo complete.")
    print("  All signals are Core-passable without transformation.\n")


if __name__ == "__main__":
    main()
