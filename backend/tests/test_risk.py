from app.services.risk import baseline_risk


def test_baseline_risk_is_explainable_and_verification_aware():
    result = baseline_risk(
        criticality=5,
        cvss=9.8,
        externally_exposed=True,
        exploited=True,
        evidence_confidence=0.9,
    )
    assert result["level"] == "critical"
    assert len(result["factors"]) == 5
    assert sum(f["contribution"] for f in result["factors"]) == result["contextual_score"]


def test_low_confidence_overrides_numeric_level():
    result = baseline_risk(
        criticality=5,
        cvss=10,
        externally_exposed=True,
        exploited=True,
        evidence_confidence=0.2,
    )
    assert result["level"] == "needs_verification"
