# Task 9 Review — Distributed QApp Propagation Layer
**Author:** Dhiraj Chavan | Marine Intelligence System
**Date:** May 2026 | contract_version: 2.0

---

## 1. ENTRY POINT

```bash
python run_distributed_qapp.py
```

No arguments. No external dependencies. Python 3.8+. Exit code 0 on full PASS.

---

## 2. FILE STRUCTURE

```
quantum-signal-engine/
├── core.py                    ← QAppExecutionEnvelope, QAppNode, PropagationEngine
├── engine.py                  ← sorting, replay verification, failure handlers
├── run_distributed_qapp.py    ← single entry point, 7-phase execution proof
├── requirements.txt
└── REVIEW_PACKET.md
```

---

## 3. CORE ARCHITECTURE

**3 classes. Fixed roles.**

```
core.QAppExecutionEnvelope  ← frozen dataclass; immutable event contract
core.QAppNode               ← stateful node: dedup map, replay log, execution hash
core.PropagationEngine      ← routes Node_A events to Node_B + Node_C
```

**engine.py exposes:**
```
sort_envelopes()              ← (timestamp, sequence_id) sort; O(n log n)
reconstruct_chronological()   ← wraps sort on node.replay_log
deterministic_replay_verify() ← 5x SHA-256 replay loop; raises ReplayDivergenceError
reject_corrupted()            ← recomputes hash; raises CorruptedHashError on mismatch
simulate_failure_sequence_gap() ← raises SequenceGapError on non-consecutive seq IDs
propagate_ordered()           ← sorts then calls engine.propagate() per envelope
```

---

## 4. EXECUTION ENVELOPE CONTRACT

| Field | Type | Constraint |
|---|---|---|
| `trace_id` | str | globally unique per trace |
| `qapp_id` | str | application identifier |
| `node_origin` | str | source node ID |
| `invocation_id` | str | globally unique per event |
| `payload_hash` | str | SHA-256 hex of raw payload |
| `sequence_id` | int | monotonically increasing, gap-free |
| `timestamp` | int | logical step; never wall-clock |
| `contract_version` | str | "2.0" |

---

## 5. STATE HASH MODEL

Each node maintains `execution_hash` — a compounded deterministic SHA-256 chain:

```
h₀ = SHA256(node_id)
hₙ = SHA256(f"{hₙ₋₁}:{payload_hash}:{sequence_id}")
```

Properties: order-dependent, append-only, reproducible from replay_log alone.
Same event set + same order → identical hash across any number of replay runs.

---

## 6. DETERMINISTIC REPLAY VERIFICATION

`deterministic_replay_verify(node, runs=5)`:
1. Extracts `replay_log` via `reconstruct_chronological()` (sorted by timestamp, seq).
2. Recomputes hash chain from `SHA256(node_id)` base, 5 independent times.
3. Compares all 5 results — any divergence raises `ReplayDivergenceError` with full halt reason.
4. Returns verified hash on PASS.

---

## 7. FAILURE HANDLERS

| Exception | Trigger | Halt Message Format |
|---|---|---|
| `CorruptedHashError` | `stored_hash != SHA256(raw_payload)` | `HALT \| invocation_id=... \| payload_hash mismatch \| stored=... \| computed=...` |
| `SequenceGapError` | `seq[i] != seq[i-1] + 1` | `HALT \| Node=... \| SequenceGap detected: expected seq=N, got seq=M \| invocation_id=...` |
| `ReplayDivergenceError` | 5-run hash set cardinality > 1 | `HALT \| Node=... \| replay produced divergent hashes across N runs \| hashes=[...]` |

All exceptions inherit from `Exception`. All halt messages are explicit, no silent swallowing.

---

## 8. DUPLICATE SUPPRESSION

`QAppNode.log_and_compute()` checks `invocation_id` against `received_invocations` dict before any mutation. Duplicate events are dropped in O(1) with no state change. Idempotent under arbitrary redelivery.

---

## 9. OUT-OF-ORDER CONVERGENCE

`sort_envelopes()` sorts on `(timestamp, sequence_id)`. `propagate_ordered()` applies this sort before routing. `reconstruct_chronological()` applies it on the stored replay log. Any arrival order produces identical sorted sequence, identical hash chain, identical output.

**Proof (Phase 3):** Input `[seq=3, seq=1, seq=2]` → sorted `[1, 2, 3]` → chronological reconstruction `[1, 2, 3]` → [PASS].

---

## 10. COMPLIANCE CHECKLIST

| Requirement | Status |
|---|---|
| Frozen envelope dataclass | ✅ |
| Duplicate suppression via `invocation_id` dict | ✅ |
| SHA-256 compounded execution hash | ✅ |
| Chronological sort on `(timestamp, seq)` | ✅ |
| 5x deterministic replay verification | ✅ |
| `CorruptedHashError` with HALT message | ✅ |
| `SequenceGapError` with HALT message | ✅ |
| `ReplayDivergenceError` with HALT message | ✅ |
| No external dependencies | ✅ |
| No file I/O in core/engine | ✅ |
| No wall-clock timestamps | ✅ |
| Single entry point `run_distributed_qapp.py` | ✅ |
| Exit code 0 on full PASS | ✅ |
| Cross-node invocation set parity proof | ✅ |
