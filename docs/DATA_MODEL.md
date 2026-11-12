# Deepsight data model

The initial migration creates `users`, `assets`, and `findings`. The production model expands these into immutable observations, time-ranged identifiers, identity decisions, services, relationships, intelligence, ML outputs, risk history, investigations, job runs, and reports.

```mermaid
erDiagram
  USERS ||--o{ AUDIT_LOG : creates
  ASSETS ||--o{ FINDINGS : has
  ASSETS ||--o{ OBSERVATIONS : reconciles
  ASSETS ||--o{ RISK_ASSESSMENTS : receives
```
