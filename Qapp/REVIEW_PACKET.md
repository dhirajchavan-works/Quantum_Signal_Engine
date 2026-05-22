# REVIEW_PACKET.md
# Task 9 — Distributed QApp Propagation Layer
# Marine Intelligence System | BHIV Core Interface
# Quantum Infrastructure / Distributed QApp Runtime Systems

**Author:** Dhiraj Chavan
**Date:** May 2026
**Task Classification:** 8-phase distributed QApp infrastructure sprint
**Integration Block:** Kanishk · Raj · Raj Prajapati · Jaffer Ali · Ganesh

---

## 1. Entry Point

```bash
python run_distributed_qapp.py
```

**Requirements:**
- Python 3.8 or higher
- No external dependencies — pure Python standard library only
- No arguments required
- No manual steps

**Exit codes:**
- `0` — all 8 phases passed
- `1` — any phase failed (reason printed before exit)

**File structure:**
```
task9-distributed-qapp/
├── run_distributed_qapp.py     ← ENTRY POINT — run this
├── envelope.py                 ← Phase 1: QAppExecutionEnvelope
├── nodes.py                    ← Phase 2: DistributedNode + 3 singletons
├── propagation.py              ← Phase 3 + 4: engine + replay
├── failure_sim.py              ← Phase 5: 4 failure case simulators
├── REVIEW_PACKET.md            ← Phase 8: this document
├── TESTING_PACKET.md           ← Vinayak: BHIV Universal Testing Protocol v2
├── README.md
├── requirements.txt
└── .gitignore
```

---

## 2. QApp Invocation Flow

Each QApp execution produces exactly one `QAppExecutionEnvelope` — an immutable,
frozen dataclass. Every field is deterministic. No `datetime.now()`. No randomness.
No hidden fields. Same inputs always produce an identical envelope.

**Construction pipeline:**

```
caller supplies: qapp_id, node_origin, payload (dict), sequence_id, contract_version
                                │
                                ▼
payload_hash    = SHA-256( canonical_json(payload, sort_keys=True) )
trace_id        = SHA-256( f"trace:{qapp_id}:{node_origin}:{sequence_id}" )
invocation_id   = SHA-256( f"invoke:{trace_id}:{payload_hash}:{sequence_id}" )
timestamp       = 2026-01-01T00:00:00Z  +  (sequence_id × 60 seconds)
                                │
                                ▼
QAppExecutionEnvelope(frozen=True)  ← immutable after construction
```

**Required fields (spec §Phase 1):**

| Field | Type | Derivation | Purpose |
|---|---|---|---|
| `trace_id` | str (SHA-256 hex) | `SHA-256("trace:{qapp_id}:{node_origin}:{seq}")` | Ties one causal chain together |
| `qapp_id` | str | Caller-supplied | Human-readable QApp identifier |
| `node_origin` | str | Caller-supplied | Node that created this invocation |
| `invocation_id` | str (SHA-256 hex) | `SHA-256("invoke:{trace_id}:{payload_hash}:{seq}")` | Proves exact payload was invoked |
| `payload_hash` | str (SHA-256 hex) | `SHA-256(canonical_json(payload))` | Content integrity fingerprint |
| `sequence_id` | int | Caller-supplied (monotonic, ≥ 1) | Causal ordering key |
| `timestamp` | str (ISO-8601 UTC) | `anchor + seq × 60s` | Deterministic — no wall clock |
| `contract_version` | str | Caller-supplied | Schema version for downstream validation |

**Live example — seq=1, payload=qnode_01:**
```json
{
    "trace_id":         "e897fd62515f1161ae562fc7a3b64f59...",
    "qapp_id":          "bhiv.corrosion.delta.v1",
    "node_origin":      "Node_A",
    "invocation_id":    "9d0eb6ca72948342786483c4d5cf74f2...",
    "payload_hash":     "e75a9e9d9e78709c55ea69032c5987ae...",
    "sequence_id":      1,
    "timestamp":        "2026-01-01T00:01:00Z",
    "contract_version": "qapp-v1.0"
}
```

**Determinism guarantee:** `QAppExecutionEnvelope.create(same_args)` returns an
identical object on every call, across every machine, forever.

---

## 3. Distributed Propagation Flow

**Topology:** single-origin fan-out (spec §Phase 3).

