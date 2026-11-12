from dataclasses import dataclass
from typing import Any

STRONG_IDENTIFIERS = {"mac", "cloud_resource_id", "device_id", "serial"}


@dataclass(frozen=True)
class IdentityDecision:
    outcome: str
    score: float
    evidence: dict[str, Any]
    reason: str


def resolve_identity(
    observation_identifiers: dict[str, Any],
    candidate_identifiers: dict[str, Any],
) -> IdentityDecision:
    strong_matches = [
        key
        for key in STRONG_IDENTIFIERS
        if observation_identifiers.get(key)
        and observation_identifiers.get(key) == candidate_identifiers.get(key)
    ]
    conflicts = [
        key
        for key in STRONG_IDENTIFIERS
        if observation_identifiers.get(key)
        and candidate_identifiers.get(key)
        and observation_identifiers[key] != candidate_identifiers[key]
    ]
    if conflicts:
        return IdentityDecision(
            "potentially_separate",
            0.05,
            {"conflicts": conflicts, "strong_matches": strong_matches},
            "Strong identifiers conflict; automatic merge is blocked.",
        )
    if strong_matches:
        return IdentityDecision(
            "confirmed_match",
            0.99,
            {"strong_matches": strong_matches},
            "A strong identifier matched exactly.",
        )
    shared = [
        key
        for key in ("hostname", "fqdn", "ip")
        if observation_identifiers.get(key)
        and observation_identifiers.get(key) == candidate_identifiers.get(key)
    ]
    if shared and shared != ["ip"]:
        return IdentityDecision(
            "probable_match",
            0.7,
            {"shared_identifiers": shared},
            "Weak or contextual identifiers agree; analyst review is required.",
        )
    return IdentityDecision(
        "unresolved",
        0.1 if shared else 0.0,
        {"shared_identifiers": shared},
        "No sufficient identity evidence was found.",
    )
