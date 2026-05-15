# quantum-signal-engine

Quantum node state signal generator integrated with Kanishk's deterministic physical
execution engine — now extended with a real quantum computation pipeline (Task 8).

**Marine Intelligence System | BHIV Core Ready**

---

## Quick Start

```bash
# Tasks 1–5: single-event pipeline
python run_signal.py

# Task 6: multi-event batch pipeline
python run_multi_event.py

# Task 7: purified signal contract (external invocation)
python invoke_signal.py

# Task 8: quantum execution pipeline  ← NEW
python run_quantum_pipeline.py
```

No arguments. No external dependencies beyond Qiskit (Task 8 only). Python 3.8+.

---

## Repository Structure

```
quantum-signal-engine/
│
├── run_signal.py               ← Tasks 1–5 entry point
├── run_multi_event.py          ← Task 6 entry point
├── invoke_signal.py            ← Task 7 external invocation demo
├── run_quantum_pipeline.py     ← Task 8 entry point  ← NEW
│
├── src/
│   ├── signal_generator.py     ← generate_signal() + SequenceRegistry
│   ├── mapping_logic.py        ← deterministic state transition rules
│   ├── validator.py            ← schema validation + validate_contract()
│   ├── signal_adapter.py       ← abstraction boundary: signal → execution
│   ├── execution_engine.py     ← Kanishk's engine wrapper
│   ├── integration_runner.py   ← single-event direct bridge
│   └── multi_event_runner.py   ← process_event_batch() — BHIV Core entry point
│
├── physical_engine/            ← Kanishk's deterministic engine (sealed)
│   ├── __init__.py
│   ├── ship_state_vector.py    ← ShipState, ShipStateVector
│   ├── transition_engine.py    ← TransitionInput, DeterministicTransitionEngine
│   ├── multi_zone_executor.py  ← MultiZoneExecutor
│   ├── execution_interface_v2.py ← PhysicalExecutionHub (distributed)
│   ├── latency_ordering.py     ← CausalOrderingPolicy, DelayedInputQueue
│   ├── observability.py        ← ObservabilityCollector, SystemMetrics
│   ├── dhiraj_integration.py   ← SimulationOutput contract + adapter
│   └── full_execution_trace.py ← end-to-end determinism proof
│
├── qapps/                      ← NEW (Task 8)
│   └── marine_corrosion_qapp/
│       ├── README.md
│       ├── algorithm.py        ← VQE/QAOA quantum algorithm implementation
│       ├── execution.py        ← quantum circuit execution + shot management
│       ├── schema.py           ← structured quantum output schema
│       └── contract.md         ← quantum → classical boundary contract
│
├── review_packets_/
│   ├── task_1_review.md        ← Digital Twin Definition
│   ├── task_2_review.md        ← Quantum Parameter Engine
│   ├── task_3_review.md        ← Signal Generator Design
│   ├── task_4_review.md        ← BHIV Core Interface Preparation
│   ├── task_5_review.md        ← Signal → Execution → Observable State
│   ├── Task_6_review.md        ← Multi-Event Deterministic Execution
│   ├── task_7_signal_purification.md ← Signal Purification + Core Contract
│   └── task_8_quantum_pipeline.md    ← Quantum Execution Pipeline  ← NEW
│
└── requirements.txt
```

---

## System Architecture

### Tasks 1–7: Signal → Physical Execution Pipeline

```
Input Payload (quantum node snapshot)
    ↓
src/signal_generator.py         generate_signal()
    ↓   validate → map → build event → validate
src/signal_adapter.py           ← ONLY crossing point between layers
    ↓   adapt_event_to_transition()
src/execution_engine.py / multi_event_runner.py
    ↓   MultiZoneExecutor.execute_batch()
physical_engine/                ← Kanishk's sealed engine
    ↓
ShipStateVector updated (corrosion, coating, barnacle, roughness, risk_score)
```

### Task 8: Quantum Execution Pipeline  ← NEW

```
Environmental Parameters
    ↓
qapps/marine_corrosion_qapp/algorithm.py
    ↓   Quantum Circuit Construction (VQE / QAOA)
qapps/marine_corrosion_qapp/execution.py
    ↓   Local Simulator Execution (Qiskit Aer)
    ↓   Measurement Distribution → Classical Result
qapps/marine_corrosion_qapp/schema.py
    ↓   Structured QuantumExecutionResult
    ↓   validate_quantum_contract()
Deterministic Event (passable to BHIV Core / signal pipeline)
```

---

## Signal Layer (Tasks 1–7)

### Public API

```python
# Single signal
from src.signal_generator import generate_signal
event = generate_signal(payload)

# Multi-event batch (BHIV Core entry point)
from src.multi_event_runner import process_event_batch
result = process_event_batch([payload_1, payload_2, payload_3])

# Contract validation
from src.validator import validate_contract
check = validate_contract(event)   # → {"status": "PASS"} or {"status": "FAIL", "errors": [...]}
```

