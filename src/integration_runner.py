# integration_runner.py
# Task 5 — Direct Invocation Bridge
#
# Flow (as per PDF instruction):
#   input_payload
#       → generate_state_event()    [Dhiraj — signal layer]
#       → execute_event()           [Kanishk — physical engine]
#       → observable state change   [proven]
#
# No file I/O. No async. No queue. Just direct function calls.
# trace_id carried from input → event → execution → output.

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import signal_generator
import execution_engine
from validator import ValidationError


def run_integration(input_payload: dict,
                    trace_id: str = "trace-001",
                    target_zone: str = "bow") -> dict:
    """
    End-to-end bridge: input → signal → Kanishk's engine → observable result.

    Args:
        input_payload : dict  — raw quantum node snapshot
        trace_id      : str   — carried through entire pipeline
        target_zone   : str   — hull zone to apply physical transition to

    Returns:
        dict with trace_id, node_id, event, execution, final_state
    """
    node_id = input_payload.get("node_id", "UNKNOWN")

    # Step 1 — Generate signal (Dhiraj)
    try:
        event = signal_generator.generate_state_event(input_payload)
    except ValidationError as exc:
        print(f"[REJECTED] trace={trace_id}  reason=invalid_schema  detail={exc}")
        return {
            "trace_id":    trace_id,
            "node_id":     node_id,
            "event":       None,
            "execution":   {"action": "REJECTED", "reason": str(exc)},
            "final_state": None,
        }

    # Step 2 — Execute through Kanishk's engine
    execution_result = execution_engine.execute_event(event,
                                                      trace_id=trace_id,
                                                      target_zone=target_zone)

    return {
        "trace_id":    trace_id,
        "node_id":     event["node_ref"],
        "event":       event,
        "execution":   execution_result,
        "final_state": execution_result["final_state"],
    }