```
Node_A  (origin — receives its own event, then forwards)
  │
  ├──→  Node_B  (downstream receiver)
  └──→  Node_C  (downstream receiver)
```

**Per-envelope propagation sequence inside `propagate_qapp_event(envelope)`:**

```
Step 1  Node_A.receive(env_dict)
        _PROPAGATION_LOG ← { step: "ORIGIN",    from: "Node_A", to: "Node_A", ... }
        Node_A.execution_hash updated

Step 2  Node_A.record_propagation(env_dict, "Node_B")
        Node_B.receive(env_dict)
        _PROPAGATION_LOG ← { step: "PROPAGATE", from: "Node_A", to: "Node_B", ... }
        Node_B.execution_hash updated

Step 3  Node_A.record_propagation(env_dict, "Node_C")
        Node_C.receive(env_dict)
        _PROPAGATION_LOG ← { step: "PROPAGATE", from: "Node_A", to: "Node_C", ... }
        Node_C.execution_hash updated
```

**Execution hash chain per node:**

```
initial_hash  = SHA-256("INIT:<node_id>")
after_recv_1  = SHA-256( f"{initial_hash}:{invocation_id_1}" )
after_recv_2  = SHA-256( f"{after_recv_1}:{invocation_id_2}" )
...
```

Inserting, deleting, or reordering any received invocation changes the final hash.
The chain is tamper-evident without any external library.

**Causal ordering:**
Every log entry carries `sequence_id`. `replay_qapp_log()` sorts by
`(sequence_id, step_order)` — ORIGIN before PROPAGATE within a single sequence —
so a shuffled log always reconstructs to the same canonical state.

**Append-only invariant:**
`_PROPAGATION_LOG` is never mutated after write. `get_propagation_log()` returns a
shallow copy. Callers cannot corrupt the source.

**Log entry shape:**
```json
{
    "step":          "PROPAGATE",
    "from":          "Node_A",
    "to":            "Node_B",
    "invocation_id": "9d0eb6ca...",
    "sequence_id":   1,
    "trace_id":      "e897fd62...",
    "timestamp":     "2026-01-01T00:01:00Z"
}
```

---

## 4. Replay Reconstruction

`replay_qapp_log(log)` reconstructs the full propagation path deterministically
from any snapshot of the propagation log (spec §Phase 4).

**Algorithm:**

```
Input: log (list of propagation entries, any order)

1. Causal-sort:
       sorted_log = sorted(log, key=lambda e: (e["sequence_id"], STEP_ORDER[e["step"]]))
       STEP_ORDER = { "ORIGIN": 0, "PROPAGATE": 1 }

2. Rebuild node hash chains from scratch:
       for each node_id in ["Node_A", "Node_B", "Node_C"]:
           hash = SHA-256("INIT:<node_id>")
       for entry in sorted_log where entry["to"] == node_id:
           hash = SHA-256(f"{hash}:{entry['invocation_id']}")

3. consensus_hash  = SHA-256( json({ Node_A: h, Node_B: h, Node_C: h }, sort_keys) )
4. log_hash        = SHA-256( canonical_json(sorted_log) )
5. coverage check  = verify Node_A / Node_B / Node_C received identical invocation sets

Output: { node_hashes, consensus_hash, log_hash, consistent, coverage }
```

**Phase 4 verification (live vs replay):**
Replayed `node_hashes[N]` is compared to `ALL_NODES[N].execution_hash` for all
three nodes. Any mismatch is a hard FAIL — it means propagation code and replay
code have diverged.

**Why node hashes differ between B and C:**
Node_B and Node_C execution hashes are intentionally different from each other.
Each chain begins at `SHA-256("INIT:<node_id>")`, embedding node identity into
every link. Consensus is verified via the `consistent` flag (same invocation sets),
not raw hash equality between different nodes.

---

## 5. Failure Cases

All failure cases implemented in `failure_sim.py`. Every case:
- prints a structured `┌─/│/└─` block before raising or returning
- never silently recovers
- preserves valid replay state for unaffected nodes

### Case 1 — Delayed Propagation

```
Trigger  : envelope arrives with sequence_id gap > DELAY_THRESHOLD (default = 3)
Example  : seq=10 arrives after last_acknowledged_seq=3  →  gap = 6
Policy   : ACCEPTED with flag=CAUSAL_DELAY  (delayed-but-valid data is never dropped)
Action   : return dict with { status: "DELAYED", flag: "CAUSAL_DELAY", gap: 6 }
No exception raised — the flag is the signal for downstream audit
```

