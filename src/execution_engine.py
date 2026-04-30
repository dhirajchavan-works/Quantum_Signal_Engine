# execution_engine.py
# Task 5 — Kanishk's Real Engine Integration
#
# This is NOT a stub. This calls Kanishk's actual:
#   - physical_engine.ship_state_vector.ShipState / ShipStateVector
#   - physical_engine.transition_engine.TransitionInput / DeterministicTransitionEngine
#   - physical_engine.multi_zone_executor.MultiZoneExecutor
#
# Maps Dhiraj's signal (CONVERGED / SUSPENDED / DIVERGED) → physical TransitionInput
# → runs through Kanishk's MultiZoneExecutor → observable ShipState change
#
# Execution Policy:
#   CONVERGED  → apply standard physical transition → state UPDATED
#   SUSPENDED  → skip (low confidence) → state UNCHANGED  → [SKIPPED]
#   DIVERGED   → log only, quarantine → state UNCHANGED   → [DIVERGED]
#   Bad schema → reject before any state touch             → [REJECTED]

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validator import validate_output, ValidationError
from physical_engine.ship_state_vector import ShipState, ShipStateVector
from physical_engine.transition_engine import TransitionInput, DeterministicTransitionEngine
from physical_engine.multi_zone_executor import MultiZoneExecutor

# ── Default hull zones (Kanishk's 4-zone model) ───────────────────────────────
_DEFAULT_ZONES = {
    "bow":       ShipState.create("bow",       corrosion_depth=0.10, coating_thickness=4.5,  barnacle_density=2.0, roughness=0.30),
    "stern":     ShipState.create("stern",     corrosion_depth=0.30, coating_thickness=3.0,  barnacle_density=5.0, roughness=0.80),
    "port":      ShipState.create("port",      corrosion_depth=0.05, coating_thickness=5.0,  barnacle_density=0.5, roughness=0.10),
    "starboard": ShipState.create("starboard", corrosion_depth=0.20, coating_thickness=4.0,  barnacle_density=3.0, roughness=0.50),
}

# ── Singleton executor (Kanishk's engine) ─────────────────────────────────────
_executor: MultiZoneExecutor = MultiZoneExecutor(ShipStateVector(_DEFAULT_ZONES))

# ── Execution log ─────────────────────────────────────────────────────────────
_execution_log: list = []


# ── Mapping: Dhiraj signal → physical rates ───────────────────────────────────
# When a node CONVERGES, its energy_delta/confidence/variance describe
# the VQE output. We map these to physical hull transition rates:
#   - Low energy_delta → stable chemistry → low corrosion rate
#   - High confidence  → reliable estimate → normal coating degradation
#   - Low variance     → tight bounds → low barnacle uncertainty

