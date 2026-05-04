* *# quantum-signal-engine

Quantum node state signal generator integrated with Kanishk's physical execution engine.
Multi-event deterministic execution — BHIV Core ready.

---

## Run

### Single-event (Tasks 1–5)
```bash
python run_signal.py
```

### Multi-event (Task 6)
```bash
python run_multi_event.py
```

No arguments. No dependencies. Python 3.8+.

---

## Structure

```
quantum-signal-engine/
├── src/
│   ├── signal_generator.py     ← entry logic + SequenceRegistry (updated Task 6)
│   ├── mapping_logic.py        ← deterministic state transition rules
│   ├── validator.py            ← schema validation + failure checks
│   ├── signal_adapter.py       ← NEW: abstraction boundary, signal→execution
│   ├── execution_engine.py     ← Kanishk's engine wrapper (uses signal_adapter)
│   ├── integration_runner.py   ← single-event direct bridge
│   └── multi_event_runner.py   ← NEW: process_event_batch() BHIV Core entry point
├── physical_engine/            ← Kanishk's real engine (sealed, unchanged)
│   ├── __init__.py
│   ├── ship_state_vector.py
│   ├── transition_engine.py
│   └── multi_zone_executor.py
├── run_signal.py               ← single-event entry point (Tasks 1–5)
├── run_multi_event.py          ← multi-event entry point (Task 6)
├── requirements.txt
├── README.md
└── review_packets_/
    ├── task_1_review.md  ...  task_5_review.md
    └── task_6_review.md
```

---

## Abstraction Boundary (Task 6)

```
signal_generator.py
    ↓  generate_state_event(payload, seq_registry)
signal_adapter.py           ← ONLY crossing point between signal and execution
    ↓  adapt_event_to_transition(event, zone_id)
execution_engine.py / multi_event_runner.py
    ↓  MultiZoneExecutor.execute_batch()
physical_engine/            ← Kanishk's engine (sealed)
```

---

## BHIV Core API (Task 6)

```python
from src.multi_event_runner import process_event_batch

result = process_event_batch([
    {"node_id": "qnode_01", "energy_delta": 0.0001, "iterations": 120, "confidence": 0.92, "variance": 0.002},
    {"node_id": "qnode_01", "energy_delta": 0.0002, "iterations": 200, "confidence": 0.91, "variance": 0.003},
    {"node_id": "qnode_02", "energy_delta": 0.0005, "iterations": 80,  "confidence": 0.88, "variance": 0.004},
])
# {
#   "trace_id":      "5d334ba4...",
#   "final_hash":    "3906c356...",
#   "nodes_updated": ["qnode_01", "qnode_01", "qnode_02"],
#   "execution_log": [...],
#   "final_state":   {...}
# }
```

## SequenceRegistry (per-node monotonic seq)

```python
from src.signal_generator import generate_state_event, SequenceRegistry

registry = SequenceRegistry()
e1 = generate_state_event(payload_1, registry)  # qnode_01 → seq=1
e2 = generate_state_event(payload_2, registry)  # qnode_01 → seq=2
e3 = generate_state_event(payload_3, registry)  # qnode_02 → seq=1
```

---

## State Transitions

| Condition | State |
|---|---|
| `energy_delta > 0.01` | DIVERGED |
| `iterations > 500` | DIVERGED |
| `confidence < 0.70` | SUSPENDED |
| `variance > 0.01` | SUSPENDED |
| `confidence >= 0.85` AND `variance <= 0.005` AND `energy_delta <= 0.005` | CONVERGED |
| fallback | SUSPENDED |

## Execution Policy

| Signal | Action | Kanishk's Engine | State |
|---|---|---|---|
| CONVERGED | EXECUTED | Called | Updated |
| SUSPENDED | SKIPPED | Not called | Unchanged |
| DIVERGED | LOGGED | Not called | Unchanged |
| Bad schema | REJECTED | Not called | Unchanged |

---

## Guarantees

- Same input → identical output, always (no randomness, no wall clock)
- `SequenceRegistry` — per-node monotonic seq, caller-owned, no global state
- Events sorted by (node_id, seq) before execution — order-insensitive
- `signal_adapter.py` — clean boundary, signal layer never touches execution layer
- No file I/O, no global state, no external dependencies
- Fails loudly on bad input — no silent failures

---

*Dhiraj Chavan · Marine Intelligence System · May 2026*
