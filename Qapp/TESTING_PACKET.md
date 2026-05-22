# TESTING_PACKET.md
# Task 9 — Distributed QApp Propagation Layer
# BHIV Universal Testing Protocol v2
# Marine Intelligence System | Testing Department

**Prepared for:** Vinayak (Testing Department)
**Prepared by:** Dhiraj Chavan
**Task:** Task 9 — Distributed QApp Propagation Layer
**Protocol:** BHIV Universal Testing Protocol v2
**Date:** May 2026

---

## Testing Authority

This packet must be used by Vinayak and the Testing Department to verify Task 9
against the BHIV Universal Testing Protocol v2. All test cases derive directly
from three sources:

1. **Assigned task spec** — 8-phase distributed QApp infrastructure sprint
2. **REVIEW_PACKET.md** — implementation design and compliance record
3. **Actual runnable output** — `python run_distributed_qapp.py`

Testing must cover all six domains listed in the spec:
replay consistency · divergence handling · propagation determinism ·
hash agreement · failure isolation · observability correctness

---

## Pre-Test Setup

### Environment requirements

```bash
python --version     # must be Python 3.8+
# No pip installs needed — pure stdlib
```

### How to run

```bash
git clone <repo-url>
cd task9-distributed-qapp
python run_distributed_qapp.py
```

### Expected exit code
```
Exit 0  →  all 8 phases passed
Exit 1  →  failure (reason printed before exit)
```

### Clean run indicator
The last lines of output must contain:
```
OVERALL : PASS ✅
```

---

## Test Suite

---

### DOMAIN 1 — Replay Consistency

**Test ID:** TC-REPLAY-01
**Spec reference:** Phase 4 — Distributed Replay Reconstruction
**REVIEW_PACKET section:** §4 Replay Reconstruction

**What to verify:**
Replaying the propagation log from scratch must reproduce the exact same
execution hash for every node as the live node state after propagation.

**Test procedure:**
```bash
python run_distributed_qapp.py
```
Look for Phase 4 output block.

**Expected output (Phase 4):**
```
Comparing replayed hashes to live node state:
  Node_A  live=<hash>...  replay=<hash>...  ✅
  Node_B  live=<hash>...  replay=<hash>...  ✅
  Node_C  live=<hash>...  replay=<hash>...  ✅

✅  Replay reconstructed  |  hash match=True  |  consistent=True
```

**Pass criteria:**
- All three nodes show `✅` (live hash == replayed hash)
- `hash match=True`
- `consistent=True`
- Phase 4 does not exit with code 1

**Fail indicators:**
- Any `❌` in the hash comparison table
- Output contains `FAIL: Replay hashes do not match`
- Exit code 1

---

**Test ID:** TC-REPLAY-02
**Spec reference:** Phase 7 — Determinism Proof (Proof A)
**REVIEW_PACKET section:** §6 Determinism Proof

**What to verify:**
The same frozen propagation log replayed 5 times must produce identical
consensus hashes every time.

**Expected output (Phase 7, Proof A):**
```
Proof A — 5× replay of frozen propagation log
Run    consensus_hash                               log_hash
────── ──────────────────────────────────────────── ────────────────────
1      <same-64-char-hex>...  <hash>...  ✅
2      <same-64-char-hex>...  <hash>...  ✅
3      <same-64-char-hex>...  <hash>...  ✅
4      <same-64-char-hex>...  <hash>...  ✅
5      <same-64-char-hex>...  <hash>...  ✅

Result : [PASS]  All 5 hashes IDENTICAL
```

**Pass criteria:**
- All 5 runs show the identical `consensus_hash` string
- All 5 `log_hash` values identical
- Result line reads `[PASS]`

**Fail indicators:**
- Any two rows show different `consensus_hash` values
- Result line reads `[FAIL]`

---

### DOMAIN 2 — Divergence Handling

**Test ID:** TC-DIV-01
**Spec reference:** Phase 5 — Divergence + Failure Simulation (Case 3)
**REVIEW_PACKET section:** §5 Failure Cases — Case 3

**What to verify:**
When Node_C does not receive a propagation, the system must halt and report
the missing node. It must NOT silently continue.

**Expected output (Phase 5, Case 3):**
```
┌─ Failure Case 3: Missing Propagation
│  ❌ HALT  : invocation_id=<id>... was NOT delivered to: ['Node_C'].
│             Full consensus requires all nodes.
│             Partial replay state preserved for ['Node_A', 'Node_B'].
│  Action  : Propagation REJECTED. Replay state preserved.
└──────────────────────────────────────────────────────────────
→ PropagationFailure (expected): Missing propagation to ['Node_C']...
```

**Pass criteria:**
- `❌ HALT` is printed before exception
- `['Node_C']` identified as missing
- `PropagationFailure` raised (caught by runner — marked EXPECTED)
- `failure_outcomes["missing_propagation"]` == `"HALTED"`

**Fail indicators:**
- Missing propagation is accepted silently (no HALT output)
- `UNEXPECTED_PASS` appears in failure summary

---

**Test ID:** TC-DIV-02
**Spec reference:** Phase 6 — Observability Layer
**REVIEW_PACKET section:** §7 Observability Output — Divergence Detection

