import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import CallSession, ImageUpload
from services.image_upload_flow import grant_upload_link_for_verified_email
from services.llm_agent import analyze_appliance_image

_EMAIL_FORM = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._%+\-]*@[a-zA-Z0-9][a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

router = APIRouter(prefix="/media", tags=["media"])

def _upload_dir() -> Path:
    """
    Vercel/serverless filesystems are read-only except for /tmp.
    Create directories lazily at request time (not import time).
    """
    base = Path(settings.upload_dir or "/tmp/uploads")
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Last-resort fallback.
        base = Path("/tmp/uploads")
        base.mkdir(parents=True, exist_ok=True)
    return base


@router.get("/enter-email/{token}", response_class=HTMLResponse)
def enter_email_page(token: str, db: Session = Depends(get_db)):
    session = db.query(CallSession).filter(CallSession.email_entry_token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    return HTMLResponse(
        content=(
            "<html><body><h2>Enter your email</h2><p>Type your email to receive the appliance photo upload link.</p>"
            "<form action='/media/enter-email/{token}' method='post'>"
            "<input type='email' name='email' required placeholder='you@example.com' style='width:280px'/>"
            "<button type='submit'>Submit</button></form></body></html>"
        ).replace("{token}", token)
    )


@router.post("/enter-email/{token}", response_class=HTMLResponse)
def enter_email_submit(token: str, email: str = Form(...), db: Session = Depends(get_db)):
    session = db.query(CallSession).filter(CallSession.email_entry_token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid or expired link.")
    normalized = (email or "").strip().lower()
    if not _EMAIL_FORM.match(normalized):
        back_url = f"/media/enter-email/{token}"
        return HTMLResponse(
            content=(
                f"<html><body><p>That does not look like a valid email.</p>"
                f"<a href='{back_url}'>Try again</a></body></html>"
            ),
            status_code=400,
        )
    grant_upload_link_for_verified_email(db, session, normalized)
    return HTMLResponse(
        content=(
            "<html><body><p>Thank you. Check your inbox for the upload link.</p>"
            "<p>You can return to your call.</p></body></html>"
        )
    )


@router.get("/upload/{token}", response_class=HTMLResponse)
def get_upload_page(token: str, db: Session = Depends(get_db)):
    session = db.query(CallSession).filter(CallSession.image_upload_token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid upload link.")
    return HTMLResponse(
        content=(
            "<html><body><h2>Sears Home Services - Appliance Photo Upload</h2>"
            "<form action='/media/upload/{token}' method='post' enctype='multipart/form-data'>"
            "<input type='file' name='file' accept='image/*' required />"
            "<button type='submit'>Upload</button></form></body></html>"
        ).replace("{token}", token)
    )


@router.post("/upload/{token}")
async def upload_image(token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    session = db.query(CallSession).filter(CallSession.image_upload_token == token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid upload link.")

    extension = Path(file.filename or "photo.jpg").suffix or ".jpg"
    filename = f"{uuid4().hex}{extension}"
    path = _upload_dir() / filename
    content = await file.read()
    path.write_bytes(content)

    vision = analyze_appliance_image(content, session.appliance_type, call_sid=session.call_sid)
    session.image_uploaded = True
    session.image_analysis_summary = (
        f"Detected appliance: {vision.appliance_type or 'unknown'}. "
        f"Visible issues: {vision.visible_issues}. "
        f"Recommended next step: {vision.recommendation}"
    )

    image_upload = ImageUpload(
        call_sid=session.call_sid,
        upload_token=token,
        email=session.customer_email or "unknown@unknown.local",
        file_path=str(path),
        detected_appliance=vision.appliance_type,
        visible_issues=vision.visible_issues,
        recommended_next_step=vision.recommendation,
    )
    db.add(image_upload)
    db.commit()

    return JSONResponse(
        {
            "status": "uploaded",
            "detected_appliance": vision.appliance_type,
            "visible_issues": vision.visible_issues,
            "recommended_next_step": vision.recommendation,
            "note": "On serverless platforms, uploaded files are stored in /tmp and may not persist long-term.",
        }
    )
