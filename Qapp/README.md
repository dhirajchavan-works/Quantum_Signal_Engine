# Task 9 — Distributed QApp Propagation Layer

**Marine Intelligence System | BHIV Core Interface**
**Quantum Infrastructure / Distributed QApp Runtime Systems**

> This task proves that the QApp can survive as a distributed infrastructure
> participant inside TANTRA-style runtime systems — with replay-safe execution,
> governed propagation behaviour, and observable hybrid quantum-classical
> runtime coordination.

---

## Quick Start

```bash
git clone <repo-url>
cd task9-distributed-qapp
python run_distributed_qapp.py
```

**Requirements:** Python 3.8+ · No external dependencies · No pip installs

**Expected result:**
```
  OVERALL : PASS ✅
```

Exit code `0` on full pass. Exit code `1` with printed reason on any failure.

---

## What This Builds

Task 9 is the transition point from isolated quantum simulation into
distributed infrastructure engineering.

| Layer | Component | File |
|---|---|---|
| Invocation | `QAppExecutionEnvelope` — immutable, SHA-256 IDs, deterministic | `envelope.py` |
| Node simulation | `Node_A`, `Node_B`, `Node_C` — hash chains, append-only logs | `nodes.py` |
| Propagation engine | Fan-out A → [B, C], causal ordering, append-only log | `propagation.py` |
| Replay reconstruction | Re-sort, hash rebuild, consensus, coverage check | `propagation.py` |
| Failure simulation | 4 cases — loud halt, valid state preserved | `failure_sim.py` |
| Entry point | 8-phase driver, full observability, determinism proofs | `run_distributed_qapp.py` |
| Documentation | 10-section review packet | `REVIEW_PACKET.md` |
| Testing | BHIV Universal Testing Protocol v2 | `TESTING_PACKET.md` |

---

## Phase Breakdown

| Phase | Name | What runs |
|---|---|---|
| 1 | QApp Invocation Envelope | Create 3 deterministic envelopes — no `datetime.now()`, no randomness |
| 2 | Distributed Node Simulation | Initialise Node_A, Node_B, Node_C — show pre-propagation state |
| 3 | QApp Propagation Engine | Node_A fans out to Node_B and Node_C — log every step |
| 4 | Distributed Replay Reconstruction | Replay log from scratch — verify hashes match live nodes |
| 5 | Divergence + Failure Simulation | 4 cases: delayed, duplicate, missing, out-of-order |
| 6 | Observability Layer | Propagation chain · node status · divergence · consensus hash |
| 7 | Determinism Proof | 5× replay identical · shuffle-then-resort converges |
| 8 | REVIEW_PACKET.md | Documentation artefact — verified by file-presence check |

---

## Propagation Model

```
QAppExecutionEnvelope (seq=1)
        │
        ▼
  Node_A  ← origin
        │
        ├──→  Node_B  ✅
        └──→  Node_C  ✅
```

Every step is logged to an **append-only** propagation log.
`replay_qapp_log()` causal-sorts by `(sequence_id, step_order)` before
rebuilding hash chains — so replay is **log-order-independent**.

---

## Determinism Guarantees

```
Same envelope inputs    →  identical QAppExecutionEnvelope, always
Same propagation log    →  identical consensus_hash across 5 replays
Shuffled log + re-sort  →  same consensus_hash (3 shuffle trials confirmed)
```

No `datetime.now()`. No `random`. No hidden state. Everything inspectable.

---

## Failure Cases

| Case | Trigger | Action | Exception |
|---|---|---|---|
| Delayed propagation | `sequence_id` gap > threshold | Accept with `CAUSAL_DELAY` flag | None |
| Duplicate propagation | Same `invocation_id` received twice | Hard reject, log unchanged | `PropagationFailure` |
| Missing propagation | Expected node never received envelope | Halt, partial state preserved | `PropagationFailure` |
| Out-of-order sequence | Non-monotonic `sequence_id` batch | Halt, batch discarded | `PropagationFailure` |

No silent recovery on any case.

---

## File Structure

```
task9-distributed-qapp/
├── run_distributed_qapp.py     ← ENTRY POINT
├── envelope.py                 ← Phase 1: QAppExecutionEnvelope
├── nodes.py                    ← Phase 2: DistributedNode + 3 singletons
├── propagation.py              ← Phase 3 + 4: engine + replay
├── failure_sim.py              ← Phase 5: 4 failure simulators
├── REVIEW_PACKET.md            ← Phase 8: 10-section design review
├── TESTING_PACKET.md           ← Vinayak: BHIV Universal Testing Protocol v2
├── README.md                   ← this file
├── requirements.txt            ← stdlib only declaration
└── .gitignore
```

Core Python files: **5** (within spec limit of 5–7).

---

## Architecture Constraints

Per spec — strictly **not** built:

- ❌ Networking stacks
- ❌ Async queue systems (no Kafka, no RabbitMQ)
- ❌ Distributed databases
- ❌ Cloud infrastructure
- ❌ Orchestration engines

This is a **propagation simulation layer only** — bounded, inspectable,
deterministic, replay-safe, operationally understandable.

---

## Integration Block

| Partner | Role |
|---|---|
| **Kanishk** | Distributed replay-safe execution and reconciliation |
| **Raj** | Invocation and routing architecture |
| **Raj Prajapati** | Enforcement and execution governance |
| **Jaffer Ali** | Distributed telemetry propagation systems |
| **Ganesh** | Deterministic runtime coordination systems |

---

## Testing

Testing must be conducted by **Vinayak** using **BHIV Universal Testing Protocol v2**.

See [`TESTING_PACKET.md`](TESTING_PACKET.md) for:
- 13 test cases across 6 domains
- Expected output for every phase
- Pass/fail criteria
- Final verdict form

---

## Previous Tasks

This task extends the Marine Intelligence quantum pipeline:

| Task | Description |
|---|---|
| Task 1 | Digital Twin Definition — hull degradation model |
| Task 2 | Quantum Parameter Engine + State Mapping |
| Task 3 | Signal Generator Design |
| Task 4 | BHIV Core Interface Preparation |
| Tasks 5–8 | Governance, contracts, bounded probabilistic computation |
| **Task 9** | **Distributed QApp Propagation Layer** ← this task |

Task 9 does **not** import from any previous task files. Fully self-contained.

---

## stdlib Used

```
hashlib    — SHA-256 for all ID and hash computation
dataclasses — frozen QAppExecutionEnvelope
datetime   — deterministic timestamp from sequence_id (no datetime.now())
json       — canonical serialisation
sys        — exit codes, path management
os         — path resolution
io         — UTF-8 stdout on Windows
random     — Phase 7 shuffle proof only
```

---

*Dhiraj Chavan · Marine Intelligence System · BHIV Core · May 2026*
