"""
execution.py
------------
Runtime wrapper for the Marine Corrosion QApp.

Responsibilities:
  1. Accept a validated CorrosionInput object.
  2. Build the quantum circuit via algorithm.py.
  3. Execute on the local AerSimulator with a fixed seed.
  4. Post-process raw shot counts into Corrosion Intelligence metrics.
  5. Validate output against the quantum contract.
  6. Return a structured result dictionary.

No cloud dependencies. All simulation is local (qiskit-aer).
"""

from __future__ import annotations

import math
from typing import Dict, Any

from qiskit_aer import AerSimulator

from .schema import CorrosionInput
from .algorithm import build_corrosion_circuit, circuit_summary

# ---------------------------------------------------------------------------
# Contract thresholds (engineering constants – not runtime-derived)
# ---------------------------------------------------------------------------

_MIN_CONFIDENCE = 0.5          # Reject outputs with confidence below this
_MAX_DEGRADATION_PROB = 1.0    # Sanity upper bound
_MIN_SHOTS_REQUIRED = 512      # Minimum meaningful shot count
_ANODE_BASELINE_MA = 10.0      # Baseline anode current (mA) at zero risk
_ANODE_SCALE_MA = 200.0        # Maximum additional anode current (mA) at full risk


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_corrosion_qapp(
    corrosion_input: CorrosionInput,
    seed: int = 42,
    shots: int = 4096,
) -> Dict[str, Any]:
    """
    Execute the marine corrosion quantum assessment pipeline.

    Parameters
    ----------
    corrosion_input : CorrosionInput
        Validated environmental parameter object.
    seed : int
        Simulator RNG seed — controls all randomness for determinism.
    shots : int
        Number of measurement shots. Must be >= 512.

    Returns
    -------
    dict
        Raw result dictionary ready for CorrosionOutput instantiation.

    Raises
    ------
    ValueError
        If inputs are out-of-spec or execution fails contract validation.
    RuntimeError
        If the simulator raises an unexpected error.
    """
    if shots < _MIN_SHOTS_REQUIRED:
        raise ValueError(
            f"shots={shots} is below the minimum required ({_MIN_SHOTS_REQUIRED}). "
            "Insufficient shots produce unreliable distributions."
        )

    # ------------------------------------------------------------------
    # Step 1 – Normalize inputs to circuit angles
    # ------------------------------------------------------------------
    normalized = corrosion_input.to_normalized()

    # ------------------------------------------------------------------
    # Step 2 – Build quantum circuit
    # ------------------------------------------------------------------
    circuit = build_corrosion_circuit(normalized)
    summary = circuit_summary(circuit)

    # ------------------------------------------------------------------
    # Step 3 – Execute on local AerSimulator (deterministic seed)
    # ------------------------------------------------------------------
    simulator = AerSimulator(method="statevector", seed_simulator=seed)

    try:
        from qiskit import transpile
        transpiled = transpile(circuit, simulator, seed_transpiler=seed)
        job = simulator.run(transpiled, shots=shots, seed_simulator=seed)
        result = job.result()
    except Exception as exc:
        raise RuntimeError(f"AerSimulator execution failed: {exc}") from exc

    raw_counts: Dict[str, int] = result.get_counts()

    # ------------------------------------------------------------------
    # Step 4 – Post-process shot distribution
    # ------------------------------------------------------------------
    measurement_distribution = _normalize_counts(raw_counts, shots)
    dominant_state = max(raw_counts, key=raw_counts.get)
    dominant_freq = raw_counts[dominant_state] / shots

    # ------------------------------------------------------------------
    # Step 5 – Derive Corrosion Intelligence metrics
    # ------------------------------------------------------------------
    degradation_probability = _compute_degradation_probability(
        measurement_distribution=measurement_distribution,
        normalized_angles=normalized,
    )
    confidence_score = _compute_confidence(measurement_distribution, shots)
    recommended_anode_current = _compute_anode_current(degradation_probability)

    # ------------------------------------------------------------------
    # Step 6 – Assemble result dict
    # ------------------------------------------------------------------
    result_dict: Dict[str, Any] = {
        "degradation_probability": round(degradation_probability, 6),
        "confidence_score": round(confidence_score, 6),
        "recommended_anode_current": round(recommended_anode_current, 4),
        "dominant_state": dominant_state,
        "dominant_state_frequency": round(dominant_freq, 6),
        "measurement_distribution": {
            k: round(v, 6) for k, v in measurement_distribution.items()
        },
        "shots_used": shots,
        "circuit_summary": summary,
        "seed": seed,
    }

    return result_dict


