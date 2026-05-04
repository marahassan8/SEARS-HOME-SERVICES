"""email capture pending + web token

Revision ID: 20260505_0003
Revises: 20260504_0002
Create Date: 2026-05-05 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260505_0003"
down_revision: Union[str, Sequence[str], None] = "20260504_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("call_sessions", sa.Column("pending_email", sa.String(length=255), nullable=True))
    op.add_column("call_sessions", sa.Column("email_entry_token", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_call_sessions_email_entry_token"), "call_sessions", ["email_entry_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_call_sessions_email_entry_token"), table_name="call_sessions")
    op.drop_column("call_sessions", "email_entry_token")
    op.drop_column("call_sessions", "pending_email")
