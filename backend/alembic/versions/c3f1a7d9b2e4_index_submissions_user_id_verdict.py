"""index submissions on user_id and verdict

Revision ID: c3f1a7d9b2e4
Revises: 20e9e45a4474
Create Date: 2026-08-03 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c3f1a7d9b2e4'
down_revision: Union[str, Sequence[str], None] = '20e9e45a4474'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_submissions_user_id_verdict",
        "submissions",
        ["user_id", "verdict"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_submissions_user_id_verdict", table_name="submissions")
