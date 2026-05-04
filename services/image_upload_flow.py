from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CallSession
from services.communications import send_image_upload_email


def grant_upload_link_for_verified_email(db: Session, session: CallSession, email: str) -> None:
    normalized = (email or "").strip().lower()
    token = uuid4().hex
    session.customer_email = normalized
    session.pending_email = None
    session.email_entry_token = None
    session.image_upload_token = token
    session.stage = "troubleshoot"
    session.troubleshooting_step_index = 0
    db.commit()
    upload_url = f"{settings.public_base_url.rstrip('/')}/media/upload/{token}"
    send_image_upload_email(normalized, upload_url)
