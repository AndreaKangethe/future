from app.services.drift import drift_summary


def test_drift_summary_detects_distribution_change():
    result = drift_summary([1, 1, 1, 2, 2], [8, 9, 9, 10, 10])
    assert result["status"] == "drift"
    assert result["psi"] > 0.2
