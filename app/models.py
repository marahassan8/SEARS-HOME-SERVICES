from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(40), default="full_time")

    service_areas = relationship("TechnicianServiceArea", back_populates="technician", cascade="all, delete-orphan")
    specialties = relationship("TechnicianSpecialty", back_populates="technician", cascade="all, delete-orphan")
    availability_slots = relationship("TechnicianAvailability", back_populates="technician", cascade="all, delete-orphan")


class TechnicianServiceArea(Base):
    __tablename__ = "technician_service_areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)

    technician = relationship("Technician", back_populates="service_areas")


class TechnicianSpecialty(Base):
    __tablename__ = "technician_specialties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    appliance_type: Mapped[str] = mapped_column(String(40), nullable=False)

    technician = relationship("Technician", back_populates="specialties")


class TechnicianAvailability(Base):
    __tablename__ = "technician_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    technician = relationship("Technician", back_populates="availability_slots")


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_sid: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    customer_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    appliance_type: Mapped[str] = mapped_column(String(40), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    symptom_summary: Mapped[str] = mapped_column(Text, nullable=False)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    availability_id: Mapped[int] = mapped_column(ForeignKey("technician_availability.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)


class CallSession(Base):
    __tablename__ = "call_sessions"

    call_sid: Mapped[str] = mapped_column(String(80), primary_key=True)
    stage: Mapped[str] = mapped_column(String(40), default="collect_appliance")
    appliance_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    symptom: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_when: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    unusual_sound: Mapped[str | None] = mapped_column(Text, nullable=True)
    troubleshooting_step_index: Mapped[int] = mapped_column(Integer, default=0)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    preferred_window: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selected_availability_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pending_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_entry_token: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, index=True)
    image_upload_token: Mapped[str | None] = mapped_column(String(120), nullable=True)
    image_uploaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scheduling_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    zip_retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ImageUpload(Base):
    __tablename__ = "image_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_sid: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    upload_token: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_appliance: Mapped[str | None] = mapped_column(String(40), nullable=True)
    visible_issues: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
