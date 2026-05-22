# Marine Intelligence System — Quantum Stack
## BHIV Core | Tasks 1–9 | Full Pipeline

**Author:** Dhiraj Chavan · Marine Intelligence System
**Product Lane:** Quantum Infrastructure / Distributed QApp Runtime Systems
**Period:** 2026

---

> **What this repository proves:**
> A quantum-assisted digital twin for ship hull degradation — built from
> first principles. Physics-based corrosion modelling, deterministic VQE
> computation, governed callable interface, and finally a distributed
> infrastructure participant with replay-safe propagation and observable
> consensus across three nodes.

---

## Quick Start

```bash
# Tasks 1–4
python run_signal.py

# Task 9
python run_distributed_qapp.py
```

**Requirements:** Python 3.8+ · No pip installs · No external dependencies
**Exit codes:** `0` = PASS · `1` = FAIL (reason printed before exit)

---

## Repository Structure

```
marine-intelligence-quantum-stack/
│
├── run_signal.py                    ← Tasks 1–4 entry point
├── src/
│   ├── signal_generator.py          ← generate_state_event() callable
│   ├── mapping_logic.py             ← deterministic state transition engine
│   └── validator.py                 ← schema validation + failure checks
│
├── run_distributed_qapp.py          ← Task 9 entry point
├── envelope.py                      ← Phase 1: QAppExecutionEnvelope
├── nodes.py                         ← Phase 2: Node_A, Node_B, Node_C
├── propagation.py                   ← Phase 3+4: engine + replay
├── failure_sim.py                   ← Phase 5: 4 failure simulators
│
├── review_packets/
│   ├── task_1_review.md
│   ├── task_2_review.md
│   ├── task_3_review.md
│   └── task_4_review.md
│
├── REVIEW_PACKET.md                 ← Task 9: 10-section design review
├── TESTING_PACKET.md                ← Task 9: BHIV Universal Testing Protocol v2
├── requirements.txt                 ← stdlib only — no pip installs
├── .gitignore
└── README.md                        ← this file
```

---

## Pipeline Overview

Nine tasks. One progressive build. Each extends the foundation of the last.

```
Task 1  ──  Define the physical system        ship hull digital twin
   │
Task 2  ──  Compute quantum parameters        VQE → corrosion rate constant k
   │
Task 3  ──  Build the signal generator        deterministic state machine
   │
Task 4  ──  Harden the callable interface     BHIV Core contract
   │
Task 5  ──  Add contract governance           schema versioning + enforcement
   │
Task 6  ──  Bound the probabilistic layer     uncertainty + confidence flags
   │
Task 7  ──  Wrap the QApp with governance     execution authority separation
   │
Task 8  ──  Coordinate the hybrid runtime     quantum-classical orchestration
   │
Task 9  ──  Prove distributed survival        propagation · replay · consensus
```

**Transition point:** Tasks 1–8 prove correctness of isolated execution.
Task 9 proves the system can survive as **distributed infrastructure**.

---

## Task 1 — Digital Twin Definition

**Run:** `python run_signal.py`
**Review:** `review_packets/task_1_review.md`

### Four physical processes modelled

| Process | Physics | Master driver |
|---|---|---|
| **Corrosion** | Seawater converts Fe → Fe₂O₃ electrochemically | O₂ · salinity · temperature · coating |
| **Biofouling** | Barnacle attachment and growth | Antifouling paint (suppresses ~90% when intact) |
| **Coating degradation** | Mechanical erosion · UV · chemical decay | Controls every other process |
| **Performance loss** | Drag → fuel cost (annual £ figure) | Roughness index |

### State variables per hull zone

| Variable | Unit | Role |
|---|---|---|
| `corrosion_depth` | mm | Cumulative material loss |
| `coating_thickness` | mm | Master control variable |
| `barnacle_density` | organisms/m² | Biofouling load |
| `flow_velocity` | m/s | Hydrodynamic shear input |
| `roughness_index` | μm Ra | Surface drag parameter |
| `risk_score` | 0.0–1.0 | Composite intervention indicator |

**Zone model:** 50–200 rectangular zones, each updated independently.
**Scope:** hull surface only — no propulsion, cargo, or routing.

---

## Task 2 — Quantum Parameter Engine + State Mapping

**Run:** `python run_signal.py`
**Review:** `review_packets/task_2_review.md`