**What to verify:**
After clean propagation (all 3 nodes receive all 3 envelopes), divergence
detection must confirm zero divergence.

**Expected output (Phase 6):**
```
┌── Divergence Detection ─────────────────────────────────────┐
│  Node_B invocations : ['<id12>...', '<id12>...', '<id12>...']
│  Node_C invocations : ['<id12>...', '<id12>...', '<id12>...']
│  Divergence         : ✅ NONE — nodes consistent
└──────────────────────────────────────────────────────────────┘
```

**Pass criteria:**
- Node_B and Node_C invocation lists are identical
- `Divergence : ✅ NONE` appears

---

### DOMAIN 3 — Propagation Determinism

**Test ID:** TC-DET-01
**Spec reference:** Phase 7 — Determinism Proof (Proof B)
**REVIEW_PACKET section:** §6 Determinism Proof — Proof B

**What to verify:**
Shuffling the propagation log (changing entry order) and replaying it must
still produce the same consensus hash as the canonical (unshuffled) replay.
This proves the causal sort is the sole ordering mechanism.

**Expected output (Phase 7, Proof B):**
```
Proof B — shuffle log order 3×, replay each, verify same consensus
Trial   shuffled_input_order           converged
─────── ────────────────────────────── ─────────
1       seqs=[3, 1, 2]...              ✅ YES
2       seqs=[2, 3, 1]...              ✅ YES
3       seqs=[1, 3, 2]...              ✅ YES

Result : [PASS]  All shuffled replays converge to canonical
```

**Pass criteria:**
- All 3 shuffle trials show `✅ YES`
- Result reads `[PASS]`

**Fail indicators:**
- Any trial shows `❌ NO — DIVERGED`
- Result reads `[FAIL]`

---

**Test ID:** TC-DET-02
**Spec reference:** Phase 1 — QApp Invocation Envelope
**REVIEW_PACKET section:** §2 QApp Invocation Flow

**What to verify:**
Running the same `QAppExecutionEnvelope.create()` call twice must produce
identical envelopes. No randomness. No wall-clock timestamp.

**Test procedure (manual, in Python REPL or test script):**
```python
from envelope import QAppExecutionEnvelope

args = dict(
    qapp_id="bhiv.test.v1",
    node_origin="Node_A",
    payload={"x": 1},
    sequence_id=1,
    contract_version="qapp-v1.0",
)
e1 = QAppExecutionEnvelope.create(**args)
e2 = QAppExecutionEnvelope.create(**args)

assert e1.to_dict() == e2.to_dict(), "FAIL: envelopes differ"
print("PASS: envelopes identical")
```

**Pass criteria:**
- `e1.to_dict() == e2.to_dict()` is True
- No exception

---

### DOMAIN 4 — Hash Agreement

**Test ID:** TC-HASH-01
**Spec reference:** Phase 6 — Observability Layer
**REVIEW_PACKET section:** §7 Observability Output — Final Consensus Hash

**What to verify:**
The consensus hash and log hash are present, non-empty, and 64 hex characters
(full SHA-256).

**Expected output (Phase 6):**
```
┌── Final Consensus Hash ─────────────────────────────────────┐
│  consensus : <64-hex-chars>
│  log_hash  : <64-hex-chars>
└──────────────────────────────────────────────────────────────┘
```

**Pass criteria:**
- `consensus` value is a 64-character lowercase hex string
- `log_hash` value is a 64-character lowercase hex string
- Both values are identical across two consecutive full runs of `run_distributed_qapp.py`

**How to verify across runs:**
```bash
python run_distributed_qapp.py 2>&1 | grep "consensus :"
python run_distributed_qapp.py 2>&1 | grep "consensus :"
# Both lines must be identical
```

---

**Test ID:** TC-HASH-02
**Spec reference:** Phase 4 + Phase 7
**REVIEW_PACKET section:** §4 Replay Reconstruction, §6 Determinism Proof

**What to verify:**
The consensus hash produced by Phase 4 replay, Phase 6 observability, and
Phase 7 Proof A must all be identical.

**Test procedure:**
```bash
python run_distributed_qapp.py 2>&1 | grep -E "(consensus|consensus_hash)" | head -20
```

**Pass criteria:**
- Phase 4 `consensus=` value matches Phase 6 `consensus :` value
- All 5 Phase 7 Proof A `consensus_hash` values match

---

### DOMAIN 5 — Failure Isolation

**Test ID:** TC-FAIL-01
**Spec reference:** Phase 5 — all 4 cases
**REVIEW_PACKET section:** §5 Failure Cases

**What to verify:**
All 4 failure cases are detected and handled. None silently passes.

**Expected output (Phase 5 summary):**
```
Failure simulation summary:
  ✅  delayed_propagation         : DELAYED
  ✅  duplicate_propagation       : REJECTED
  ✅  missing_propagation         : HALTED
  ✅  out_of_order_sequence       : HALTED

✅  All 4 failure cases detected and handled correctly  |  no silent recovery
```

