"""
algorithm.py
------------
Parameterized quantum circuit for marine corrosion risk estimation.

Algorithm: Hardware-Efficient Ansatz (HEA) — a shallow parameterized
variational circuit commonly used as a VQE ansatz.

Design rationale:
- 6 qubits correspond to the 6 environmental input parameters.
- Each qubit's rotation angle is derived from a normalized physical measurement.
- Entanglement layers (CX gates) model inter-variable correlations
  (e.g., salinity × dissolved oxygen synergy in electrochemical corrosion).
- Two variational layers deepen the expressibility while staying shallow
  enough for near-term hardware compatibility and fast simulation.

Circuit topology per layer:
  [RY(θ_i)] → [CX chain] → [RZ(θ_i)] → [CX chain]

Final step: full measurement on all 6 qubits.
"""

from __future__ import annotations

import math
from typing import Dict

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


NUM_QUBITS = 6
NUM_LAYERS = 2  # Variational depth


def build_corrosion_circuit(normalized_angles: Dict[str, float]) -> QuantumCircuit:
    """
    Construct the parameterized Hardware-Efficient Ansatz circuit.

    Parameters
    ----------
    normalized_angles : dict
        Keys: theta_salinity, theta_temperature, theta_pH,
              theta_oxidation, theta_oxygen, theta_current.
        Values: float in [0, π].

    Returns
    -------
    QuantumCircuit
        Fully constructed circuit with measurements on all qubits.
    """
    angles = [
        normalized_angles["theta_salinity"],
        normalized_angles["theta_temperature"],
        normalized_angles["theta_pH"],
        normalized_angles["theta_oxidation"],
        normalized_angles["theta_oxygen"],
        normalized_angles["theta_current"],
    ]

    if len(angles) != NUM_QUBITS:
        raise ValueError(
            f"Expected {NUM_QUBITS} angle parameters, received {len(angles)}."
        )

    qr = QuantumRegister(NUM_QUBITS, name="q")
    cr = ClassicalRegister(NUM_QUBITS, name="c")
    circuit = QuantumCircuit(qr, cr)

    # ------------------------------------------------------------------
    # Initial state preparation: Hadamard superposition
    # ------------------------------------------------------------------
    circuit.h(qr)

    # ------------------------------------------------------------------
    # Variational layers
    # ------------------------------------------------------------------
    for layer in range(NUM_LAYERS):
        # Rotation block – angles scaled by layer index to break symmetry
        scale = 1.0 + (layer * 0.5)
        for i, theta in enumerate(angles):
            scaled_theta = (theta * scale) % (2 * math.pi)
            circuit.ry(scaled_theta, qr[i])

        # Cross-coupling: RZ gates modelling pairwise interactions
        # Salinity × DO correlation
        circuit.rz(angles[0] * angles[4], qr[0])
        # Temperature × pH correlation
        circuit.rz(angles[1] * angles[2], qr[1])
        # Oxidation potential × current density correlation
        circuit.rz(angles[3] * angles[5], qr[3])

        # Entanglement block – linear CX chain
        _apply_cx_chain(circuit, qr)

        # Second rotation block (RY)
        for i, theta in enumerate(angles):
            scaled_theta = (theta * scale * 1.3) % (2 * math.pi)
            circuit.ry(scaled_theta, qr[i])

        # Second entanglement block – reversed CX chain for richer entanglement
        _apply_cx_chain_reversed(circuit, qr)

    # ------------------------------------------------------------------
    # Final RY sweep for output expressibility
    # ------------------------------------------------------------------
    for i, theta in enumerate(angles):
        circuit.ry(theta, qr[i])

    # ------------------------------------------------------------------
    # Measurement: all qubits → classical register
    # ------------------------------------------------------------------
    circuit.measure(qr, cr)

    return circuit


def _apply_cx_chain(circuit: QuantumCircuit, qr: QuantumRegister) -> None:
    """Forward linear entanglement: q0→q1→q2→q3→q4→q5."""
    for i in range(NUM_QUBITS - 1):
        circuit.cx(qr[i], qr[i + 1])


def _apply_cx_chain_reversed(circuit: QuantumCircuit, qr: QuantumRegister) -> None:
    """Reversed linear entanglement: q5→q4→q3→q2→q1→q0."""
    for i in range(NUM_QUBITS - 1, 0, -1):
        circuit.cx(qr[i], qr[i - 1])


def circuit_summary(circuit: QuantumCircuit) -> Dict[str, object]:
    """
    Return a lightweight summary dict for logging and audit.
    """
    return {
        "num_qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "gate_counts": dict(circuit.count_ops()),
        "num_parameters": circuit.num_parameters,
    }