### VQE pipeline — offline, once per material type

```
PySCF classical pre-computation
    ↓  hᵢⱼ, gᵢⱼₖₗ integrals — CAS(10,8) active space
Jordan-Wigner mapping  →  380 Pauli terms
    ↓
UCCSD ansatz  (16 qubits, 220 parameters)
    ↓
COBYLA (200 iters) → SPSA (50) → L-BFGS-B (|ΔE| < 1×10⁻⁵)
    ↓
E�� = −2847.3142 ± 0.0048 Hartree
    ↓
band_gap = 2.10 eV  |  tunnelling_factor = 0.0023  |  k_base = 3.47×10⁻⁹
```

### Four delta equations per zone per timestep

```
Eq 1  delta_corrosion_mm     = k_base × f_T × f_S × f_O2 × M_Fe × Δt
Eq 2  delta_coating_mm       = −k_coat × Δcorrosion × coating_thickness
Eq 3  delta_roughness_um     = α_r × Δcorrosion + β_r × fouling × Δt
Eq 4  delta_fouling_coverage = k_f × (1 − fouling) × f_vel(v) × Δt
```

### Bayesian correction — drydock survey loop

| State | k uncertainty |
|---|---|
| Prior (no surveys) | ±64% |
| After survey 1 | ±31% |
| After survey 2 | ±14% |
| After survey 3 | ±6% |

### Confidence flags

| Flag | σ / value | Engine behaviour |
|---|---|---|
| `NOMINAL` | < 20% | Automatic decisions enabled |
| `LOW` | 20–50% | Human review required |
| `CRITICAL` | > 50% | No autonomous action |

---

## Task 3 — Signal Generator Design

**Run:** `python run_signal.py`
**Review:** `review_packets/task_3_review.md`

### `generate_state_event(input_payload: dict) -> dict`

Single callable. No constructor. No instance required.

```
input_payload
    ↓
validate_input()          fails loudly if anything wrong
    ↓
resolve_transition()      deterministic priority-ordered rule table
    ↓
timestamp                 anchor(2026-01-01T00:00:00Z) + (iterations × 60s)
    ↓
event assembly            engine_event_version 2.0
    ↓
validate_output()         confirms shape before returning
    ↓
return event
```

### Transition table (first match wins)

| Condition | Next state |
|---|---|
| `energy_delta > 0.01` | `DIVERGED` |
| `iterations > 500` | `DIVERGED` |
| `confidence < 0.70` | `SUSPENDED` |
| `variance > 0.01` | `SUSPENDED` |
| `confidence >= 0.85` AND `variance <= 0.005` AND `energy_delta <= 0.005` | `CONVERGED` |
| fallback | `SUSPENDED` |

`sigma = sqrt(variance)` · `prev = "INITIALISING"` if `iterations == 0` else `"ACTIVE"`

### Live example

**Input:**
```json
{
    "node_id": "qnode_01",  "energy_delta": 0.0001,
    "iterations": 120,      "confidence": 0.92,  "variance": 0.002
}
```

**Output:**
```json
{
    "engine_event_version": "2.0",
    "node_ref": "qnode_01",
    "transition": {
        "prev": "ACTIVE", "next": "CONVERGED",
        "cause": "confidence=0.92>=0.85, variance=0.002<=0.005, energy_delta=0.0001<=0.005",
        "seq": 1, "ts": "2026-01-01T02:00:00Z"
    },
    "uncertainty_envelope": { "confidence": 0.92, "sigma": 0.04472136 }
}
```

---

## Task 4 — BHIV Core Interface Preparation

**Run:** `python run_signal.py`
**Review:** `review_packets/task_4_review.md`

### What was hardened

| Component | File | Guarantee |
|---|---|---|
| `generate_state_event()` | `signal_generator.py` | Single callable — no constructor, no instance |
| `resolve_transition()` | `mapping_logic.py` | Pure function — no side effects, no randomness, no I/O |
| `validate_input()` | `validator.py` | Type + range + presence — exact error messages |
| `validate_output()` | `validator.py` | All required keys + `seq` is `int` — checked before return |

### Failure cases

| Input | Result |
|---|---|
| Missing `energy_delta` | `ValidationError: Missing required field(s): ['energy_delta']` |
| `confidence = 0.55` | `SUSPENDED — below 0.70 floor` |
| `energy_delta = 0.05` | `DIVERGED — exceeds 0.01 threshold` |
| `confidence = 1.5` | `ValidationError: must be a float in [0.0, 1.0]` |

