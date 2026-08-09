"""add users.token_version

Revision ID: 71d04016900b
Revises: a3d7be24f915
Create Date: 2026-08-10 01:43:00.899620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71d04016900b'
down_revision: Union[str, Sequence[str], None] = 'a3d7be24f915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default rather than a Python default: existing rows need a value
    # too, and tokens already in the wild carry no version, which is read as 0.
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_version")
