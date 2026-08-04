"""add platform to reminders

Revision ID: b6c3d70e14fa
Revises: c4e8f10a92db
Create Date: 2026-08-04 20:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b6c3d70e14fa'
down_revision: Union[str, Sequence[str], None] = 'c4e8f10a92db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows predate the column and carry no platform. They are one
    # day's generated reminders and regenerate on the next read, so clearing
    # them is cheaper and more honest than guessing a platform for each.
    op.execute("DELETE FROM reminders")

    op.add_column("reminders", sa.Column("platform", sa.String(length=20), nullable=False))
    op.drop_constraint(
        "reminders_user_id_run_date_kind_subject_key", "reminders", type_="unique"
    )
    op.create_unique_constraint(
        "reminders_user_id_run_date_kind_platform_subject_key",
        "reminders",
        ["user_id", "run_date", "kind", "platform", "subject"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "reminders_user_id_run_date_kind_platform_subject_key",
        "reminders",
        type_="unique",
    )
    op.create_unique_constraint(
        "reminders_user_id_run_date_kind_subject_key",
        "reminders",
        ["user_id", "run_date", "kind", "subject"],
    )
    op.drop_column("reminders", "platform")
