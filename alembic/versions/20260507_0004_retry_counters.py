"""add retry counters to call sessions

Revision ID: 20260507_0004
Revises: 20260505_0003
Create Date: 2026-05-07 23:50:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260507_0004"
down_revision: Union[str, Sequence[str], None] = "20260505_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "call_sessions",
        sa.Column("email_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "call_sessions",
        sa.Column("scheduling_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "call_sessions",
        sa.Column("zip_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.alter_column("call_sessions", "email_retry_count", server_default=None)
    op.alter_column("call_sessions", "scheduling_retry_count", server_default=None)
    op.alter_column("call_sessions", "zip_retry_count", server_default=None)


def downgrade() -> None:
    op.drop_column("call_sessions", "zip_retry_count")
    op.drop_column("call_sessions", "scheduling_retry_count")
    op.drop_column("call_sessions", "email_retry_count")