### Case 2 — Duplicate Propagation

```
Trigger  : invocation_id already present in seen_invocations set
Example  : seq=1 envelope received twice
Policy   : HARD REJECT — replay log unchanged, idempotent
Action   : PropagationFailure("Duplicate invocation: 9d0eb6ca...")
Replay state : unmodified for all nodes
```

### Case 3 — Missing Propagation

```
Trigger  : one or more expected nodes never received an envelope
Example  : expected=[A, B, C], received=[A, B]  →  Node_C missing
Policy   : HALT — consensus cannot be reached
Action   : PropagationFailure("Missing propagation to ['Node_C']...")
Replay state : A and B states preserved and valid; C is flagged absent
```

### Case 4 — Out-of-Order Sequence ID

```
Trigger  : non-monotonic sequence_ids in a delivery batch
Example  : batch [seq=1, seq=3, seq=2] → violation at index 2
Policy   : HALT at first violation — entire batch rejected
Action   : PropagationFailure("Out-of-order at index 2: seq=2 arrived after seq=3")
Replay state : unaffected — batch was not applied
Note     : replay_qapp_log() auto-sorts stored logs, so this case applies to
           live delivery before storage, not to post-storage replay
```

**Confidence flags on failure outputs:**

| Flag | Condition | Engine Behaviour |
|---|---|---|
| `CAUSAL_DELAY` | Gap > threshold | Accepted; logged for audit; human review advised |
| `REJECTED` | Duplicate invocation_id | Hard reject; no state change |
| `CONSENSUS_FAIL` | Node missing from propagation | Halt; partial state preserved |
| `ORDER_VIOLATION` | Non-monotonic sequence | Halt; batch discarded |

---

## 6. Determinism Proof

### Proof A — 5× replay of same frozen log

```
Frozen log captured after Phase 3 propagation (9 entries, 3 envelopes × 3 steps).
Same log replayed 5 times without modification.

Run 1:  consensus=10dd6b9a5e9972100ad39d67d95d878c40679206...  ✅
Run 2:  consensus=10dd6b9a5e9972100ad39d67d95d878c40679206...  ✅
Run 3:  consensus=10dd6b9a5e9972100ad39d67d95d878c40679206...  ✅
Run 4:  consensus=10dd6b9a5e9972100ad39d67d95d878c40679206...  ✅
Run 5:  consensus=10dd6b9a5e9972100ad39d67d95d878c40679206...  ✅

[PASS]  All 5 consensus hashes IDENTICAL — determinism CONFIRMED
```

### Proof B — shuffle propagation log 3×, replay each, verify convergence

```
The causal sort in replay_qapp_log() re-orders any shuffled input by
(sequence_id, step_order) before computing hashes.
A shuffled log that is correctly re-sorted must always converge to the
same canonical consensus hash.

Shuffle 1:  seqs=[3,1,2]  →  consensus=10dd6b9a...  ✅ matches canonical
Shuffle 2:  seqs=[2,3,1]  →  consensus=10dd6b9a...  ✅ matches canonical
Shuffle 3:  seqs=[1,3,2]  →  consensus=10dd6b9a...  ✅ matches canonical

[PASS]  All shuffled replays converge to canonical — causal sort CONFIRMED
```

**Why this matters:**
In a real distributed system, log entries may arrive from different network paths
in arbitrary order. The causal sort is the mechanism that makes replay
order-independent. These proofs validate that mechanism directly.

---

## 7. Observability Output

The console is the complete observability layer. No UI, no external tooling,
no log aggregation service required (spec §Phase 6).

**Five required outputs — all rendered in Phase 6:**

### 1. Propagation Chain
```
┌── Propagation Chain ─────────────────────────────────────────┐
│  seq=1  ts=2026-01-01T00:01:00Z
│  invoke=9d0eb6ca72948342786483c4...
│  Node_A  →  Node_B  ✅
│  Node_A  →  Node_C  ✅
│  ·
│  seq=2  ts=2026-01-01T00:02:00Z
│  ...
└──────────────────────────────────────────────────────────────┘
```

