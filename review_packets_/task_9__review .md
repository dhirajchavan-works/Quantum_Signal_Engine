# REVIEW PACKET — Task 9: Distributed QApp Propagation Layer
**Marine Intelligence Quantum Pipeline | Task 9 of N**

---

## Entry Point

```
python run_distributed_qapp.py
```

No dependencies beyond Python stdlib (`hashlib`, `dataclasses`, `json`, `sys`, `random`).  
All phases run sequentially. Console output is the sole observability layer.

---

## QApp Invocation Flow

```
run_distributed_qapp.py
  └─ Phase 1: QAppExecutionEnvelope.create(...)
        qapp_id, node_origin, payload, sequence_id, contract_version
        → payload_hash   = SHA-256(json(payload))
        → trace_id       = SHA-256(qapp_id | node_origin | contract_version)
        → invocation_id  = SHA-256(qapp_id | node_origin | sequence_id)
        → timestamp      = "seq-<sequence_id>"   ← deterministic, no datetime.now()
```

Every field in `QAppExecutionEnvelope` is a pure function of its inputs.  
No clocks, no UUIDs, no randomness. The same inputs always produce the same envelope.

---

## Distributed Propagation Flow

```
Phase 2: propagate_qapp_event(envelope)

  Node_A.receive(envelope)          ← origin receipt
  Node_A.record_propagation(→ B, C) ← outbound log entry
  Node_B.receive(envelope)          ← downstream receipt
  Node_C.receive(envelope)          ← downstream receipt
  _PROPAGATION_LOG.append(entry)    ← global append-only log
```

**Causal ordering** is preserved by `sequence_id`:
- `propagate_qapp_event` rejects any envelope with `sequence_id < 1`.
- `replay_qapp_log` sorts the log by `sequence_id` before replaying, regardless of insertion order.
- Downstream nodes (`Node_B`, `Node_C`) have a strict monotonic acceptance rule enforced in failure simulations.

**Propagation log entry fields:**
`phase`, `sequence_id`, `invocation_id`, `trace_id`, `qapp_id`, `node_origin`,
`payload_hash`, `contract_version`, `timestamp`, `envelope_hash`, `path`

---

## Replay Reconstruction

```
Phase 4: replay_qapp_log(log, nodes=[Node_B, Node_C])

  1. Sort log entries by sequence_id (causal order enforcement)
  2. Check for duplicate sequence_ids → HALT if found
  3. For each entry:
       a. Recompute envelope_hash from fields
       b. Compare against stored envelope_hash → HALT if mismatch
       c. Apply to each replay node via node.receive(...)
  4. Compare final execution_hash across all replayed nodes
  5. HALT if hashes diverge (non-convergence = protocol violation)
  6. Return consensus_hash = SHA-256(sorted unique hashes)
```

**Determinism guarantee:** The execution_hash on each node is a rolling SHA-256:

```python
execution_hash = SHA-256(previous_hash | json(envelope_dict))
```

Because SHA-256 is deterministic and the log is sorted by `sequence_id`, any replay of the same log will produce the same final `execution_hash` on every node, every time.

---

## Failure Cases

### Case 1 — Delayed Propagation
**Trigger:** `seq=3` arrives before `seq=2`.  
**Detection:** `incoming_seq > expected_next` (expected = `len(received) + 1`).  
**Response:** Printed `[HALT]` message, seq=3 rejected, state preserved through seq=1.

### Case 2 — Duplicate Propagation
**Trigger:** Same `invocation_id` delivered twice.  
**Detection:** `invocation_id` already present in `received_invocations`.  
**Response:** Printed `[HALT]` message, second delivery rejected, `execution_hash` unchanged (asserted).

### Case 3 — Missing Propagation
**Trigger:** Log claims 3 envelopes propagated but seq=2 is absent.  
**Detection:** `len(incomplete_log) < declared_total`.  
**Response:** Printed `[HALT]` message, replay aborted, missing seq listed explicitly.

