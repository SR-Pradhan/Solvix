"""add solution reviews

Revision ID: c4f31a90b2de
Revises: b7d58eba582f
Create Date: 2026-08-30 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c4f31a90b2de'
down_revision: Union[str, Sequence[str], None] = 'b7d58eba582f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "solution_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("external_problem_id", sa.String(length=100), nullable=False),
        sa.Column("problem_name", sa.String(length=255)),
        sa.Column("language", sa.String(length=20)),
        sa.Column("verdict", sa.String(length=20), nullable=False),
        sa.Column(
            "expected",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "used",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("checked_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "user_id",
            "platform",
            "external_problem_id",
            name="uq_review_problem",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("solution_reviews")
