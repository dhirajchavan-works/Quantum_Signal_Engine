# QApp — Distributed QApp Propagation Layer

**Marine Intelligence System | BHIV Core Infrastructure**
**Task 9 | May 2026**

A deterministic, distributed propagation system for QApp invocations across a 3-node cluster. Proves that the same QApp event, propagated across Node_A → Node_B → Node_C, produces an identical execution hash on every node — and survives replay, shuffle, and 4 classes of network failure.

---

## Run

```bash
python run_distributed_qapp.py
```

No arguments. No external dependencies. Python 3.8+. Standard library only.

---

## Structure

```
qapp/
├── envelope.py              ← QAppExecutionEnvelope (frozen dataclass, SHA-256 IDs)
├── nodes.py                 ← DistributedNode (receive, log, hash chain, replay)
├── propagation.py           ← propagate_qapp_event(), replay_qapp_log(), check_consensus()
├── failure_sim.py           ← 4 failure simulations (halt, no silent recovery)
├── run_distributed_qapp.py  ← Entry point — 7 phases, full determinism proof
└── REVIEW_PACKET.md         ← Full technical specification
```

---

## What It Does

The QApp propagation layer solves one problem: **given a QApp invocation on Node_A, prove that Node_B and Node_C end up in identical state, and that this is reproducible from any log**.

### Phase summary

| Phase | What it proves |
|---|---|
| 1 | Envelopes are created deterministically — no wall clock, no randomness |
| 2 | Node_A propagates to Node_B and Node_C in causal order |
| 3 | Append-only replay log and node state are fully inspectable |
| 4 | Replaying the log from scratch produces the same final hash |
| 5 | 4 failure classes are detected and halted — no silent failures |
| 6 | Observability output: propagation chain, node hashes, divergence rate |
| 7 | 5-run determinism proof + shuffle test — order-invariant convergence |

---

## Envelope

Every QApp invocation is wrapped in a `QAppExecutionEnvelope`:

```python
from envelope import make_envelope

env = make_envelope(
    qapp_id="marine_corrosion_qapp_v1",
    node_origin="Node_A",
    payload={"zone": "bow", "corrosion_rate": 0.05, "dt": 1.0},
    sequence_id=1,
)
```

All IDs are derived via SHA-256 — no UUIDs, no randomness, no wall clock:

```
trace_id      = SHA-256(qapp_id + node_origin + str(sequence_id))
invocation_id = SHA-256(qapp_id + node_origin + payload_hash + str(sequence_id))
payload_hash  = SHA-256(json.dumps(payload, sort_keys=True))
timestamp     = 2026-01-01T00:00:00Z + (sequence_id × 60s)
envelope_hash = SHA-256(all fields concatenated)
```

Same inputs → same envelope → same hash. Always.

---

## Propagation

```python
from propagation import propagate_qapp_event, check_consensus
from nodes import make_node_registry

nodes = make_node_registry()   # Node_A, Node_B, Node_C

record = propagate_qapp_event(envelope, nodes)
# → Node_A receives → Node_A records propagation
# → Node_B receives → Node_C receives → consensus checked
```

Console output per propagation:
```
┌─ PROPAGATE seq=1  invocation=ccbc812401d2023e...  env_hash=0ecd0729d6874994...
│  [Node_A] RECEIVED  seq=1  exec_hash=9c71ee015ea3821f...
│  [Node_A] PROPAGATING → Node_B, Node_C
│  [Node_B] RECEIVED  seq=1  exec_hash=9c71ee015ea3821f...
│  [Node_C] RECEIVED  seq=1  exec_hash=9c71ee015ea3821f...
└─ CONSENSUS ✓  hash=9c71ee015ea3821f...
```

**Execution hash (rolling chain, per node):**
```
execution_hash = SHA-256(execution_hash || envelope_hash)
```

Applied only to RECEIVED events. PROPAGATED events are routing metadata and do not change the hash.

---

## Replay

```python
from propagation import replay_qapp_log

result = replay_qapp_log(envelopes)
# Fresh nodes, sorted by sequence_id, replayed in order
# result["final_consensus_hash"] == original consensus hash
```

