# quantum-signal-engine

Quantum node state signal generator integrated with Kanishk's physical execution engine.
Proves: 1 signal → 1 execution → 1 observable state change.

## Run

```bash
python run_signal.py
```

No arguments. No dependencies. Python 3.8+.

## Structure

```
quantum-signal-engine/
├── src/
│   ├── signal_generator.py    ← Dhiraj: quantum event generator (Task 4, unchanged)
│   ├── mapping_logic.py       ← Dhiraj: deterministic state transition rules
│   ├── validator.py           ← Dhiraj: schema validation
│   ├── execution_engine.py    ← NEW: wraps Kanishk's MultiZoneExecutor
│   └── integration_runner.py  ← NEW: direct invocation bridge
├── physical_engine/           ← Kanishk's real engine (integrated)
│   ├── ship_state_vector.py   ← ShipState, ShipStateVector
│   ├── transition_engine.py   ← TransitionInput, DeterministicTransitionEngine
│   └── multi_zone_executor.py ← MultiZoneExecutor (4-zone hull model)
├── run_signal.py              ← MAIN ENTRY POINT
├── requirements.txt
└── review_packets_/
    └── task_5_review.md
```

## Integration Flow

```
input_payload
    → generate_state_event()          [Dhiraj — signal layer]
    → _signal_to_transition_rates()   [deterministic mapping]
    → MultiZoneExecutor.execute_batch() [Kanishk — real engine]
    → ShipState updated (corrosion, coating, risk_score)
    → pre_hash ≠ post_hash            [observable proof]
```

## Execution Policy

| Signal | Action | Kanishk's Engine | State |
|---|---|---|---|
| CONVERGED | EXECUTED | ✅ Called | ✅ Updated |
| SUSPENDED | SKIPPED | ❌ Not called | ❌ Unchanged |
| DIVERGED | LOGGED | ❌ Not called | ❌ Unchanged |
| Bad schema | REJECTED | ❌ Not called | ❌ Unchanged |

*Dhiraj Chavan · Marine Intelligence System · April 2026*
