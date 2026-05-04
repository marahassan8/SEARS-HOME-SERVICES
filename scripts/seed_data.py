from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Technician, TechnicianAvailability, TechnicianServiceArea, TechnicianSpecialty


TECHNICIANS = [
    ("Alex Rivera", "alex@shs.local", "312-555-0100", ["60601", "60602"], ["washer", "dryer"]),
    ("Priya Shah", "priya@shs.local", "312-555-0101", ["60601", "60610"], ["refrigerator", "oven"]),
    ("Marcus Lee", "marcus@shs.local", "312-555-0102", ["60602", "60611"], ["dishwasher", "washer"]),
    ("Dana Brooks", "dana@shs.local", "312-555-0103", ["60610", "60611"], ["hvac", "oven"]),
    ("Ethan Clark", "ethan@shs.local", "312-555-0104", ["60601", "60611"], ["dryer", "hvac"]),
    ("Rosa Diaz", "rosa@shs.local", "312-555-0105", ["60602", "60610"], ["refrigerator", "dishwasher"]),
]


def seed():
    db = SessionLocal()
    try:
        existing = db.execute(select(Technician.id).limit(1)).first()
        if existing:
            print("Seed skipped: technicians already exist")
            return

        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0, tzinfo=None) + timedelta(days=1)
        slot_template = [(9, 11), (13, 15), (17, 19)]

        for idx, (name, email, phone, zips, specialties) in enumerate(TECHNICIANS):
            tech = Technician(name=name, email=email, phone=phone, employment_type="full_time")
            db.add(tech)
            db.flush()

            for zip_code in zips:
                db.add(TechnicianServiceArea(technician_id=tech.id, zip_code=zip_code))
            for appliance in specialties:
                db.add(TechnicianSpecialty(technician_id=tech.id, appliance_type=appliance))

            for day_offset in range(0, 4):
                base_day = now + timedelta(days=day_offset)
                for start_hour, end_hour in slot_template:
                    start_time = base_day.replace(hour=start_hour)
                    end_time = base_day.replace(hour=end_hour)
                    db.add(
                        TechnicianAvailability(
                            technician_id=tech.id,
                            start_time=start_time,
                            end_time=end_time,
                            is_booked=False,
                        )
                    )

        db.commit()
        print(f"Seeded {len(TECHNICIANS)} technicians with availability.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
