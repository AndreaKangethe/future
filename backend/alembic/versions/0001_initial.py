"""Create the Deepsight foundation schema.

The metadata-driven first revision keeps the initial scaffold portable across the
SQLite test database and PostgreSQL deployment. Future revisions should use
explicit Alembic operations for controlled production changes.
"""

from alembic import op

import app.models.audit
import app.models.core
import app.models.integration
import app.models.investigation
import app.models.ml
import app.models.observation
import app.models.relationship
import app.models.report
import app.models.risk_assessment
import app.models.vulnerability
from app.db.base import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
