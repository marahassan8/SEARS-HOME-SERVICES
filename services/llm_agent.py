import base64
import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from app.config import settings
from services.diagnostics import detect_appliance_type

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,63}@[a-zA-Z0-9][a-zA-Z0-9.\-]*\.[a-zA-Z]{2,}$")

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    appliance_type: str | None
    visible_issues: str
    recommendation: str


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def extract_email_from_speech(utterance: str, *, call_sid: str | None = None) -> str | None:
    """
    Parse a messy speech-to-text transcript into a single RFC-shaped email or None.
    """
    text = (utterance or "").strip()
    if not text:
        return None
    client = _client()
    if client is None:
        return None
    try:
        logger.info(
            "openai_call purpose=extract_email model=%s call_sid=%s",
            settings.llm_model,
            call_sid or "-",
        )
        response = client.responses.create(
            model=settings.llm_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You normalize caller email addresses from noisy phone speech transcripts. "
                        "Return strict JSON with one key: email. "
                        "Value must be a single valid email in lowercase, or null if you cannot infer it. "
                        "Fix common STT errors: 'at the rate', 'at', 'dot', missing dots in gmail/outlook/yahoo. "
                        "Do not invent domains; if unsure return null."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        payload = json.loads(response.output_text.strip())
        raw = payload.get("email")
        if raw is None or raw == "null":
            return None
        candidate = str(raw).strip().lower()
        return candidate if _EMAIL_RE.match(candidate) else None
    except Exception:
        return None


def extract_appliance_type(utterance: str, *, call_sid: str | None = None) -> str | None:
    fallback = detect_appliance_type(utterance)
    client = _client()
    if client is None:
        return fallback

    try:
        logger.info(
            "openai_call purpose=extract_appliance model=%s call_sid=%s",
            settings.llm_model,
            call_sid or "-",
        )
        response = client.responses.create(
            model=settings.llm_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract the caller appliance type. Return strict JSON with key appliance_type "
                        "and value one of washer,dryer,refrigerator,dishwasher,oven,hvac,null."
                    ),
                },
                {"role": "user", "content": utterance},
            ],
        )
        payload = json.loads(response.output_text.strip())
        parsed = payload.get("appliance_type")
        if parsed in {"washer", "dryer", "refrigerator", "dishwasher", "oven", "hvac"}:
            return parsed
    except Exception:
        return fallback
    return fallback


def should_request_image(symptom: str, error_code: str | None, unusual_sound: str | None) -> bool:
    text = " ".join([symptom or "", error_code or "", unusual_sound or ""]).lower()
    if any(token in text for token in ("leak", "burn", "spark", "smoke", "crack", "broken", "error")):
        return True
    return len(text) > 30


def analyze_appliance_image(
    image_bytes: bytes, reported_appliance_type: str | None, *, call_sid: str | None = None
) -> VisionResult:
    client = _client()
    if client is None:
        return VisionResult(
            appliance_type=reported_appliance_type,
            visible_issues="Vision model not configured. Image received for manual review.",
            recommendation="Continue with technician scheduling and include image in work order notes.",
        )

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    try:
        logger.info(
            "openai_call purpose=vision_analyze model=%s call_sid=%s image_bytes=%s",
            settings.vision_model,
            call_sid or "-",
            len(image_bytes),
        )
        response = client.responses.create(
            model=settings.vision_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an appliance diagnostics assistant. Return strict JSON with keys: "
                        "appliance_type, visible_issues, recommendation. appliance_type must be one of "
                        "washer,dryer,refrigerator,dishwasher,oven,hvac,unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Reported appliance type: {reported_appliance_type or 'unknown'}",
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{encoded}",
                        },
                    ],
                },
            ],
        )
        parsed = json.loads(response.output_text.strip())
        appliance = parsed.get("appliance_type")
        if appliance == "unknown":
            appliance = reported_appliance_type
        return VisionResult(
            appliance_type=appliance,
            visible_issues=parsed.get("visible_issues", "No obvious issue detected."),
            recommendation=parsed.get("recommendation", "Proceed with standard troubleshooting."),
        )
    except Exception:
        return VisionResult(
            appliance_type=reported_appliance_type,
            visible_issues="Unable to complete automated vision analysis.",
            recommendation="Proceed with baseline troubleshooting and technician scheduling.",
        )