### 2. Node Replay Status
```
┌── Node Replay Status ────────────────────────────────────────┐
│  Node_A   recv= 3  propagated= 6  log_entries= 9  hash=1835de92...
│  Node_B   recv= 3  propagated= 0  log_entries= 3  hash=b416edc5...
│  Node_C   recv= 3  propagated= 0  log_entries= 3  hash=b4bc9b7a...
└──────────────────────────────────────────────────────────────┘
```

### 3. Divergence Detection
```
┌── Divergence Detection ─────────────────────────────────────┐
│  Node_B invocations : ['9d0eb6ca...', 'a9d7bb85...', 'b1bdb8c5...']
│  Node_C invocations : ['9d0eb6ca...', 'a9d7bb85...', 'b1bdb8c5...']
│  Divergence         : ✅ NONE — nodes consistent
└──────────────────────────────────────────────────────────────┘
```

### 4. Replay Verification
```
┌── Replay Verification ──────────────────────────────────────┐
│  Node_A   hash=1835de92a3da964062cf90f3...
│  Node_B   hash=b416edc52c4cf77450...
│  Node_C   hash=b4bc9b7a824f8eda...
│  consistent : ✅ YES
└──────────────────────────────────────────────────────────────┘
```

### 5. Final Consensus Hash
```
┌── Final Consensus Hash ─────────────────────────────────────┐
│  consensus : 10dd6b9a5e9972100ad39d67d95d878c40679206...
│  log_hash  : 65e6cc6cff9869ec3fe020cc25d00aff65d8d45f...
└──────────────────────────────────────────────────────────────┘
```

---

## 8. What Was Built

| Component | File | Spec Phase | Description |
|---|---|---|---|
| Execution envelope | `envelope.py` | Phase 1 | Frozen dataclass, SHA-256 IDs, deterministic timestamp |
| Node simulation | `nodes.py` | Phase 2 | 3 singletons, 4 tracking fields, hash chains |
| Propagation engine | `propagation.py` | Phase 3 | Fan-out, append-only log, causal sort |
| Replay reconstruction | `propagation.py` | Phase 4 | Hash rebuild, consensus, coverage check |
| Failure simulation | `failure_sim.py` | Phase 5 | 4 cases, structured halt, no silent recovery |
| Entry point | `run_distributed_qapp.py` | All phases | 8-phase driver, exit 0/1 |
| Documentation | `REVIEW_PACKET.md` | Phase 8 | This document — 10 mandatory sections |
| Testing protocol | `TESTING_PACKET.md` | — | Vinayak: BHIV Universal Testing Protocol v2 |

**Architectural decisions:**

**Frozen dataclass for envelope** — Immutability is contractual. Any attempt to
modify a field after construction raises a `FrozenInstanceError` at the Python level.

**SHA-256 chain for execution hash** — Tamper-evident without any external library.
Insertion, deletion, or reordering of received invocations changes every downstream
hash link.

**Causal sort key `(sequence_id, step_order)`** — Replay is log-order-independent.
This is the mechanism that makes distributed replay safe regardless of delivery order.

**`PropagationFailure` always preceded by a print** — Never silent. The console
message and the exception carry the same reason string so both log-aggregation
and human readers get identical information.

**`get_propagation_log()` returns a copy** — The global log cannot be mutated by
callers. Replay runs on snapshots, not on live references.

**No genesis hash sharing across nodes** — Each node's chain begins at
`SHA-256("INIT:<node_id>")`. Node identity is embedded in every hash link.
Consensus is verified via identical invocation coverage, not raw hash equality.

---

## 9. System Boundaries

### In scope

- QApp execution envelope creation (Phase 1)
- 3-node propagation environment simulation (Phase 2)
- Single-origin fan-out propagation: Node_A → [Node_B, Node_C] (Phase 3)
- Append-only propagation log (Phase 3)
- Replay reconstruction and hash verification (Phase 4)
- Four failure mode detection and halt (Phase 5)
- Console observability layer (Phase 6)
- Determinism proofs — 5× replay, 3× shuffle convergence (Phase 7)
- Integration documentation (Phase 8)

### Out of scope (per spec §IMPORTANT ARCHITECTURAL CONSTRAINTS)

- Networking stacks — no sockets, no HTTP, no gRPC
- Async queue systems — no Kafka, no RabbitMQ, no asyncio
- Distributed databases — no SQL, no NoSQL, no file-backed stores
- Cloud infrastructure — no AWS, no GCP, no Azure
- Orchestration engines — no Kubernetes, no Docker, no systemd
- Kanishk's execution engine — not imported, not mutated
- Enforcement logic — delegated to Raj Prajapati's governance layer
- Peer-to-peer topologies — only single-origin fan-out