def _signal_to_transition_rates(event: dict, zone_id: str) -> TransitionInput:
    """
    Convert a CONVERGED engine event into Kanishk's TransitionInput.
    Pure deterministic mapping — same event → same rates, always.
    """
    ue    = event["uncertainty_envelope"]
    conf  = ue["confidence"]    # 0.0 – 1.0
    sigma = ue["sigma"]         # sqrt(variance)

    # Deterministic physical rate derivation from quantum signal
    corrosion_rate           = round(0.02 + (1.0 - conf) * 0.05, 8)   # lower conf → more corrosion
    coating_degradation_rate = round(0.01 + sigma * 0.5,          8)   # higher sigma → more coating loss
    barnacle_growth_rate     = round(0.1  + (1.0 - conf) * 0.3,   8)   # lower conf → more fouling
    roughness_rate           = round(0.002 + sigma * 0.05,        8)
    dt                       = 1.0                                      # 1 time unit per signal event

    return TransitionInput(
        zone_id=zone_id,
        corrosion_rate=corrosion_rate,
        coating_degradation_rate=coating_degradation_rate,
        barnacle_growth_rate=barnacle_growth_rate,
        roughness_rate=roughness_rate,
        dt=dt,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_state() -> dict:
    """Return current zone states as a dict (observable snapshot)."""
    return {
        zid: {
            "corrosion_depth":   s.corrosion_depth,
            "coating_thickness": s.coating_thickness,
            "barnacle_density":  s.barnacle_density,
            "roughness":         s.roughness,
            "risk_score":        s.risk_score,
        }
        for zid, s in _executor.current_state.get_all().items()
    }

def get_global_hash() -> str:
    """Return Kanishk's global state hash (proves state changed)."""
    return _executor.global_hash

def get_execution_log() -> list:
    return list(_execution_log)

def reset_state() -> None:
    """Reset executor and log — for test isolation only."""
    global _executor
    _executor = MultiZoneExecutor(ShipStateVector(_DEFAULT_ZONES))
    _execution_log.clear()


def execute_event(event: dict, trace_id: str = "no-trace",
                  target_zone: str = "bow") -> dict:
    """
    Consume a validated engine event, route through Kanishk's engine.

    Args:
        event       : engine_event_version 2.0 dict from generate_state_event()
        trace_id    : carried through pipeline for full traceability
        target_zone : which hull zone to apply the signal to (default: 'bow')

    Returns:
        dict: trace_id, node_id, final_state, action, reason,
              pre_hash, post_hash, zone_state (after)

    Policy:
        CONVERGED → TransitionInput → MultiZoneExecutor.execute_batch() → state UPDATED
        SUSPENDED → [SKIPPED]   no execution
        DIVERGED  → [DIVERGED]  logged, not applied
        Bad schema→ [REJECTED]  before any state access
    """
    # 1. Schema guard — reject anything malformed before touching Kanishk's engine
    try:
        validate_output(event)
    except ValidationError as exc:
        result = {
            "trace_id": trace_id, "node_id": event.get("node_ref", "UNKNOWN"),
            "final_state": None, "action": "REJECTED",
            "reason": f"invalid_schema: {exc}",
            "pre_hash": get_global_hash(), "post_hash": get_global_hash(), "zone_state": None,
        }
        _execution_log.append(result)
        print(f"[REJECTED] trace={trace_id}  reason=invalid_schema")
        return result

    node_id    = event["node_ref"]
    next_state = event["transition"]["next"]
    cause      = event["transition"]["cause"]
    pre_hash   = get_global_hash()

    if next_state == "CONVERGED":
        # Build TransitionInput from signal — map quantum params to physical rates
        inp = _signal_to_transition_rates(event, zone_id=target_zone)

        # Call Kanishk's MultiZoneExecutor
        batch = _executor.execute_batch({target_zone: inp}, transition_name="standard")

        post_hash = get_global_hash()
        zone_after = _executor.get_zone(target_zone)

        action = "EXECUTED"
        reason = f"transition applied via Kanishk's engine | batch_id={batch.batch_id} | {cause}"
        print(f"[EXECUTION] node={node_id} transitioned to CONVERGED  "
              f"zone={target_zone}  batch={batch.batch_id}  trace={trace_id}")
        print(f"            risk_score: {_DEFAULT_ZONES[target_zone].risk_score:.8f} → {zone_after.risk_score:.8f}")
        print(f"            pre_hash={pre_hash[:16]}...  post_hash={post_hash[:16]}...")

        result = {
            "trace_id":    trace_id,
            "node_id":     node_id,
            "final_state": next_state,
            "action":      action,
            "reason":      reason,
            "pre_hash":    pre_hash,
            "post_hash":   post_hash,
            "zone_state":  zone_after.to_dict(),
        }

    elif next_state == "SUSPENDED":
        action = "SKIPPED"; reason = f"low_confidence: {cause}"
        print(f"[SKIPPED]   node={node_id}  reason=low_confidence  trace={trace_id}")
        result = {
            "trace_id": trace_id, "node_id": node_id, "final_state": None,
            "action": action, "reason": reason,
            "pre_hash": pre_hash, "post_hash": pre_hash, "zone_state": None,
        }

    elif next_state == "DIVERGED":
        action = "LOGGED"; reason = f"diverged_quarantined: {cause}"
        print(f"[DIVERGED]  node={node_id}  logged but NOT applied  trace={trace_id}")
        result = {
            "trace_id": trace_id, "node_id": node_id, "final_state": None,
            "action": action, "reason": reason,
            "pre_hash": pre_hash, "post_hash": pre_hash, "zone_state": None,
        }

    else:
        action = "REJECTED"; reason = f"unknown_state: {next_state}"
        print(f"[REJECTED]  node={node_id}  reason=unknown_state  trace={trace_id}")
        result = {
            "trace_id": trace_id, "node_id": node_id, "final_state": None,
            "action": action, "reason": reason,
            "pre_hash": pre_hash, "post_hash": pre_hash, "zone_state": None,
        }

    _execution_log.append(result)
    return result
