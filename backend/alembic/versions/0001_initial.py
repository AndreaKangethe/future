"""Create the Deepsight foundation schema.

The metadata-driven first revision keeps the initial scaffold portable across the
SQLite test database and PostgreSQL deployment. Future revisions should use
explicit Alembic operations for controlled production changes.
"""

from alembic import op
from app.db.base import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        for table, column in (
            ("observations", "observation_timestamp"),
            ("model_inferences", "created_at"),
            ("risk_assessments", "created_at"),
        ):
            op.execute(f"SELECT create_hypertable('{table}', '{column}', if_not_exists => TRUE)")


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
