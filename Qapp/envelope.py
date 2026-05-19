"""
envelope.py — QAppExecutionEnvelope

Fully deterministic execution envelope for the Marine Intelligence
distributed quantum pipeline. No datetime.now(), no randomness.
All IDs derived via SHA-256 of inputs.
"""

import hashlib
import json
from dataclasses import dataclass


def _sha256_hex(*parts: str) -> str:
    """Deterministic SHA-256 over concatenated string parts."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class QAppExecutionEnvelope:
    trace_id: str          # SHA-256(qapp_id + node_origin + contract_version)
    qapp_id: str           # Unique QApp identifier (caller-supplied, stable)
    node_origin: str       # Originating node name
    invocation_id: str     # SHA-256(qapp_id + node_origin + sequence_id)
    payload_hash: str      # SHA-256 of the serialised payload dict
    sequence_id: int       # Monotonically increasing causal counter
    timestamp: str         # Deterministic timestamp: "seq-<sequence_id>"
    contract_version: str  # Semantic version string for the QApp contract

    @staticmethod
    def create(
        qapp_id: str,
        node_origin: str,
        payload: dict,
        sequence_id: int,
        contract_version: str,
    ) -> "QAppExecutionEnvelope":
        """
        Factory — all fields computed deterministically from inputs.

        Parameters
        ----------
        qapp_id          : stable QApp identifier
        node_origin      : name of the originating node
        payload          : arbitrary dict; hashed but never stored raw
        sequence_id      : caller-managed monotonic counter (causal order)
        contract_version : semver string
        """
        payload_hash = _sha256_hex(json.dumps(payload, sort_keys=True))
        trace_id = _sha256_hex(qapp_id, node_origin, contract_version)
        invocation_id = _sha256_hex(qapp_id, node_origin, str(sequence_id))
        timestamp = f"seq-{sequence_id}"

        return QAppExecutionEnvelope(
            trace_id=trace_id,
            qapp_id=qapp_id,
            node_origin=node_origin,
            invocation_id=invocation_id,
            payload_hash=payload_hash,
            sequence_id=sequence_id,
            timestamp=timestamp,
            contract_version=contract_version,
        )

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for replay logs and hashing)."""
        return {
            "trace_id": self.trace_id,
            "qapp_id": self.qapp_id,
            "node_origin": self.node_origin,
            "invocation_id": self.invocation_id,
            "payload_hash": self.payload_hash,
            "sequence_id": self.sequence_id,
            "timestamp": self.timestamp,
            "contract_version": self.contract_version,
        }

    def envelope_hash(self) -> str:
        """SHA-256 fingerprint of the entire envelope (deterministic)."""
        return _sha256_hex(json.dumps(self.to_dict(), sort_keys=True))