**Pass criteria:**
- `delayed_propagation` → `DELAYED` (accepted with flag, not exception)
- `duplicate_propagation` → `REJECTED`
- `missing_propagation` → `HALTED`
- `out_of_order_sequence` → `HALTED`
- No `UNEXPECTED_PASS` anywhere in output

---

**Test ID:** TC-FAIL-02
**Spec reference:** Phase 5 — Case 2 (Duplicate)
**REVIEW_PACKET section:** §5 Failure Cases — Case 2

**What to verify:**
After a duplicate is rejected, the propagation log is unchanged.
Valid replay state must be preserved.

**Pass criteria:**
- `PropagationFailure` raised before any log append
- Phase 4 replay hash still matches live node state after Phase 5

---

**Test ID:** TC-FAIL-03
**Spec reference:** Phase 5 — Case 1 (Delayed)
**REVIEW_PACKET section:** §5 Failure Cases — Case 1

**What to verify:**
Delayed propagation is NOT rejected. It is accepted with a `CAUSAL_DELAY` flag.
Delayed-but-valid data must never be silently dropped.

**Expected output (Phase 5, Case 1):**
```
┌─ Failure Case 1: Delayed Propagation
│  ⚠️  FLAG  : seq=10 arrived after seq=3. Gap=6 steps (threshold=3).
│             Accepted with flag=CAUSAL_DELAY.
│  Action  : Accepted (with flag).
└──────────────────────────────────────────────────────────────
→ status=DELAYED  gap=6  flag=CAUSAL_DELAY
```

**Pass criteria:**
- Status is `DELAYED`, not `REJECTED`
- `CAUSAL_DELAY` flag present
- No `PropagationFailure` raised

---

### DOMAIN 6 — Observability Correctness

**Test ID:** TC-OBS-01
**Spec reference:** Phase 6 — Observability Layer
**REVIEW_PACKET section:** §7 Observability Output

**What to verify:**
All 5 required observability outputs are present in Phase 6 console output.

**Required blocks to verify:**

| # | Block name | Verify presence of |
|---|---|---|
| 1 | Propagation Chain | `seq=1`, `seq=2`, `seq=3`, `Node_A → Node_B`, `Node_A → Node_C` |
| 2 | Node Replay Status | `Node_A`, `Node_B`, `Node_C`, `recv=`, `hash=` |
| 3 | Divergence Detection | `Divergence`, `✅ NONE` or `❌ YES — ALERT` |
| 4 | Replay Verification | `consistent : ✅ YES` |
| 5 | Final Consensus Hash | `consensus :`, `log_hash :` — both 64 hex chars |

**Test procedure:**
```bash
python run_distributed_qapp.py 2>&1 | grep -E "(seq=|Node_A|Node_B|Node_C|Divergence|consistent|consensus)"
```

**Pass criteria:**
- All 5 block headers present in output
- All required sub-fields visible
- No block is missing or empty

---

**Test ID:** TC-OBS-02
**Spec reference:** Phase 2 + Phase 6
**REVIEW_PACKET section:** §3 Distributed Propagation Flow

**What to verify:**
After propagation, each node shows `received_count = 3` (one per envelope).
Node_A shows `propagated_count = 6` (two per envelope: once to B, once to C).
Node_B and Node_C show `propagated_count = 0`.

**Expected values in Phase 6 Node Replay Status:**
```
Node_A   recv= 3  propagated= 6  ...
Node_B   recv= 3  propagated= 0  ...
Node_C   recv= 3  propagated= 0  ...
```

**Pass criteria:**
- `Node_A recv=3`, `Node_A propagated=6`
- `Node_B recv=3`, `Node_B propagated=0`
- `Node_C recv=3`, `Node_C propagated=0`

---

## Final Verdict Form

To be completed by Vinayak (Testing Department):

```
Tester          : ________________________
Date tested     : ________________________
Python version  : ________________________
Run command     : python run_distributed_qapp.py
Exit code       : ____  (expected: 0)

Domain results:

  DOMAIN 1  Replay Consistency          PASS / FAIL
  DOMAIN 2  Divergence Handling         PASS / FAIL
  DOMAIN 3  Propagation Determinism     PASS / FAIL
  DOMAIN 4  Hash Agreement              PASS / FAIL
  DOMAIN 5  Failure Isolation           PASS / FAIL
  DOMAIN 6  Observability Correctness   PASS / FAIL

Test case results:

  TC-REPLAY-01    PASS / FAIL
  TC-REPLAY-02    PASS / FAIL
  TC-DIV-01       PASS / FAIL
  TC-DIV-02       PASS / FAIL
  TC-DET-01       PASS / FAIL
  TC-DET-02       PASS / FAIL
  TC-HASH-01      PASS / FAIL
  TC-HASH-02      PASS / FAIL
  TC-FAIL-01      PASS / FAIL
  TC-FAIL-02      PASS / FAIL
  TC-FAIL-03      PASS / FAIL
  TC-OBS-01       PASS / FAIL
  TC-OBS-02       PASS / FAIL

Overall verdict  :  PASS / FAIL

Notes / observations:
_______________________________________________________________
_______________________________________________________________
```

---

*BHIV Universal Testing Protocol v2 | Marine Intelligence System | May 2026*