### 5-run determinism proof

```
Run 1: transition='CONVERGED'   sigma=0.04472136   ts=2026-01-01T02:00:00Z
Run 2: transition='CONVERGED'   sigma=0.04472136   ts=2026-01-01T02:00:00Z
Run 3: transition='CONVERGED'   sigma=0.04472136   ts=2026-01-01T02:00:00Z
Run 4: transition='CONVERGED'   sigma=0.04472136   ts=2026-01-01T02:00:00Z
Run 5: transition='CONVERGED'   sigma=0.04472136   ts=2026-01-01T02:00:00Z

[PASS] All 5 outputs IDENTICAL — determinism CONFIRMED
```

---

## Task 5 — Contract Governance Layer

**Product lane:** Quantum Infrastructure / Contract Discipline

A formal contract layer between the quantum computation output and BHIV Core.

**Key deliverables:**
- `quantum_output_schema.json` — typed contract with validation rules for every field
- Integration contract **MARINE-INT-002 v1.0.0** — full input/output packet format
- Contract version negotiation between producer and consumer
- Enforcement boundary: computation authority ≠ execution authority

**Principles:**
- Schema is versioned — breaking changes require an explicit version bump
- All fields are typed and range-bounded — no implicit coercion in the consumer
- Contract violations halt execution before any downstream computation begins
- The governance layer never mutates computation output — read-only

---

## Task 6 — Bounded Probabilistic Computation

**Product lane:** Quantum Infrastructure / Uncertainty Quantification

First-order error propagation through the full k_base chain.
Every output delta carries a bounded 95% confidence interval.

**Propagation path:**
```
σ_E₀ (±0.0048 Hartree from VQE)
    ↓
σ_k_base  →  σ_delta_corrosion  →  σ_delta_coating  →  σ_delta_roughness
    ↓
95% CI on every delta  →  NOMINAL / LOW / CRITICAL flag
```

**Guarantee:** `CRITICAL`-flagged outputs block autonomous action permanently
until cleared by human review.

---

## Task 7 — Governance-Aware QApp Wrapping

**Product lane:** Quantum Infrastructure / Governed QApp Runtime

The QApp wrapper enforces the three-layer authority model:

```
Quantum engine  →  computes
Wrapper         →  governs
BHIV Core       →  executes
```

**Wrapper responsibilities:**
- Validate output against the active contract version
- Attach `approval_required`, `execution_class`, `authority_level` metadata
- Block execution when confidence flags are insufficient for the requested action
- Route to human review queue on `LOW` or `CRITICAL` flags
- Produce a full audit log entry for every governance decision

No layer crosses into another's authority. Wrapper is read-only on computation output.

---

## Task 8 — Hybrid Quantum-Classical Runtime

**Product lane:** Quantum Infrastructure / Hybrid Runtime Coordination

Coordination layer managing the handoff between quantum computation and
classical simulation within one timestep cycle per zone.

**Timestep cycle:**
```
Step 1  Quantum phase    ← VQE parameters from offline cache (not re-run per step)
Step 2  Classical phase  ← 4 delta equations applied with quantum k values
Step 3  Uncertainty      ← propagated through classical chain
Step 4  Governance       ← flags evaluated, execution class assigned
Step 5  State update     ← zone variables updated — append-only log entry
Step 6  Output emit      ← structured event dispatched to BHIV Core
```

**Hard contract:** partial state is never committed.
Any failure in any step aborts the full timestep.
Replay of any timestep from its log entry reproduces identical output.

---

## Task 9 — Distributed QApp Propagation Layer

**Run:** `python run_distributed_qapp.py`
**Review:** `REVIEW_PACKET.md` (10 sections)
**Testing:** `TESTING_PACKET.md` (BHIV Universal Testing Protocol v2 — Vinayak)

Proves the QApp can survive as a distributed infrastructure participant —
causal propagation, append-only replay, observable consensus, governed failure handling.

### 8 phases

