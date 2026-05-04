"""expand call session text fields

Revision ID: 20260504_0002
Revises: 20260430_0001
Create Date: 2026-05-04 20:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260504_0002"
down_revision: Union[str, Sequence[str], None] = "20260430_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "call_sessions",
        "started_when",
        existing_type=sa.String(length=120),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "call_sessions",
        "error_code",
        existing_type=sa.String(length=40),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "call_sessions",
        "unusual_sound",
        existing_type=sa.String(length=120),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "call_sessions",
        "unusual_sound",
        existing_type=sa.Text(),
        type_=sa.String(length=120),
        existing_nullable=True,
    )
    op.alter_column(
        "call_sessions",
        "error_code",
        existing_type=sa.Text(),
        type_=sa.String(length=40),
        existing_nullable=True,
    )
    op.alter_column(
        "call_sessions",
        "started_when",
        existing_type=sa.Text(),
        type_=sa.String(length=120),
        existing_nullable=True,
    )
