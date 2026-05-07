from datetime import datetime
from typing import Iterable

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import Technician, TechnicianAvailability, TechnicianServiceArea, TechnicianSpecialty


WINDOW_HOURS = {
    "morning": (8, 12),
    "afternoon": (12, 17),
    "evening": (17, 20),
    "any": (8, 20),
}


def parse_preferred_window(text: str) -> str:
    lowered = text.lower()
    if any(
        token in lowered
        for token in ("any time", "anytime", "whatever", "whenever", "first available", "anything")
    ):
        return "any"
    for key in ("morning", "afternoon", "evening"):
        if key in lowered:
            return key
    return "any"


def get_matching_slots(
    db: Session, zip_code: str, appliance_type: str, preferred_window: str
) -> Iterable[tuple[Technician, TechnicianAvailability]]:
    hour_min, hour_max = WINDOW_HOURS.get(preferred_window, WINDOW_HOURS["any"])

    stmt = (
        select(Technician, TechnicianAvailability)
        .join(TechnicianServiceArea, TechnicianServiceArea.technician_id == Technician.id)
        .join(TechnicianSpecialty, TechnicianSpecialty.technician_id == Technician.id)
        .join(TechnicianAvailability, TechnicianAvailability.technician_id == Technician.id)
        .where(
            and_(
                TechnicianServiceArea.zip_code == zip_code,
                TechnicianSpecialty.appliance_type == appliance_type,
                TechnicianAvailability.is_booked.is_(False),
            )
        )
        .order_by(TechnicianAvailability.start_time.asc())
    )

    for tech, slot in db.execute(stmt).all():
        if hour_min <= slot.start_time.hour < hour_max and slot.start_time >= datetime.utcnow():
            yield tech, slot