def validate_quantum_contract(result: dict) -> bool:
    """
    Validate that a result dictionary satisfies all quantum contract rules.

    Rules enforced:
      R1  – Required keys are present.
      R2  – degradation_probability ∈ [0, 1].
      R3  – confidence_score ∈ [0, 1].
      R4  – confidence_score >= _MIN_CONFIDENCE.
      R5  – recommended_anode_current >= 0.
      R6  – shots_used >= _MIN_SHOTS_REQUIRED.
      R7  – measurement_distribution values sum to ~1.0 (±0.01 tolerance).
      R8  – dominant_state is a non-empty bit string.

    Parameters
    ----------
    result : dict
        Output dictionary from run_corrosion_qapp.

    Returns
    -------
    bool
        True if all rules pass; False otherwise (with stderr logging).
    """
    import sys

    required_keys = {
        "degradation_probability",
        "confidence_score",
        "recommended_anode_current",
        "dominant_state",
        "measurement_distribution",
        "shots_used",
    }

    # R1
    missing = required_keys - set(result.keys())
    if missing:
        print(f"CONTRACT VIOLATION R1: Missing keys {missing}", file=sys.stderr)
        return False

    dp = result["degradation_probability"]
    cs = result["confidence_score"]
    ac = result["recommended_anode_current"]
    ds = result["dominant_state"]
    md = result["measurement_distribution"]
    su = result["shots_used"]

    # R2
    if not (0.0 <= dp <= _MAX_DEGRADATION_PROB):
        print(f"CONTRACT VIOLATION R2: degradation_probability={dp} out of [0,1]", file=sys.stderr)
        return False

    # R3
    if not (0.0 <= cs <= 1.0):
        print(f"CONTRACT VIOLATION R3: confidence_score={cs} out of [0,1]", file=sys.stderr)
        return False

    # R4
    if cs < _MIN_CONFIDENCE:
        print(
            f"CONTRACT VIOLATION R4: confidence_score={cs} below minimum threshold {_MIN_CONFIDENCE}",
            file=sys.stderr,
        )
        return False

    # R5
    if ac < 0.0:
        print(f"CONTRACT VIOLATION R5: recommended_anode_current={ac} is negative", file=sys.stderr)
        return False

    # R6
    if su < _MIN_SHOTS_REQUIRED:
        print(f"CONTRACT VIOLATION R6: shots_used={su} below minimum {_MIN_SHOTS_REQUIRED}", file=sys.stderr)
        return False

    # R7
    total_prob = sum(md.values())
    if not (0.99 <= total_prob <= 1.01):
        print(
            f"CONTRACT VIOLATION R7: measurement_distribution sums to {total_prob:.4f}, expected ~1.0",
            file=sys.stderr,
        )
        return False

    # R8
    if not isinstance(ds, str) or len(ds) == 0:
        print(f"CONTRACT VIOLATION R8: dominant_state is invalid: {ds!r}", file=sys.stderr)
        return False

    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize_counts(raw_counts: Dict[str, int], shots: int) -> Dict[str, float]:
    """Convert raw integer shot counts to normalized float probabilities."""
    return {state: count / shots for state, count in sorted(raw_counts.items())}


def _compute_degradation_probability(
    measurement_distribution: Dict[str, float],
    normalized_angles: Dict[str, float],
) -> float:
    """
    Estimate degradation probability from the quantum shot distribution.

    Method:
      - Bit strings with more '1' bits represent higher-energy corrosion states.
      - We weight each state's probability by its Hamming weight (number of 1-bits)
        divided by the total qubit count, then sum to get a weighted risk score.
      - This is modulated by the physical oxidation potential and salinity angles,
        the two dominant electrochemical drivers.

    The result is clipped to [0, 1].
    """
    num_qubits = len(next(iter(measurement_distribution)))
    hamming_weighted = 0.0
    for state, prob in measurement_distribution.items():
        hamming_weight = state.count("1") / num_qubits
        hamming_weighted += prob * hamming_weight

    # Physical modulation: high oxidation potential and high salinity → higher risk
    oxidation_factor = normalized_angles["theta_oxidation"] / math.pi
    salinity_factor = normalized_angles["theta_salinity"] / math.pi
    oxygen_factor = normalized_angles["theta_oxygen"] / math.pi

    # Weighted combination: 60% quantum signal, 40% physical scaling
    physical_risk = (0.5 * oxidation_factor + 0.3 * salinity_factor + 0.2 * oxygen_factor)
    combined = 0.60 * hamming_weighted + 0.40 * physical_risk

    return max(0.0, min(1.0, combined))


def _compute_confidence(
    measurement_distribution: Dict[str, float],
    shots: int,
) -> float:
    """
    Compute confidence from shot distribution entropy (information-theoretic).

    A uniform distribution over all 2^n states = maximum entropy = minimum confidence.
    A peaked distribution (one dominant state) = minimum entropy = maximum confidence.

    Confidence = 1 - (H / H_max), normalized to [0, 1].
    Also penalises low shot counts via a shot factor.
    """
    probs = list(measurement_distribution.values())
    entropy = -sum(p * math.log2(p) for p in probs if p > 0.0)
    num_states = 2 ** len(next(iter(measurement_distribution)))
    h_max = math.log2(num_states)
    normalized_entropy = entropy / h_max if h_max > 0 else 0.0
    raw_confidence = 1.0 - normalized_entropy

    # Shot count penalty: confidence saturates above 8192 shots
    shot_factor = min(1.0, math.log2(shots + 1) / math.log2(8193))
    confidence = raw_confidence * shot_factor

    return max(0.0, min(1.0, confidence))


def _compute_anode_current(degradation_probability: float) -> float:
    """
    Translate degradation probability into a concrete anode current recommendation (mA).

    Formula: I_anode = I_baseline + I_scale * P_degradation
    This is a linear engineering model; non-linear models can replace it
    once empirical corrosion data is integrated.
    """
    return _ANODE_BASELINE_MA + _ANODE_SCALE_MA * degradation_probability
