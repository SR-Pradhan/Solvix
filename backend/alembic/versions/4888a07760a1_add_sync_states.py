"""add sync_states

Revision ID: 4888a07760a1
Revises: 71d04016900b
Create Date: 2026-08-10 10:46:28.234035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4888a07760a1'
down_revision: Union[str, Sequence[str], None] = '71d04016900b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sync_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("full_import_completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "platform", name="uq_sync_user_platform"),
    )

    # No backfill on purpose. Every existing account simply does one more
    # full fetch on its next sync, which is idempotent thanks to the unique
    # constraint on submissions. A heuristic like "more than N rows means it
    # finished" would be a guess, and guessing is exactly what caused the bug.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("sync_states")