The replay sorts by `sequence_id` before applying, so input order is irrelevant. Proved by the shuffle test in Phase 7.

---

## Failure Cases

| Case | What happens | How it's caught |
|---|---|---|
| Delayed propagation | seq=2 arrives before seq=1 | `CAUSAL ORDER VIOLATION` — rejected, state unchanged |
| Duplicate propagation | Same envelope delivered twice | `DUPLICATE invocation_id` — rejected, hash unchanged |
| Missing propagation | Node_C never receives an envelope | `DIVERGENCE DETECTED` — consensus check fails |
| Out-of-order sequence_id | seq=5 arrives, seq=3 expected | `CAUSAL ORDER VIOLATION` — rejected, state unchanged |

No silent recovery. Every failure prints an explicit `!! HALT:` line and preserves the node's valid state.

---

## Ordering

`sequence_id` is the **sole ordering authority**. Timestamps exist for observability only and are never used for ordering decisions.

| Property | `sequence_id` | Timestamp |
|---|---|---|
| Assigned by | Hub / originator (monotonic) | Derived from `sequence_id` only |
| Used for ordering | Yes — strictly enforced | Never |
| Used for | Processing order, replay, causal chain | Human-readable observability |

---

## Determinism Proof

```
Run 1: 459837e3cbfd61e59bf4b5e0155514a0...
Run 2: 459837e3cbfd61e59bf4b5e0155514a0...
Run 3: 459837e3cbfd61e59bf4b5e0155514a0...
Run 4: 459837e3cbfd61e59bf4b5e0155514a0...
Run 5: 459837e3cbfd61e59bf4b5e0155514a0...

[PASS] All 5 hashes IDENTICAL — replay determinism CONFIRMED

Shuffled input order: [3, 1, 4, 2]
After sort:           [1, 2, 3, 4]
Canonical hash:  459837e3cbfd61e5...
Shuffled hash:   459837e3cbfd61e5...

[PASS] Shuffled input → same final hash — order-invariance CONFIRMED
```

---

## Observability

The console is the observability layer. No UI, no files, no external dashboards.

```
┌─────────────────────────────────────────────────────────────────┐
│  PROPAGATION CHAIN                                              │
├─────────────────────────────────────────────────────────────────┤
│  seq=1  Node_A → [Node_B, Node_C]  hash=9c71ee01...            │
│  seq=2  Node_A → [Node_B, Node_C]  hash=7eb8f4c4...            │
│  seq=3  Node_A → [Node_B, Node_C]  hash=eab4e337...            │
│  seq=4  Node_A → [Node_B, Node_C]  hash=459837e3...            │
├─────────────────────────────────────────────────────────────────┤
│  NODE REPLAY STATUS                                             │
├─────────────────────────────────────────────────────────────────┤
│  ✓ Node_A:  received=4  hash=459837e3cbfd61e5...               │
│  ✓ Node_B:  received=4  hash=459837e3cbfd61e5...               │
│  ✓ Node_C:  received=4  hash=459837e3cbfd61e5...               │
├─────────────────────────────────────────────────────────────────┤
│  DIVERGENCE DETECTION                                           │
│  divergence_rate = 0.0  (0 divergences in 4 propagations)      │
├─────────────────────────────────────────────────────────────────┤
│  CONSENSUS HASH                                                 │
│  459837e3cbfd61e59bf4b5e0155514a01d9a9e67671505a...            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Guarantees

- Same payload → same envelope → same propagation → same consensus hash. Always.
- Duplicate invocation_ids are rejected — no double-application possible.
- Out-of-order or missing envelopes halt with an explicit reason — never silently pass.
- Replay from log produces identical hash to live run.
- Shuffled input order converges to the same result after sort.
- All state is inspectable: `node.full_log()`, `node.execution_hash`, `node.received_invocations`.

---

## System Boundary

This layer handles envelope routing and hash consensus only. It does not:

- Know what the payload physically does to the hull
- Call Kanishk's physical engine (Tasks 1–8)
- Interpret CONVERGED / SUSPENDED / DIVERGED signal states
- Import any previous task files

*Dhiraj Chavan · Marine Intelligence System · May 2026*
