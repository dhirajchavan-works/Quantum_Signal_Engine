# envelope.py
# QAppExecutionEnvelope — immutable execution envelope for distributed QApp propagation.
#
# Rules:
#   no datetime.now()           — timestamp is deterministic from sequence_id
#   no randomness               — all IDs are SHA-256 of deterministic inputs
#   frozen dataclass            — immutable after construction
#   same inputs → same envelope, always

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

# ── Deterministic time anchor ──────────────────────────────────────────────────
_ANCHOR          = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
_STEP_SECONDS    = 60           # each sequence_id step = 60 real seconds
CONTRACT_DEFAULT = "qapp-v1.0"


# ── Hash helpers ───────────────────────────────────────────────────────────────

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_payload_hash(payload: dict) -> str:
    """Canonical JSON → SHA-256.  Sort keys so dict ordering never matters."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256(canonical)


def compute_trace_id(qapp_id: str, node_origin: str, sequence_id: int) -> str:
    """Unique per (qapp, origin-node, sequence).  Ties one causal chain together."""
    return _sha256(f"trace:{qapp_id}:{node_origin}:{sequence_id}")


def compute_invocation_id(trace_id: str, payload_hash: str, sequence_id: int) -> str:
    """Unique per (trace, payload, sequence).  Proves exact payload was invoked."""
    return _sha256(f"invoke:{trace_id}:{payload_hash}:{sequence_id}")


def compute_timestamp(sequence_id: int) -> str:
    """Anchor + (sequence_id × 60 s).  No wall clock. Fully reproducible."""
    ts = _ANCHOR + timedelta(seconds=sequence_id * _STEP_SECONDS)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Envelope ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class QAppExecutionEnvelope:
    """
    Immutable execution envelope produced once per QApp invocation.
    Travels with the event through the entire propagation graph.
    All fields are deterministic — no secret state, nothing hidden.

    Fields
    ------
    trace_id         SHA-256 of (qapp_id, node_origin, sequence_id)
    qapp_id          Human-readable QApp name / identifier
    node_origin      Node that originated this invocation
    invocation_id    SHA-256 of (trace_id, payload_hash, sequence_id)
    payload_hash     SHA-256 of the canonical JSON payload
    sequence_id      Monotonic invocation counter (int >= 1)
    timestamp        ISO-8601 UTC — deterministic from sequence_id
    contract_version Schema version string for downstream validation
    """

    trace_id:         str
    qapp_id:          str
    node_origin:      str
    invocation_id:    str
    payload_hash:     str
    sequence_id:      int
    timestamp:        str
    contract_version: str

    # ── Factory ───────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        qapp_id:          str,
        node_origin:      str,
        payload:          dict,
        sequence_id:      int,
        contract_version: str = CONTRACT_DEFAULT,
    ) -> "QAppExecutionEnvelope":
        """
        Build a fully-formed envelope from raw inputs.
        No defaults that depend on runtime state.
        Same arguments → identical envelope every time.
        """
        payload_hash  = compute_payload_hash(payload)
        trace_id      = compute_trace_id(qapp_id, node_origin, sequence_id)
        invocation_id = compute_invocation_id(trace_id, payload_hash, sequence_id)
        timestamp     = compute_timestamp(sequence_id)

        return cls(
            trace_id         = trace_id,
            qapp_id          = qapp_id,
            node_origin      = node_origin,
            invocation_id    = invocation_id,
            payload_hash     = payload_hash,
            sequence_id      = sequence_id,
            timestamp        = timestamp,
            contract_version = contract_version,
        )

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a plain dict — safe to serialise, log, or pass across layers."""
        return {
            "trace_id":         self.trace_id,
            "qapp_id":          self.qapp_id,
            "node_origin":      self.node_origin,
            "invocation_id":    self.invocation_id,
            "payload_hash":     self.payload_hash,
            "sequence_id":      self.sequence_id,
            "timestamp":        self.timestamp,
            "contract_version": self.contract_version,
        }

    def short(self) -> str:
        """Compact one-line summary for console output."""
        return (
            f"Envelope(seq={self.sequence_id}, "
            f"qapp={self.qapp_id!r}, "
            f"origin={self.node_origin}, "
            f"trace={self.trace_id[:12]}..., "
            f"invoke={self.invocation_id[:12]}...)"
        )
