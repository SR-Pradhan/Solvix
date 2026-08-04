"""add reminders

Revision ID: c4e8f10a92db
Revises: a7d2e59b31c8
Create Date: 2026-08-04 19:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c4e8f10a92db'
down_revision: Union[str, Sequence[str], None] = 'a7d2e59b31c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "run_date", "kind", "subject"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("reminders")
