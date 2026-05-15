# Marine Corrosion QApp — Architectural Contract Specification

**Version:** 1.0.0  
**Status:** Production  
**Owner:** BHIV Quantum Execution Infrastructure  
**Boundary:** Quantum Execution Layer ↔ Kanishk's Deterministic Execution Layer

---

## 1. Purpose

This document defines the **strict boundary contracts** governing all data exchanges between the Marine Corrosion QApp quantum execution layer and the classical Deterministic Execution Layer (DEL). It is the authoritative specification for integration engineers, quantum application developers (QApps), and system reviewers.

No data crosses this boundary without conforming to the schemas and transformation rules defined herein.

---

## 2. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Upstream Classical System                  │
│         (Environmental Monitoring Station / Sensor API)     │
└──────────────────────────┬──────────────────────────────────┘
                           │  JSON Payload (CorrosionInput)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               Quantum Execution Layer (QEL)                 │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  schema.py  │──▶│ algorithm.py │──▶│  execution.py    │  │
│  │  Validation │   │ Circuit Build│   │  Aer Simulation  │  │
│  └─────────────┘   └──────────────┘   └────────┬─────────┘  │
│                                                │            │
│                           Raw Shot Distribution│            │
│                           Dict[str, int]        │            │
│                                                ▼            │
│                                    Post-Processing          │
│                                    (entropy, Hamming,       │
│                                     physical modulation)    │
└──────────────────────────┬──────────────────────────────────┘
                           │  Structured JSON (CorrosionOutput)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          Deterministic Execution Layer (DEL)                │
