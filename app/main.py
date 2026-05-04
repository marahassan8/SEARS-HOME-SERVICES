from fastapi import FastAPI

from app.media import router as media_router
from app.voice import router as voice_router

app = FastAPI(title="SHS Voice Diagnostic Agent")
app.include_router(voice_router)
app.include_router(media_router)


@app.get("/health")
def health():
    return {"ok": True}
