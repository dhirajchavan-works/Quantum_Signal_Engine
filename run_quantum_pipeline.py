"""
run_quantum_pipeline.py
-----------------------
Production-grade entry point for the BHIV Quantum Execution Pipeline.

Pipeline Flow:
  Input Parameters → Quantum Circuit Generation → Simulator Execution
  → Measured Output → Structured Result → Deterministic Event

Usage:
  python run_quantum_pipeline.py
  python run_quantum_pipeline.py --seed 42
"""

import json
import time
import argparse
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Local QApp imports
# ---------------------------------------------------------------------------
from qapps.marine_corrosion_qapp.schema import CorrosionInput, CorrosionOutput
from qapps.marine_corrosion_qapp.execution import run_corrosion_qapp, validate_quantum_contract


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(input_params: dict, seed: int = 42, shots: int = 4096) -> dict:
    """
    Execute the full quantum pipeline end-to-end.

    Parameters
    ----------
    input_params : dict
        Raw dictionary matching CorrosionInput schema.
    seed : int
        RNG seed for deterministic simulation.
    shots : int
        Number of simulator measurement shots.

    Returns
    -------
    dict
        Fully structured pipeline result envelope.
    """
    pipeline_start = time.perf_counter()
    run_id = f"BHIV-QP-{int(time.time())}"

    print(f"[{datetime.now(timezone.utc).isoformat()}] Pipeline START  run_id={run_id}")
    print(f"  seed={seed}  shots={shots}")
    print(f"  input={json.dumps(input_params, indent=2)}")

    # ------------------------------------------------------------------
    # Stage 1 – Input Validation
    # ------------------------------------------------------------------
    stage_t = time.perf_counter()
    try:
        validated_input = CorrosionInput(**input_params)
    except Exception as exc:
        return _error_envelope(run_id, "INPUT_VALIDATION_FAILED", str(exc))

    stage_1_ms = (time.perf_counter() - stage_t) * 1000
    print(f"  [Stage 1] Input validated in {stage_1_ms:.2f} ms")

    # ------------------------------------------------------------------
    # Stage 2 – Quantum Circuit Generation + Execution
    # ------------------------------------------------------------------
    stage_t = time.perf_counter()
    try:
        raw_result = run_corrosion_qapp(
            corrosion_input=validated_input,
            seed=seed,
            shots=shots,
        )
    except Exception as exc:
        return _error_envelope(run_id, "QUANTUM_EXECUTION_FAILED", str(exc))

    stage_2_ms = (time.perf_counter() - stage_t) * 1000
    print(f"  [Stage 2] Quantum execution completed in {stage_2_ms:.2f} ms")

    # ------------------------------------------------------------------
    # Stage 3 – Contract Validation
    # ------------------------------------------------------------------
    stage_t = time.perf_counter()
    if not validate_quantum_contract(raw_result):
        return _error_envelope(run_id, "CONTRACT_VIOLATION", "Output failed quantum contract validation")

    stage_3_ms = (time.perf_counter() - stage_t) * 1000
    print(f"  [Stage 3] Contract validated in {stage_3_ms:.2f} ms")

    # ------------------------------------------------------------------
    # Stage 4 – Structured Output Mapping
    # ------------------------------------------------------------------
    stage_t = time.perf_counter()
    try:
        output = CorrosionOutput(
            degradation_probability=raw_result["degradation_probability"],
            confidence_score=raw_result["confidence_score"],
            recommended_anode_current=raw_result["recommended_anode_current"],
            dominant_state=raw_result["dominant_state"],
            measurement_distribution=raw_result["measurement_distribution"],
            shots_used=raw_result["shots_used"],
        )
    except Exception as exc:
        return _error_envelope(run_id, "OUTPUT_MAPPING_FAILED", str(exc))

    stage_4_ms = (time.perf_counter() - stage_t) * 1000
    print(f"  [Stage 4] Output structured in {stage_4_ms:.2f} ms")

    total_ms = (time.perf_counter() - pipeline_start) * 1000

    envelope = {
        "run_id": run_id,
        "status": "SUCCESS",
        "seed": seed,
        "shots": shots,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "execution_time_ms": round(total_ms, 3),
        "stage_times_ms": {
            "input_validation": round(stage_1_ms, 3),
            "quantum_execution": round(stage_2_ms, 3),
            "contract_validation": round(stage_3_ms, 3),
            "output_mapping": round(stage_4_ms, 3),
        },
        "input": input_params,
        "output": output.dict(),
        "deterministic_event": _build_deterministic_event(output),
    }

    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Pipeline COMPLETE  run_id={run_id}")
    print(f"  total_time={total_ms:.2f} ms")
    print(f"\n=== RESULT ===\n{json.dumps(envelope, indent=2)}")
    return envelope


def _build_deterministic_event(output: CorrosionOutput) -> dict:
    """
    Translate probabilistic quantum output into a fixed, immutable system signal.
    Thresholds are engineering constants – not derived from runtime state.
    """
    risk_level = "LOW"
    if output.degradation_probability >= 0.7:
        risk_level = "CRITICAL"
    elif output.degradation_probability >= 0.4:
        risk_level = "ELEVATED"
    elif output.degradation_probability >= 0.2:
        risk_level = "MODERATE"

    action_required = risk_level in ("ELEVATED", "CRITICAL")

    return {
        "event_type": "CORROSION_RISK_ASSESSMENT",
        "risk_level": risk_level,
        "action_required": action_required,
        "signal": "INCREASE_ANODE_CURRENT" if action_required else "HOLD",
        "recommended_anode_current_mA": output.recommended_anode_current,
        "confidence": output.confidence_score,
    }


def _error_envelope(run_id: str, error_code: str, detail: str) -> dict:
    return {
        "run_id": run_id,
        "status": "FAILED",
        "error_code": error_code,
        "detail": detail,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="BHIV Quantum Execution Pipeline – Marine Corrosion QApp"
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument("--shots", type=int, default=4096, help="Simulator shot count (default: 4096)")
    parser.add_argument(
        "--input-json",
        type=str,
        default=None,
        help="Path to JSON file with CorrosionInput parameters. Uses built-in demo if omitted.",
    )
    args = parser.parse_args()

    if args.input_json:
        with open(args.input_json, "r") as fh:
            input_params = json.load(fh)
    else:
        # Deterministic demo payload
        input_params = {
            "salinity": 35.2,
            "temperature_celsius": 18.5,
            "pH": 7.8,
            "material_oxidation_potential": 0.44,
            "dissolved_oxygen_mgl": 6.5,
            "current_density_mAcm2": 0.12,
        }

    result = run_pipeline(input_params=input_params, seed=args.seed, shots=args.shots)
    sys.exit(0 if result.get("status") == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