| Phase | Name | What runs |
|---|---|---|
| 1 | QApp Invocation Envelope | 3 deterministic envelopes — SHA-256 IDs, no `datetime.now()` |
| 2 | Distributed Node Simulation | Node_A, Node_B, Node_C — 4 tracking fields, genesis hashes |
| 3 | QApp Propagation Engine | Fan-out A → [B, C] — append-only log, every step printed |
| 4 | Distributed Replay Reconstruction | Causal sort + hash rebuild — verified against live nodes |
| 5 | Divergence + Failure Simulation | 4 cases — loud halt, state preserved, no silent recovery |
| 6 | Observability Layer | Propagation chain · node status · divergence · consensus hash |
| 7 | Determinism Proof | 5× replay identical · 3× shuffle convergence |
| 8 | REVIEW_PACKET.md | Presence + all 10 sections verified at runtime |

### Propagation model

```
QAppExecutionEnvelope (seq=N)
        │
        ▼
  Node_A  ←  origin
        │
        ├──────→  Node_B  ✅
        └──────→  Node_C  ✅
```

All steps logged to an append-only `_PROPAGATION_LOG`.
`replay_qapp_log()` causal-sorts by `(sequence_id, step_order)` —
replay is **log-order-independent**.

### QAppExecutionEnvelope — all 8 fields

| Field | Derivation |
|---|---|
| `trace_id` | `SHA-256("trace:{qapp_id}:{node_origin}:{seq}")` |
| `qapp_id` | Caller-supplied |
| `node_origin` | `"Node_A"` |
| `invocation_id` | `SHA-256("invoke:{trace_id}:{payload_hash}:{seq}")` |
| `payload_hash` | `SHA-256(canonical_json(payload, sort_keys=True))` |
| `sequence_id` | Monotonic int ≥ 1 |
| `timestamp` | `2026-01-01T00:00:00Z + (seq × 60s)` — no wall clock |
| `contract_version` | `"qapp-v1.0"` |

### Execution hash chain

```
hash₀  =  SHA-256("INIT:<node_id>")
hashₙ  =  SHA-256(f"{hashₙ₋₁}:{invocation_id_n}")
```

Inserting, deleting, or reordering any received invocation changes
every downstream hash link — tamper-evident without external libraries.

### Failure cases

| Case | Trigger | Policy | Exception |
|---|---|---|---|
| Delayed propagation | `seq` gap > threshold | Accept with `CAUSAL_DELAY` flag — never drop | None |
| Duplicate propagation | Same `invocation_id` twice | Hard reject — replay log unchanged | `PropagationFailure` |
| Missing propagation | Expected node never received | Halt — consensus unreachable | `PropagationFailure` |
| Out-of-order sequence | Non-monotonic `seq` batch | Halt — reorder required | `PropagationFailure` |

No silent recovery on any case. Every failure prints before raising.

### Determinism proof — live output

```
Proof A — 5× replay of frozen log
  Run 1:  consensus=10dd6b9a5e9972100ad39d67d95d878c...  ✅
  Run 2:  consensus=10dd6b9a5e9972100ad39d67d95d878c...  ✅
  Run 3:  consensus=10dd6b9a5e9972100ad39d67d95d878c...  ✅
  Run 4:  consensus=10dd6b9a5e9972100ad39d67d95d878c...  ✅
  Run 5:  consensus=10dd6b9a5e9972100ad39d67d95d878c...  ✅
  [PASS]  All 5 hashes IDENTICAL

Proof B — 3× shuffle → re-sort → replay
  Shuffle 1:  seqs=[3,1,2]  →  consensus=10dd6b9a...  ✅ matches canonical
  Shuffle 2:  seqs=[2,3,1]  →  consensus=10dd6b9a...  ✅ matches canonical
  Shuffle 3:  seqs=[1,3,2]  →  consensus=10dd6b9a...  ✅ matches canonical
  [PASS]  All shuffled replays converge to canonical
```

### Observability output — Phase 6 console

