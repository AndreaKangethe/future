from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    record_type: str
    record_id: str
    statement: str
    epistemic_class: str


def summarize(question: str, evidence: Iterable[Evidence]) -> dict:
    items = list(evidence)
    if not items:
        return {
            "answer": "I could not find approved platform evidence for that question.",
            "references": [],
            "limitations": ["No matching records were retrieved."],
        }
    lines = [
        f"Evidence summary for: {question}",
        *[
            f"[{item.epistemic_class}] {item.statement} ({item.record_type}:{item.record_id})"
            for item in items
        ],
    ]
    return {
        "answer": "\n".join(lines),
        "references": [{"type": item.record_type, "id": item.record_id} for item in items],
        "limitations": [
            "Offline deterministic fallback used; no unsupported conclusions were generated."
        ],
    }
