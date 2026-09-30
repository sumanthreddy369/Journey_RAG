"""Five-field anonymous local progress history."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progress_history",
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("topic_label", sa.String(120), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("route", sa.String(10), nullable=False),
        sa.Column("recommendation", sa.String(200), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="valid_score"),
        sa.CheckConstraint("route IN ('reteach', 'practice', 'advance')", name="valid_route"),
    )


def downgrade() -> None:
    op.drop_table("progress_history")
