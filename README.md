# quantum-signal-engine

Pure, deterministic quantum node signal generator.  
Core-ready contract for TANTRA / BHIV Core integration.

**Task 7 — Signal Purification + Core-Ready Contract**  
Author: Dhiraj Chavan | Marine Intelligence System

---

## Quick Start

```bash
# External invocation (how BHIV Core uses this)
python invoke_signal.py

# Full test harness (all phases)
python run_signal.py
```

No arguments. No dependencies. Python 3.8+.

---

## Architecture

```
quantum-signal-engine/
├── src/
│   ├── signal_generator.py   ← generate_signal() + SequenceRegistry
│   ├── mapping_logic.py      ← pure deterministic transition table
│   └── validator.py          ← validate_input() + validate_contract()
├── physical_engine/          ← Kanishk's engine (sealed, not called by signal layer)
│   ├── __init__.py
│   ├── ship_state_vector.py
│   ├── transition_engine.py
│   └── multi_zone_executor.py
├── review_packets_/
│   └── task_7_signal_purification.md
├── invoke_signal.py          ← external invocation demo
├── run_signal.py             ← full test harness
├── requirements.txt
└── README.md
```

---

## Public API

### `generate_signal(input_payload, seq_registry=None) -> dict`

```python
from src.signal_generator import generate_signal, SequenceRegistry

# Single call
event = generate_signal({
    "node_id":      "qnode_01",
    "energy_delta": 0.0001,
    "iterations":   120,
    "confidence":   0.92,
    "variance":     0.002,
})

# Multi-call with per-node monotonic sequence
registry = SequenceRegistry()
e1 = generate_signal(payload_1, registry)  # qnode_01 → sequence_id=1
e2 = generate_signal(payload_2, registry)  # qnode_01 → sequence_id=2
e3 = generate_signal(payload_3, registry)  # qnode_02 → sequence_id=1
```

### `validate_contract(event) -> dict`

```python
from src.validator import validate_contract

result = validate_contract(event)
# {"status": "PASS"} or {"status": "FAIL", "errors": [...]}
```

---

## Output Contract (Core-ready)

```json
{
  "engine_event_version": "2.0",
  "trace_id": "qnode_01-iter120-seq1",
  "node_id": "qnode_01",
  "node_ref": "qnode_01",
  "transition": {
    "prev": "ACTIVE",
    "next": "CONVERGED",
    "cause": "confidence=0.92>=0.85, variance=0.002<=0.005, energy_delta=0.0001<=0.005",
    "sequence_id": 1,
    "ts": "2026-01-01T02:00:00Z"
  },
  "uncertainty_envelope": {
    "confidence": 0.92,
    "sigma": 0.04472136
  }
}
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

---

## System Boundary

| Layer | Owner | Responsibility |
|---|---|---|
| **Signal Generator** | Dhiraj | validate → determine state → emit event |
| **BHIV Core** | Backend | receive event, route to execution |
| **Execution Engine** | Kanishk | consume events, mutate ship state |
| **Enforcement Engine** | Raj Prajapati | validate execution permissions |

**This module does NOT:**
- Call Kanishk's execution engine
- Make execution decisions (APPLIED / SKIPPED / LOGGED)
- Control event ordering or batching
- Produce a parallel hash chain

---

## Guarantees

- Same input → identical output, always (no randomness, no wall clock)
- `trace_id` is deterministic — derived from `node_id + iterations + sequence_id`
- `SequenceRegistry` — per-node monotonic, caller-owned, no global state
- `validate_contract()` — externally callable, never raises
- No file I/O, no global mutable state, no external dependencies
- Fails loudly on bad input — no silent failures

---

*Dhiraj Chavan · Marine Intelligence System · May 2026*
