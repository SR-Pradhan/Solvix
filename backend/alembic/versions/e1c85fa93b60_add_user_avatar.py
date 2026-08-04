"""add user avatar

Revision ID: e1c85fa93b60
Revises: d9f47b25e3ac
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e1c85fa93b60'
down_revision: Union[str, Sequence[str], None] = 'd9f47b25e3ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Stored in the row rather than on disk: free hosting resets the
    # filesystem on every deploy, and a 256px avatar is only tens of KB.
    op.add_column("users", sa.Column("avatar", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("avatar_mime", sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "avatar_mime")
    op.drop_column("users", "avatar")