### Integration contracts

| Partner | Role | Contract |
|---|---|---|
| Kanishk | Distributed replay-safe execution and reconciliation | `replay_qapp_log()` output dict schema |
| Raj | Invocation and routing architecture | `QAppExecutionEnvelope.to_dict()` schema |
| Raj Prajapati | Enforcement and execution governance | `PropagationFailure` exception contract |
| Jaffer Ali | Distributed telemetry propagation systems | `_PROPAGATION_LOG` entry schema |
| Ganesh | Deterministic runtime coordination systems | `consensus_hash` and `log_hash` fields |

---

## 10. Known Infrastructure Risks

| Risk | Severity | Detection mechanism | Mitigation status |
|---|---|---|---|
| Sequence ID reuse | HIGH | Out-of-order check uses `<=` not `<` — catches non-strictly-monotonic | Enforced at origin; no auto-repair |
| Partial fan-out (Node_C never receives) | HIGH | `simulate_missing_propagation()` halts with named missing nodes | Caller must resolve; no auto-retry |
| Log entry modification after write | HIGH | `log_hash` and replayed `node_hashes` diverge from live values | Phase 4 cross-check catches at runtime |
| `datetime.now()` introduced by future contributor | HIGH | Timestamp format `YYYY-MM-DDTHH:MM:SSZ` is visually identical — hard to audit | Enforced by `compute_timestamp()` — `_ANCHOR + seq × 60s` only; no import of `datetime.now` |
| Causal delay accumulation | MEDIUM | `CAUSAL_DELAY` flag; gap value quantified in return dict | Flagged and logged; threshold configurable via `DELAY_THRESHOLD` constant |
| Memory growth (unbounded log) | MEDIUM | `len(get_propagation_log())` visible in Phase 6 output | No rotation in this layer — caller responsibility |
| Node genesis hash collision | LOW | Two node IDs producing the same `SHA-256("INIT:<id>")` | SHA-256 collision resistance sufficient; node IDs are human-controlled strings |
| SHA-256 collision (invocation_id) | NEGLIGIBLE | Would require deliberate adversarial construction | Not a risk at this scale or threat model |

---

## Compliance Checklist

| Spec Requirement | File | Status |
|---|---|---|
| 8 phases implemented | `run_distributed_qapp.py` | ✅ |
| QAppExecutionEnvelope with all 8 required fields | `envelope.py` | ✅ |
| No `datetime.now()` | `envelope.py` | ✅ |
| No randomness | `envelope.py` | ✅ |
| No hidden fields | `envelope.py` | ✅ |
| 3-node environment (Node_A, Node_B, Node_C) | `nodes.py` | ✅ |
| Each node tracks 4 required fields | `nodes.py` | ✅ |
| No databases | `nodes.py` | ✅ |
| `propagate_qapp_event()` fan-out A → B, C | `propagation.py` | ✅ |
| Propagation path logged | `propagation.py` | ✅ |
| Causal ordering preserved via sequence_id | `propagation.py` | ✅ |
| Append-only replay log | `propagation.py` | ✅ |
| `replay_qapp_log()` reconstructs and verifies | `propagation.py` | ✅ |
| Same replay → same final state | `propagation.py` | ✅ |
| 4 failure cases simulated | `failure_sim.py` | ✅ |
| Each failure emits readable halt reason | `failure_sim.py` | ✅ |
| Valid replay state preserved on failure | `failure_sim.py` | ✅ |
| No silent recovery | `failure_sim.py` | ✅ |
| Observability: 5 required outputs | `run_distributed_qapp.py` Phase 6 | ✅ |
| Determinism: 5× replay identical hashes | `run_distributed_qapp.py` Phase 7 | ✅ |
| Determinism: shuffle convergence | `run_distributed_qapp.py` Phase 7 | ✅ |
| Max 5–7 core Python files | All | ✅ (5 files) |
| Runs via `python run_distributed_qapp.py` | `run_distributed_qapp.py` | ✅ |
| REVIEW_PACKET.md with 10 sections | `REVIEW_PACKET.md` | ✅ |
| Pure Python stdlib only | All | ✅ |

---

*Dhiraj Chavan · Marine Intelligence System · BHIV Core · May 2026*
