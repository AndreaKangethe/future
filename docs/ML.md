# Machine learning

ML outputs remain epistemically separate from confirmed facts. The current
foundation includes:

- `model_registry` and `model_inferences` SQLAlchemy tables, compatible with
  SQLite and PostgreSQL.
- Registry helpers for registering, listing, selecting active models, and
  recording inferences.
- A dependency-free deterministic anomaly scorer based on baseline-relative
  numeric z-scores. It returns a bounded score, anomaly flag, formula version,
  and per-feature explanation.

This is not a trained model and does not provide production accuracy,
calibration, persistence of fitted baselines, or automatic API routes.
Non-numeric features are ignored. Synthetic training data must be reported as
synthetic and never presented as production accuracy.
