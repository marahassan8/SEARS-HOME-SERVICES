import base64
import json
from dataclasses import dataclass

from openai import OpenAI

from app.config import settings
from services.diagnostics import detect_appliance_type


@dataclass
class VisionResult:
    appliance_type: str | None
    visible_issues: str
    recommendation: str


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def extract_appliance_type(utterance: str) -> str | None:
    fallback = detect_appliance_type(utterance)
    client = _client()
    if client is None:
        return fallback

    try:
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


def analyze_appliance_image(image_bytes: bytes, reported_appliance_type: str | None) -> VisionResult:
    client = _client()
    if client is None:
        return VisionResult(
            appliance_type=reported_appliance_type,
            visible_issues="Vision model not configured. Image received for manual review.",
            recommendation="Continue with technician scheduling and include image in work order notes.",
        )

    encoded = base64.b64encode(image_bytes).decode("utf-8")
    try:
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
