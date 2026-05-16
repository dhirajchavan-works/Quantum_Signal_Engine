from dataclasses import dataclass
import hashlib

@dataclass(frozen=True)
class QAppExecutionEnvelope:
    trace_id: str
    qapp_id: str
    node_origin: str
    invocation_id: str
    payload_hash: str
    sequence_id: int
    timestamp: int
    contract_version: str

class QAppNode:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.received_invocations = {}
        self.replay_log = []
        self.execution_hash = hashlib.sha256(node_id.encode()).hexdigest()
        self.propagated_events = []

    def log_and_compute(self, envelope: QAppExecutionEnvelope):
        if envelope.invocation_id in self.received_invocations:
            return
        self.received_invocations[envelope.invocation_id] = envelope
        self.replay_log.append(envelope)
        mixed = f"{self.execution_hash}:{envelope.payload_hash}:{envelope.sequence_id}"
        self.execution_hash = hashlib.sha256(mixed.encode()).hexdigest()

class PropagationEngine:
    def __init__(self, nodes: dict):
        self.nodes = nodes

    def propagate(self, envelope: QAppExecutionEnvelope, path_log: list):
        path_log.append(envelope.node_origin)
        for target_id in ["Node_B", "Node_C"]:
            if envelope.node_origin == "Node_A":
                self.nodes[target_id].log_and_compute(envelope)
                self.nodes[target_id].propagated_events.append((envelope.sequence_id, path_log.copy()))
