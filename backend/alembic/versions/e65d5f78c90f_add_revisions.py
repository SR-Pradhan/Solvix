"""add revisions

Revision ID: e65d5f78c90f
Revises: 4888a07760a1
Create Date: 2026-08-10 16:01:23.196790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e65d5f78c90f'
down_revision: Union[str, Sequence[str], None] = '4888a07760a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "revisions",
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
        sa.Column("first_solved_at", sa.DateTime(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False, server_default="0"),
        # Nullable on purpose: null is "retired", not "due immediately".
        sa.Column("due_on", sa.Date()),
        sa.Column("last_reminded_on", sa.Date()),
        sa.UniqueConstraint(
            "user_id", "platform", "external_problem_id", name="uq_revision_problem"
        ),
    )
    # Every reminder run asks "what is due for this user today".
    op.create_index("ix_revisions_due", "revisions", ["user_id", "due_on"])

    # Rows are created lazily on the next reminder run, which knows today's
    # date and can place each problem at the right rung of the ladder. Doing it
    # here would need that logic duplicated in SQL.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_revisions_due", table_name="revisions")
    op.drop_table("revisions")
