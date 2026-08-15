"""add interviews

Revision ID: b7d58eba582f
Revises: e65d5f78c90f
Create Date: 2026-08-16 00:32:29.966775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7d58eba582f'
down_revision: Union[str, Sequence[str], None] = 'e65d5f78c90f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(length=80)),
        sa.Column("platform", sa.String(length=20)),
        sa.Column("problem_name", sa.String(length=255)),
        sa.Column("problem_url", sa.String(length=500)),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column(
            "transcript",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime()),
    )
    # Listing a user's interviews newest-first is the only query there is.
    op.create_index("ix_interviews_user", "interviews", ["user_id", "id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_interviews_user", table_name="interviews")
    op.drop_table("interviews")