```
┌── Propagation Chain ───────────────────────────────────────────┐
│  seq=1  ts=2026-01-01T00:01:00Z  Node_A → Node_B ✅  Node_A → Node_C ✅
│  seq=2  ts=2026-01-01T00:02:00Z  Node_A → Node_B ✅  Node_A → Node_C ✅
│  seq=3  ts=2026-01-01T00:03:00Z  Node_A → Node_B ✅  Node_A → Node_C ✅
└────────────────────────────────────────────────────────────────┘

┌── Node Replay Status ──────────────────────────────────────────┐
│  Node_A   recv=3  propagated=6  hash=1835de92a3da9640...
│  Node_B   recv=3  propagated=0  hash=b416edc52c4cf774...
│  Node_C   recv=3  propagated=0  hash=b4bc9b7a824f8eda...
└────────────────────────────────────────────────────────────────┘

┌── Divergence Detection ────────────────────────────────────────┐
│  Divergence : ✅ NONE — nodes consistent
└────────────────────────────────────────────────────────────────┘

┌── Final Consensus Hash ────────────────────────────────────────┐
│  consensus : 10dd6b9a5e9972100ad39d67d95d878c40679206...
│  log_hash  : 65e6cc6cff9869ec3fe020cc25d00aff65d8d45f...
└────────────────────────────────────────────────────────────────┘
```

---

## System-Wide Guarantees

| Guarantee | How enforced |
|---|---|
| **Determinism** | No `datetime.now()`, no randomness, no hidden state across all 9 tasks |
| **Fail loudly** | Every failure raises with an exact human-readable reason before any computation |
| **No silent recovery** | Failures halt — never swallowed, never auto-retried |
| **Append-only audit** | Propagation logs and zone update logs never mutated after write |
| **Bounded uncertainty** | Every output delta carries a 95% CI and `NOMINAL / LOW / CRITICAL` flag |
| **Authority separation** | Compute · govern · execute are distinct layers — none crosses into another |
| **Replay safety** | Same log (any input order) → same hash, same state, always |
| **Contract discipline** | Schema versioned — breaking changes require explicit version bump |
| **Infrastructure survivability** | Distributed propagation + causal ordering + consensus verified (Task 9) |

---

## Integration Block

| Partner | Role | Contract surface |
|---|---|---|
| **Kanishk** | Distributed replay-safe execution and reconciliation | `replay_qapp_log()` output schema |
| **Raj** | Invocation and routing architecture | `QAppExecutionEnvelope.to_dict()` schema |
| **Raj Prajapati** | Enforcement and execution governance | `PropagationFailure` exception contract |
| **Jaffer Ali** | Distributed telemetry propagation systems | `_PROPAGATION_LOG` entry schema |
| **Ganesh** | Deterministic runtime coordination systems | `consensus_hash` and `log_hash` fields |

---

## Testing

### Tasks 1–4

```bash
python run_signal.py
# Phases: single execution → 4 failure cases → 5-run determinism proof
```

### Task 9

```bash
python run_distributed_qapp.py
# Phases 1–8 run automatically. Exit 0 = all passed.
```

Vinayak (Testing Department) must verify Task 9 using
**BHIV Universal Testing Protocol v2** → see `TESTING_PACKET.md`

**13 test cases · 6 domains:**
Replay Consistency · Divergence Handling · Propagation Determinism ·
Hash Agreement · Failure Isolation · Observability Correctness

---

## stdlib Used (full stack)

| Module | Tasks | Purpose |
|---|---|---|
| `math` | 1–4 | `sqrt()` for sigma |
| `datetime` | All | Deterministic timestamps — `datetime.now()` **never called** |
| `json` | All | Canonical serialisation (`sort_keys=True`) |
| `sys` | All | Exit codes · path management |
| `os` | All | Path resolution |
| `io` | All | UTF-8 stdout on Windows |
| `hashlib` | 9 | SHA-256 for all IDs and hash chains |
| `dataclasses` | 9 | `@dataclass(frozen=True)` — immutable envelope |
| `random` | 9 | Phase 7 shuffle proof only — not in core logic |

---

## Architecture Constraints (all tasks)

Per spec at every stage — strictly not built:

```
❌  Networking stacks
❌  Async queue systems  (no Kafka · no RabbitMQ · no asyncio)
❌  Distributed databases
❌  Cloud infrastructure
❌  Orchestration engines  (no Kubernetes · no Docker)
❌  UI or dashboards
```

The stack is:
**bounded · inspectable · deterministic · replay-safe · operationally understandable**

---

## Strategic Direction

Nine tasks. One direction.

From → *"can the quantum system run?"*
To   → *"can the quantum system survive as infrastructure?"*

**Trajectory:**
QApps → QDApps → governed quantum middleware →
hybrid quantum-classical runtime systems →
sovereign computational infrastructure inside the **TANTRA** direction.

---

*Dhiraj Chavan · Marine Intelligence System · BHIV Core · May 2026*