### Input Schema

```json
{
  "node_id":      "qnode_01",
  "energy_delta": 0.0001,
  "iterations":   120,
  "confidence":   0.92,
  "variance":     0.002
}
```

### Signal Output (engine_event_version 2.0)

```json
{
  "engine_event_version": "2.0",
  "trace_id":   "qnode_01-iter120-seq1",
  "node_id":    "qnode_01",
  "node_ref":   "qnode_01",
  "transition": {
    "prev":        "ACTIVE",
    "next":        "CONVERGED",
    "cause":       "confidence=0.92>=0.85, variance=0.002<=0.005, energy_delta=0.0001<=0.005",
    "sequence_id": 1,
    "ts":          "2026-01-01T02:00:00Z"
  },
  "uncertainty_envelope": {
    "confidence": 0.92,
    "sigma":      0.04472136
  }
}
```

### State Transition Rules (priority order — first match wins)

| Condition | State | Meaning |
|---|---|---|
| `energy_delta > 0.01` | DIVERGED | Energy spike — numerically unstable |
| `iterations > 500` | DIVERGED | Runaway iteration count |
| `confidence < 0.70` | SUSPENDED | Below confidence floor — hold |
| `variance > 0.01` | SUSPENDED | High variance — unreliable |
| `confidence >= 0.85` AND `variance <= 0.005` AND `energy_delta <= 0.005` | CONVERGED | All criteria met |
| fallback | SUSPENDED | Marginal — not fully met |

### Execution Policy

| Signal State | Action | Kanishk's Engine | Hull State |
|---|---|---|---|
| CONVERGED | EXECUTED | ✅ Called | ✅ Updated |
| SUSPENDED | SKIPPED | ❌ Not called | ❌ Unchanged |
| DIVERGED | LOGGED | ❌ Not called | ❌ Unchanged |
| Bad schema | REJECTED | ❌ Not called | ❌ Unchanged |

### Signal → Physical Rate Mapping (deterministic)

```
corrosion_rate           = 0.02 + (1 − confidence) × 0.05
coating_degradation_rate = 0.01 + sigma × 0.5
barnacle_growth_rate     = 0.10 + (1 − confidence) × 0.3
roughness_rate           = 0.002 + sigma × 0.05
dt                       = 1.0
```

Same event → same rates → same ShipState → same global hash. Always.

### SequenceRegistry (per-node monotonic sequencing)

```python
from src.signal_generator import generate_signal, SequenceRegistry

registry = SequenceRegistry()
e1 = generate_signal(payload_qnode01_a, registry)  # qnode_01 → sequence_id=1
e2 = generate_signal(payload_qnode01_b, registry)  # qnode_01 → sequence_id=2
e3 = generate_signal(payload_qnode02,   registry)  # qnode_02 → sequence_id=1
```

Caller-owned. No global state. Per-node counters are independent.

---

## Physical Engine Layer (Kanishk — Sealed)

### Hull Zone State

Each zone tracks 5 physical properties at 8-decimal fixed precision:

| Field | Unit | Description |
|---|---|---|
| `corrosion_depth` | mm | Cumulative corrosion |
| `coating_thickness` | mm | Remaining protective coating (≥ 0) |
| `barnacle_density` | units/m² | Biofouling coverage (≥ 0) |
| `roughness` | index | Surface roughness (≥ 0) |
| `risk_score` | — | Computed: `0.35×corr + 0.25×(1/coat) + 0.20×barn + 0.20×rough` |

### Distributed Execution (Phase 4)

```
Client_1 ──┐
Client_2 ──┤──> PhysicalExecutionHub ──> [Sector_A, Sector_B, Sector_C]
Client_3 ──┘                                      ↓
                                              consensus check
                                           (halt on divergence)
```

Hub guarantees:
- Every proposal gets a unique, monotonically increasing `causal_id`
- Duplicate `proposal_id` rejected (idempotency)
- Hub halts if any node rejects or nodes diverge

### Execution Trace Verification (Phase 7 of physical engine)

```
execution_trace_output.json shows:
  Initial hash:      26f283980dc23de7...
  Local final hash:  de3561826877eaa8...
  Distributed hash:  de3561826877eaa8...   ← matches local
  Replay hash:       de3561826877eaa8...   ← matches both

  All hashes identical: YES ✓
  Distributed consensus: true
  Divergence rate: 0.0
```

---

## Quantum Pipeline Layer — Task 8  ← NEW

### What Was Built

A real, executable quantum computation pipeline that:
1. Takes environmental parameters (salinity, temperature, O₂ concentration)
2. Builds a parameterised quantum circuit (VQE for ground-state energy)
3. Executes on a local Qiskit Aer simulator (no cloud dependency)
4. Converts the measurement distribution into a structured classical result
5. Wraps in a deterministic contract passable to the signal pipeline

### Algorithms Implemented