│                  (Kanishk's System)                         │
│                                                             │
│  Consumes: degradation_probability, confidence_score,       │
│            recommended_anode_current, risk_level,           │
│            action_required, signal                          │
└──────────────────────────┬──────────────────────────────────┘
                           │  Deterministic Actuator Signal
                           ▼
                  Cathodic Protection System
                  (Anode Current Controller)
```

---

## 3. Input Contract

### 3.1 Serialization Format

- **Transport:** UTF-8 encoded JSON object.
- **Schema Class:** `CorrosionInput` (defined in `schema.py`).
- **Validation:** Pydantic BaseModel with field-level range validators.
- **Rejection policy:** Any field outside its defined range causes an immediate `ValueError`. The pipeline returns an `INPUT_VALIDATION_FAILED` error envelope. No partial execution occurs.

### 3.2 Input Field Registry

| Field | Type | Unit | Range | Required |
|-------|------|------|-------|----------|
| `salinity` | float | ppt | [0, 50] | YES |
| `temperature_celsius` | float | °C | [-5, 45] | YES |
| `pH` | float | — | [0, 14] | YES |
| `material_oxidation_potential` | float | V | [-2.0, 2.0] | YES |
| `dissolved_oxygen_mgl` | float | mg/L | [0, 20] | YES |
| `current_density_mAcm2` | float | mA/cm² | [0, 10] | YES |

### 3.3 Angle Normalization

All input fields are normalized to `[0, π]` before circuit parameterization:

```
θ_field = π × (value - range_min) / (range_max - range_min)
```

This mapping is injective and lossless within the physical bounds.

---

## 4. Output Contract

### 4.1 Serialization Format

- **Transport:** UTF-8 encoded JSON object.
- **Schema Class:** `CorrosionOutput` (defined in `schema.py`).
- **Post-generation validation:** `validate_quantum_contract()` (defined in `execution.py`).

### 4.2 Output Field Registry

| Field | Type | Unit | Range | Description |
|-------|------|------|-------|-------------|
| `degradation_probability` | float | — | [0, 1] | Corrosion risk estimate |
| `confidence_score` | float | — | [0.5, 1] | Statistical confidence |
| `recommended_anode_current` | float | mA | [10, 210] | Cathodic protection target |
| `dominant_state` | str | bit string | len=6 | Most frequent measurement |
| `measurement_distribution` | dict | — | values sum ~1.0 | Full shot probability map |
| `shots_used` | int | — | ≥ 512 | Shot count for traceability |

### 4.3 Deterministic Event Fields (added by run_quantum_pipeline.py)

| Field | Type | Values | Consumer |
|-------|------|--------|----------|
| `risk_level` | str | LOW / MODERATE / ELEVATED / CRITICAL | DEL routing |
| `action_required` | bool | true / false | DEL actuation gate |
| `signal` | str | HOLD / INCREASE_ANODE_CURRENT | Actuator command |
| `confidence` | float | [0, 1] | DEL confidence gate |

---

## 5. Statistical Shot Data → Fixed System Signal Transformation

### 5.1 The Quantum-Classical Gap

Raw quantum output is **probabilistic**: the simulator produces a distribution over 2^6 = 64 possible bit strings. Two identical physical situations with different seeds will produce slightly different distributions. This raw stochasticity **cannot directly drive actuators**.

### 5.2 Transformation Pipeline

```
Raw Counts:  {"101010": 1720, "010101": 1274, ...}
                        ↓
Normalize:   {"101010": 0.420, "010101": 0.311, ...}  [sums to 1.0]
                        ↓
Hamming Weighting:  P_deg = Σ(P(state) × HammingWeight(state) / n_qubits)
                        ↓
Physical Modulation: combine with oxidation_factor, salinity_factor, oxygen_factor
                        ↓
degradation_probability ∈ [0, 1]  (single deterministic float)
                        ↓
Threshold Mapping:   risk_level ∈ {LOW, MODERATE, ELEVATED, CRITICAL}
                        ↓
Boolean Gate:        action_required ∈ {true, false}
                        ↓
Actuator Signal:     signal ∈ {HOLD, INCREASE_ANODE_CURRENT}
```

### 5.3 Why the Wrapping is Mandatory

1. **Actuators require discrete commands.** A continuous probability cannot be directly sent to a relay or current controller.
2. **Quantum measurements contain shot noise.** With finite shots, sampling error introduces variance. Post-processing collapses this into a point estimate with a traceable confidence score.
3. **Auditability.** The deterministic transformation is rule-based (engineered thresholds), not learned — making it explainable and certifiable.
4. **Safety.** If `confidence_score < 0.5`, the contract is violated and no signal is emitted — failing safe rather than failing open.

---

## 6. Contract Validation Rules

Enforced by `validate_quantum_contract()`:

| Rule | Field | Condition | Failure Action |
|------|-------|-----------|---------------|
| R1 | All required keys | Present in result dict | REJECT |
| R2 | `degradation_probability` | ∈ [0, 1] | REJECT |
| R3 | `confidence_score` | ∈ [0, 1] | REJECT |
| R4 | `confidence_score` | ≥ 0.5 | REJECT |
| R5 | `recommended_anode_current` | ≥ 0.0 | REJECT |
| R6 | `shots_used` | ≥ 512 | REJECT |
| R7 | `measurement_distribution` | sums to ~1.0 (±0.01) | REJECT |
| R8 | `dominant_state` | non-empty str | REJECT |

---

## 7. Determinism Guarantee

The following seeded components guarantee `same seed → same output`:

| Component | Seed Parameter |
|-----------|---------------|
| `AerSimulator` | `seed_simulator=seed` |
| `transpile()` | `seed_transpiler=seed` |
| `simulator.run()` | `seed_simulator=seed` |

No random state is accessed outside these calls. The circuit construction is purely deterministic (no internal RNG).

---

## 8. Versioning Policy

- Input/output schema changes that remove fields or narrow ranges are **breaking changes** and require a major version bump.
- Adding optional fields with defaults is a **non-breaking change**.
- Threshold value changes in `validate_quantum_contract` or `_build_deterministic_event` are **breaking changes** if they alter actuator signal logic.

---

*End of Contract Specification*
