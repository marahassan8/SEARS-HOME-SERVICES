from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CallSession, ImageUpload
from services.llm_agent import analyze_appliance_image

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/media", tags=["media"])


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
    path = UPLOAD_DIR / filename
    content = await file.read()
    path.write_bytes(content)

    vision = analyze_appliance_image(content, session.appliance_type)
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
        }
    )