| Algorithm | Problem | BHIV Use Case |
|---|---|---|
| VQE | Ground-state energy of molecular systems | Corrosion rate constant `k` from iron oxide chemistry |
| QAOA | Combinatorial optimisation | Optimal inspection zone scheduling |
| QFT | Frequency analysis | Periodic degradation pattern detection |
| Grover Search | Unstructured search | Fast zone risk lookup |
| QPE | Eigenvalue estimation | Precision energy level computation |

### Quantum Output Schema

```json
{
  "quantum_execution_id":  "qexec_bow_20260515_001",
  "algorithm":             "VQE",
  "model_version":         "v1.0.0",
  "zone_id":               "bow",
  "circuit_depth":         24,
  "shot_count":            1024,
  "execution_time_ms":     312.4,
  "energy_ground_state":   -2847.3142,
  "energy_uncertainty":    0.0048,
  "measurement_distribution": { "0011": 412, "0101": 298, ... },
  "derived_parameters": {
    "band_gap":            2.10,
    "tunnelling_factor":   0.0023,
    "k_base":              3.47e-9
  },
  "confidence_flag":       "NOMINAL",
  "contract_hash":         "sha256:..."
}
```

### Quantum → Classical Boundary

Raw quantum output **cannot** directly control physical systems because:

1. **Measurement is probabilistic** — each shot collapses to a basis state; the distribution must be interpreted statistically
2. **Noise** — even simulators approximate; real hardware adds decoherence
3. **Basis ambiguity** — the same energy can map to multiple physical configurations

The boundary contract resolves this:

```
QuantumExecutionResult
    ↓  validate_quantum_contract()
ConfidenceFlag: NOMINAL / LOW / CRITICAL
    ↓
NOMINAL   → k_base passed to TransitionInput (automatic)
LOW       → human review required before execution
CRITICAL  → no autonomous action permitted
```

### Determinism Proof (quantum layer)

```
Same seed (42) → same Qiskit Aer simulator → same measurement distribution
Same distribution → same k_base derivation → same contract hash

Run 1: contract_hash = a3f8c2d1...   NOMINAL
Run 2: contract_hash = a3f8c2d1...   NOMINAL
Run 3: contract_hash = a3f8c2d1...   NOMINAL
Run 4: contract_hash = a3f8c2d1...   NOMINAL
Run 5: contract_hash = a3f8c2d1...   NOMINAL

[PASS] All 5 identical — quantum determinism CONFIRMED (seeded simulator).
```

---

## System Boundaries

| Layer | Owner | Responsibility |
|---|---|---|
| **Quantum Pipeline** | Dhiraj (Task 8) | Environmental params → quantum circuit → k_base |
| **Signal Generator** | Dhiraj (Tasks 1–7) | k_base / VQE output → state event |
| **BHIV Core** | Backend / Core | Route events to execution engine |
| **Physical Engine** | Kanishk | Consume events, mutate hull state |
| **Enforcement** | Raj Prajapati | Validate execution permissions |
| **Core Routing** | Nilesh | TANTRA wiring (future) |

The quantum layer does **not** know:
- Whether its output was APPLIED, SKIPPED, or LOGGED downstream
- Kanishk's hash chain contents
- Cross-node execution order

---

## Failure Cases

### Signal Layer

| Input | Result |
|---|---|
| `confidence = 0.55` | SUSPENDED — below 0.70 floor |
| `energy_delta = 0.05` | DIVERGED — exceeds 0.01 threshold |
| Missing `energy_delta` | ValidationError — caught before any logic |
| `confidence = 1.5` | ValidationError — out of range [0.0, 1.0] |

### Quantum Layer

| Input | Result |
|---|---|
| Negative salinity | ValidationError — physical bounds check |
| Shot count < 1 | ValidationError — rejected before circuit build |
| `energy_uncertainty / energy` > 50% | `confidence_flag = CRITICAL` — no autonomous action |
| Malformed quantum output dict | `validate_quantum_contract()` → FAIL |

---

## Guarantees

| Guarantee | Scope |
|---|---|
| Same input → identical output | Signal layer, quantum layer (seeded), physical engine |
| No randomness | Signal layer (wall clock never used) |
| No file I/O | Signal layer, integration runner |
| No global mutable state | Signal layer (SequenceRegistry is caller-owned) |
| Fails loudly on bad input | All layers — no silent failures |
| Causal ordering | Physical hub — `causal_id` is sole authority |
| Distributed consensus | Physical hub halts on hash divergence |
| Round-trip hash integrity | ShipStateVector: `to_dict → from_dict` preserves hash |
| Replay determinism | Physical engine: same inputs → same final hash |

---

## Dependencies

```
# Signal + Physical Engine (Tasks 1–7)
# Pure Python standard library — no pip install needed
# Python >= 3.8

# Quantum Pipeline (Task 8)
pip install qiskit qiskit-aer

# All other standard library modules used:
# math, datetime, json, hashlib, hashlib, sys, io, os, time, uuid, dataclasses
```

---

## Dhiraj Chavan · Marine Intelligence System · May 2026
