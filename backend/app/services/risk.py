from dataclasses import dataclass


@dataclass(frozen=True)
class RiskFactor:
    name: str
    value: float
    weight: float
    evidence_ref: str

    @property
    def contribution(self) -> float:
        return round(self.value * self.weight, 2)


def baseline_risk(
    *,
    criticality: int,
    cvss: float | None,
    externally_exposed: bool,
    exploited: bool,
    evidence_confidence: float,
) -> dict:
    factors = [
        RiskFactor("asset_criticality", criticality / 5 * 100, 0.25, "asset:criticality"),
        RiskFactor("cvss", (cvss or 0) * 10, 0.30, "finding:cvss"),
        RiskFactor("external_exposure", 100 if externally_exposed else 0, 0.20, "service:exposure"),
        RiskFactor("exploitation_signal", 100 if exploited else 0, 0.20, "intel:exploitation"),
        RiskFactor("evidence_confidence", evidence_confidence * 100, 0.05, "evidence:confidence"),
    ]
    score = round(min(100, max(0, sum(f.contribution for f in factors))), 2)
    level = (
        "critical" if score >= 85 else "high" if score >= 65 else "medium" if score >= 40 else "low"
    )
    if evidence_confidence < 0.4:
        level = "needs_verification"
    return {
        "contextual_score": score,
        "level": level,
        "factors": [
            {
                "name": f.name,
                "value": f.value,
                "weight": f.weight,
                "contribution": f.contribution,
                "evidence_ref": f.evidence_ref,
            }
            for f in factors
        ],
        "confidence": evidence_confidence,
        "formula_version": "baseline-1",
    }
