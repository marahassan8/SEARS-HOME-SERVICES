"""initial schema

Revision ID: 20260430_0001
Revises:
Create Date: 2026-04-30 14:18:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260430_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_sessions",
        sa.Column("call_sid", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("appliance_type", sa.String(length=40), nullable=True),
        sa.Column("symptom", sa.Text(), nullable=True),
        sa.Column("started_when", sa.String(length=120), nullable=True),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("unusual_sound", sa.String(length=120), nullable=True),
        sa.Column("troubleshooting_step_index", sa.Integer(), nullable=False),
        sa.Column("zip_code", sa.String(length=10), nullable=True),
        sa.Column("preferred_window", sa.String(length=20), nullable=True),
        sa.Column("selected_availability_id", sa.Integer(), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("image_upload_token", sa.String(length=120), nullable=True),
        sa.Column("image_uploaded", sa.Boolean(), nullable=False),
        sa.Column("image_analysis_summary", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("call_sid"),
    )
    op.create_table(
        "technicians",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("employment_type", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_technicians_id"), "technicians", ["id"], unique=False)
    op.create_table(
        "technician_service_areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("zip_code", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "technician_specialties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("appliance_type", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "technician_availability",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("is_booked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("call_sid", sa.String(length=80), nullable=False),
        sa.Column("customer_phone", sa.String(length=40), nullable=False),
        sa.Column("appliance_type", sa.String(length=40), nullable=False),
        sa.Column("zip_code", sa.String(length=10), nullable=False),
        sa.Column("symptom_summary", sa.Text(), nullable=False),
        sa.Column("technician_id", sa.Integer(), nullable=False),
        sa.Column("availability_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["availability_id"], ["technician_availability.id"]),
        sa.ForeignKeyConstraint(["technician_id"], ["technicians.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_appointments_call_sid"), "appointments", ["call_sid"], unique=False)
    op.create_table(
        "image_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("call_sid", sa.String(length=80), nullable=False),
        sa.Column("upload_token", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("detected_appliance", sa.String(length=40), nullable=True),
        sa.Column("visible_issues", sa.Text(), nullable=True),
        sa.Column("recommended_next_step", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_image_uploads_call_sid"), "image_uploads", ["call_sid"], unique=False)
    op.create_index(op.f("ix_image_uploads_upload_token"), "image_uploads", ["upload_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_image_uploads_upload_token"), table_name="image_uploads")
    op.drop_index(op.f("ix_image_uploads_call_sid"), table_name="image_uploads")
    op.drop_table("image_uploads")
    op.drop_index(op.f("ix_appointments_call_sid"), table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("technician_availability")
    op.drop_table("technician_specialties")
    op.drop_table("technician_service_areas")
    op.drop_index(op.f("ix_technicians_id"), table_name="technicians")
    op.drop_table("technicians")
    op.drop_table("call_sessions")
