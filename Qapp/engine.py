import hashlib
from core import QAppExecutionEnvelope, QAppNode, PropagationEngine


class SequenceGapError(Exception):
    pass


class CorruptedHashError(Exception):
    pass


class ReplayDivergenceError(Exception):
    pass


def sort_envelopes(envelopes: list) -> list:
    return sorted(envelopes, key=lambda e: (e.timestamp, e.sequence_id))


def reconstruct_chronological(node: QAppNode) -> list:
    return sort_envelopes(node.replay_log)


def verify_payload_hash(envelope: QAppExecutionEnvelope, raw_payload: str) -> bool:
    computed = hashlib.sha256(raw_payload.encode()).hexdigest()
    return computed == envelope.payload_hash


def check_sequence_gap(envelopes: list, node_id: str) -> None:
    sorted_envs = sort_envelopes(envelopes)
    for i in range(1, len(sorted_envs)):
        prev_seq = sorted_envs[i - 1].sequence_id
        curr_seq = sorted_envs[i].sequence_id
        if curr_seq != prev_seq + 1:
            raise SequenceGapError(
                f"HALT | Node={node_id} | SequenceGap detected: "
                f"expected seq={prev_seq + 1}, got seq={curr_seq} | "
                f"invocation_id={sorted_envs[i].invocation_id}"
            )


def reject_corrupted(envelope: QAppExecutionEnvelope, raw_payload: str) -> None:
    if not verify_payload_hash(envelope, raw_payload):
        raise CorruptedHashError(
            f"HALT | invocation_id={envelope.invocation_id} | "
            f"payload_hash mismatch | stored={envelope.payload_hash} | "
            f"computed={hashlib.sha256(raw_payload.encode()).hexdigest()}"
        )


def _compute_replay_hash(envelopes: list, base_hash: str) -> str:
    h = base_hash
    for env in envelopes:
        mixed = f"{h}:{env.payload_hash}:{env.sequence_id}"
        h = hashlib.sha256(mixed.encode()).hexdigest()
    return h


def deterministic_replay_verify(node: QAppNode, runs: int = 5) -> str:
    base = hashlib.sha256(node.node_id.encode()).hexdigest()
    ordered = reconstruct_chronological(node)
    results = []
    for _ in range(runs):
        results.append(_compute_replay_hash(ordered, base))
    if len(set(results)) != 1:
        raise ReplayDivergenceError(
            f"HALT | Node={node.node_id} | replay produced divergent hashes across {runs} runs | "
            f"hashes={results}"
        )
    return results[0]


def simulate_failure_corrupted_hash(nodes: dict, engine: PropagationEngine,
                                     envelope: QAppExecutionEnvelope, bad_payload: str) -> None:
    reject_corrupted(envelope, bad_payload)


def simulate_failure_sequence_gap(node: QAppNode, envelopes: list) -> None:
    check_sequence_gap(envelopes, node.node_id)


def propagate_ordered(engine: PropagationEngine, envelopes: list) -> list:
    path_log = []
    sorted_envs = sort_envelopes(envelopes)
    for env in sorted_envs:
        engine.propagate(env, path_log)
    return path_log
