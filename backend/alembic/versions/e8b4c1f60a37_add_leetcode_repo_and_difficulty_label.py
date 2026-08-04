"""add leetcode_repo and difficulty_label

Revision ID: e8b4c1f60a37
Revises: c3f1a7d9b2e4
Create Date: 2026-08-04 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e8b4c1f60a37'
down_revision: Union[str, Sequence[str], None] = 'c3f1a7d9b2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("leetcode_repo", sa.String(length=140), nullable=True))
    op.add_column(
        "submissions", sa.Column("difficulty_label", sa.String(length=10), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("submissions", "difficulty_label")
    op.drop_column("users", "leetcode_repo")
