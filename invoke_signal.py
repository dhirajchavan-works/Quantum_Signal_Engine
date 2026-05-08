# invoke_signal.py
# External invocation demo for generate_signal().
#
# This file demonstrates how any external system (BHIV Core, TANTRA, etc.)
# would call the signal generator directly.
#
# This is NOT orchestration.
# This does NOT call any execution engine.
# This does NOT control batching, ordering, or execution flow.
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

from signal_generator import generate_signal
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

    # ── Single external call ──────────────────────────────────
    _sep("External Call — generate_signal()")

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

    print("\nSignal event (Core-ready):")
    print(json.dumps(event, indent=2))

    # ── Contract validation ───────────────────────────────────
    _sep("Contract Validation — validate_contract()")

    result = validate_contract(event)
    print(f"\n  Contract check: {result['status']}")
    if result["status"] == "FAIL":
        for err in result.get("errors", []):
            print(f"    • {err}")
        sys.exit(1)

    # ── Invalid input demo ────────────────────────────────────
    _sep("Invalid Input — rejection demo")

    bad_payloads = [
        {
            "label": "Missing energy_delta",
            "payload": {"node_id": "qnode_bad", "iterations": 10, "confidence": 0.80, "variance": 0.001},
        },
        {
            "label": "confidence out of range",
            "payload": {"node_id": "qnode_bad2", "energy_delta": 0.0002, "iterations": 5, "confidence": 1.5, "variance": 0.001},
        },
    ]

    for case in bad_payloads:
        print(f"\n  Input: {case['label']}")
        try:
            generate_signal(case["payload"])
            print("    [UNEXPECTED PASS]")
        except ValidationError as exc:
            print(f"    -> ValidationError (expected): {exc}")

    _sep()
    print("\n  External invocation complete.\n")


if __name__ == "__main__":
    main()
