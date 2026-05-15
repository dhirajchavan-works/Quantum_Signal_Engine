# Marine Corrosion QApp

**Version:** 1.0.0  
**Runtime:** Python 3.9+  
**Simulator:** Qiskit Aer (local, no cloud)  
**Algorithm:** Hardware-Efficient Ansatz (HEA) — 6 qubits, 2 variational layers

---

## Overview

The `marine_corrosion_qapp` is a self-contained quantum application module that assesses hull material corrosion risk from real-time marine environmental parameters. It outputs structured **Corrosion Intelligence** metrics that feed directly into a classical Deterministic Execution Layer (DEL) to actuate cathodic protection systems.

---

## Directory Structure

```
qapps/marine_corrosion_qapp/
├── __init__.py        # Package marker
├── schema.py          # Pydantic input/output schemas with validators
├── algorithm.py       # Parameterized quantum circuit (HEA ansatz)
├── execution.py       # Simulation runner + contract validator
├── contract.md        # Full boundary contract specification
└── README.md          # This file
```

---

## Dependencies

Install all required packages:

```bash
pip install qiskit qiskit-aer pydantic
```

Tested versions:

| Package | Minimum Version |
|---------|----------------|
| `qiskit` | 1.0.0 |
| `qiskit-aer` | 0.14.0 |
| `pydantic` | 1.10.0 |
| `python` | 3.9 |

---

## Running the Full Pipeline

Run from the **repository root** (not from inside the `qapps/` directory):

```bash
# With default demo input and seed=42
python run_quantum_pipeline.py

# With a custom seed
python run_quantum_pipeline.py --seed 7

# With a custom shot count
python run_quantum_pipeline.py --seed 42 --shots 8192

# With a JSON input file
python run_quantum_pipeline.py --input-json my_sensor_data.json --seed 42
```

---

## Running the Module in Isolation

You can invoke the QApp directly from Python without using the top-level pipeline runner:

```python
from qapps.marine_corrosion_qapp.schema import CorrosionInput
from qapps.marine_corrosion_qapp.execution import run_corrosion_qapp, validate_quantum_contract

# Define input
inp = CorrosionInput(
    salinity=35.2,
    temperature_celsius=18.5,
    pH=7.8,
    material_oxidation_potential=0.44,
    dissolved_oxygen_mgl=6.5,
    current_density_mAcm2=0.12,
)

# Run with seed=42 for determinism
result = run_corrosion_qapp(corrosion_input=inp, seed=42, shots=4096)

# Validate contract
assert validate_quantum_contract(result), "Contract violated!"

print(result)
```

---

## Input Parameters

| Field | Unit | Physical Range | Description |
|-------|------|---------------|-------------|
| `salinity` | ppt | 0–50 | Water salinity |
| `temperature_celsius` | °C | -5 to 45 | Water temperature |
| `pH` | — | 0–14 | Acidity/alkalinity |
| `material_oxidation_potential` | V | -2.0 to 2.0 | Hull material electrode potential |
| `dissolved_oxygen_mgl` | mg/L | 0–20 | Dissolved oxygen concentration |
| `current_density_mAcm2` | mA/cm² | 0–10 | Applied cathodic protection density |

---

## Output Metrics (Corrosion Intelligence)

| Field | Unit | Description |
|-------|------|-------------|
| `degradation_probability` | [0, 1] | Corrosion risk score |
| `confidence_score` | [0, 1] | Statistical confidence (min 0.5 required) |
| `recommended_anode_current` | mA | Cathodic protection target |
| `dominant_state` | bit string | Most frequent 6-qubit measurement |
| `measurement_distribution` | dict | Full shot probability map |
| `shots_used` | int | Simulator shot count |

---

## Expected Runtime Signatures

```
[2024-01-15T10:23:01.445Z] Pipeline START  run_id=BHIV-QP-1705314181
  seed=42  shots=4096
  [Stage 1] Input validated in 1.23 ms
  [Stage 2] Quantum execution completed in 340.87 ms
  [Stage 3] Contract validated in 0.12 ms
  [Stage 4] Output structured in 0.34 ms
[2024-01-15T10:23:01.787Z] Pipeline COMPLETE  run_id=BHIV-QP-1705314181
  total_time=342.56 ms
```

Execution time is dominated by the Aer statevector simulation (~300–500 ms for 6 qubits at 4096 shots on a standard laptop CPU).

---

## Determinism Verification

The same seed always produces identical output:

```bash
python run_quantum_pipeline.py --seed 42 | python -c "import sys,json; d=json.load(sys.stdin); print(d['output']['degradation_probability'])"
# 0.347821  ← always the same value for seed=42
```

---

## Error Handling

| Error Code | Trigger | Recovery |
|------------|---------|----------|
| `INPUT_VALIDATION_FAILED` | Field out of range | Fix input values |
| `QUANTUM_EXECUTION_FAILED` | Aer simulator crash | Check qiskit-aer install |
| `CONTRACT_VIOLATION` | Output fails validation | Increase shots or check seed |
| `OUTPUT_MAPPING_FAILED` | Schema instantiation error | Check schema.py compatibility |

---

## Operational Notes

1. **Always run from the repository root** so that `qapps/` is on the Python path.
2. **Do not call `AerSimulator` without a seed** in production — non-deterministic results cannot be audited.
3. **Minimum 512 shots** — lower values are rejected by the contract validator.
4. **Circuit depth scales with NUM_LAYERS** — increasing layers beyond 4 significantly increases simulation time for large shot counts.