### Case 4 — Out-of-Order sequence_id
**Trigger:** Envelopes arrive in order `[3, 1, 2]`.  
**Detection:** `incoming_seq <= highest_accepted` (monotonic ordering violated).  
**Response:** Printed `[HALT]` message at first violation (seq=1 after seq=3 accepted), state preserved through last valid accept.

**All four cases:** never silent, never recover into corrupted state, always print a human-readable halt reason, always preserve the last known good replay state.

---

## Determinism Proof

### Phase 7a — Identical replays
The same propagation log is replayed 5 independent times into fresh node pairs.  
All 5 runs must produce the same `consensus_hash`.  
A mismatch triggers `sys.exit(1)` with a printed diff.

### Phase 7b — Shuffle → re-sort → re-replay
The log is shuffled (fixed seed=42), then re-sorted by `sequence_id`, then replayed.  
The resulting `consensus_hash` must match the Phase 7a value.  
This proves that insertion order does not affect correctness — only `sequence_id` ordering matters.

**Why this works:**  
`execution_hash` is accumulated in `sequence_id` order. The node's rolling hash function is:

```
H_n = SHA-256(H_{n-1} | json(envelope_n))
```

Same ordered sequence of envelopes → same chain of SHA-256 applications → same `H_n`.

---

## Observability Output

Phase 6 prints the following blocks to stdout:

| Block | Content |
|---|---|
| Propagation Chain | seq, origin node, target nodes, timestamp, qapp_id, contract version |
| Node Replay Status | received count, propagated count, execution hash prefix |
| Divergence Detection | hash comparison across replayed Node_B and Node_C |
| Consensus Hash | full 64-character SHA-256 hex string |
| Failure Case Status | HALTED / not triggered per case |

No UI, no database, no external calls. The terminal IS the observability layer.

---

## What Was Built

| File | Purpose |
|---|---|
| `envelope.py` | `QAppExecutionEnvelope` dataclass; all fields deterministically derived from inputs via SHA-256 |
| `nodes.py` | `DistributedNode` class; `Node_A`, `Node_B`, `Node_C` singletons with append-only replay logs |
| `propagation.py` | `propagate_qapp_event` (causal propagation) + `replay_qapp_log` (deterministic replay + hash verification) |
| `failure_sim.py` | 4 failure simulations: delayed, duplicate, missing, out-of-order — all halt with printed reason |
| `run_distributed_qapp.py` | 7-phase entry point: create → propagate → log → replay → failures → observe → prove |
| `REVIEW_PACKET.md` | This document |

---

## System Boundaries

**In scope (Task 9):**
- Deterministic envelope creation
- Single-hop propagation (Node_A → Node_B, Node_C)
- Append-only causal replay log
- Four failure detection modes with explicit halts
- Determinism proofs (5× replay, shuffle+re-sort)

**Out of scope (by design):**
- Multi-hop or recursive propagation
- Network transport (no sockets, no HTTP)
- Persistence (no files written, no databases)
- Async execution (single-threaded, sequential)
- Cross-task imports (Task 9 is fully self-contained)

---

## Known Infrastructure Risks

1. **Single global propagation log** — `_PROPAGATION_LOG` in `propagation.py` is a module-level list. In a real distributed system this would be a distributed ledger or WAL. Here it is in-process only.

2. **No network partitioning** — All three nodes live in the same process. True partition tolerance (CAP theorem) is not exercised; the failure simulations model the *logical* effects of partition, not physical network failures.

3. **Monotonic sequence_id is caller-managed** — There is no global sequence counter. The caller must supply a correct, incrementing `sequence_id`. A misbehaving caller can still inject a bad sequence; Task 9 detects but does not prevent this at the envelope creation layer.

4. **Shuffle seed is fixed** — Phase 7b uses `random.seed(42)` for reproducibility. In production, shuffle-invariance would be tested against truly arbitrary orderings, not a single fixed permutation.

5. **Hash rollup is linear** — The rolling `execution_hash` is a simple chain. A node that replays a subset of the log will produce a correct partial hash, but that hash cannot be compared to a full-log hash without the full log. There is no Merkle tree; subtree verification is not supported.
