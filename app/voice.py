import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.config import settings
from app.database import get_db
from app.models import Appointment, CallSession, TechnicianAvailability
from services.communications import send_image_upload_email
from services.diagnostics import detect_appliance_type, troubleshooting_steps
from services.llm_agent import extract_appliance_type, should_request_image
from services.scheduling import get_matching_slots, parse_preferred_window

router = APIRouter(prefix="/voice", tags=["voice"])


def _say_and_gather(message: str, action: str) -> VoiceResponse:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        speech_timeout="auto",
        action=action,
        method="POST",
        speech_model=settings.twilio_speech_model,
    )
    gather.say(message, voice=settings.twilio_voice)
    response.append(gather)
    response.redirect(action, method="POST")
    return response


def _load_or_create_session(db: Session, call_sid: str) -> CallSession:
    session = db.get(CallSession, call_sid)
    if session:
        return session
    session = CallSession(call_sid=call_sid, stage="collect_appliance")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _extract_email(text: str) -> str | None:
    lowered = text.lower().strip()

    replacements = {
        " at the rate of ": " @ ",
        " at rate of ": " @ ",
        " rate of ": " @ ",
        " at symbol ": " @ ",
        " at ": " @ ",
        " dot ": " . ",
        " period ": " . ",
        " underscore ": " _ ",
        " hyphen ": " - ",
        " dash ": " - ",
        " plus ": " + ",
    }
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)

    tokens = re.findall(r"[a-z0-9]+|[@._+\-]", lowered)
    if not tokens:
        return None

    filler_tokens = {"my", "is", "email", "address", "it", "is", "the", "a", "an", "and", "please"}
    tokens = [token for token in tokens if token not in filler_tokens]

    if "@" not in tokens:
        return None

    at_index = tokens.index("@")
    local_tokens = [token for token in tokens[:at_index] if re.match(r"[a-z0-9._+\-]", token)]
    domain_tokens = [token for token in tokens[at_index + 1 :] if re.match(r"[a-z0-9.\-]", token)]

    local = "".join(local_tokens).strip("._-+")
    domain = "".join(domain_tokens).strip(".-")

    # Common speech-recognition artifacts around popular domains.
    domain = domain.replace("therateof", "")
    domain = domain.replace("attherateof", "")

    candidate = f"{local}@{domain}"
    match = re.search(r"^[a-z0-9][a-z0-9._%+\-]{0,63}@[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}$", candidate)
    return candidate if match else None


@router.post("/incoming")
def incoming_call(CallSid: str = Form(...), db: Session = Depends(get_db)):
    _load_or_create_session(db, CallSid)
    response = _say_and_gather(
        "Thank you for calling Sears Home Services. I can help diagnose your appliance issue. "
        "Which appliance are you calling about today?",
        "/voice/respond",
    )
    return Response(content=str(response), media_type="application/xml")


@router.post("/respond")
def respond(
    CallSid: str = Form(...),
    From: str = Form(default="unknown"),
    SpeechResult: str = Form(default=""),
    db: Session = Depends(get_db),
):
    session = _load_or_create_session(db, CallSid)
    utterance = (SpeechResult or "").strip()

    if session.stage == "collect_appliance":
        appliance = extract_appliance_type(utterance) or detect_appliance_type(utterance)
        if not appliance:
            response = _say_and_gather(
                "I did not catch the appliance type. Please say washer, dryer, refrigerator, "
                "dishwasher, oven, or HVAC.",
                "/voice/respond",
            )
            return Response(content=str(response), media_type="application/xml")

        session.appliance_type = appliance
        session.stage = "collect_symptom"
        db.commit()
        response = _say_and_gather(
            f"Got it, a {appliance}. Please describe what is going wrong.",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "collect_symptom":
        session.symptom = utterance
        session.stage = "collect_started_when"
        db.commit()
        response = _say_and_gather(
            "When did this issue start?",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "collect_started_when":
        session.started_when = utterance
        session.stage = "collect_error_code"
        db.commit()
        response = _say_and_gather(
            "Are you seeing any error code? If none, say no error.",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "collect_error_code":
        session.error_code = utterance
        session.stage = "collect_unusual_sound"
        db.commit()
        response = _say_and_gather(
            "Do you hear unusual sounds? If yes, briefly describe them.",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "collect_unusual_sound":
        session.unusual_sound = utterance
        if should_request_image(session.symptom or "", session.error_code, session.unusual_sound):
            session.stage = "collect_email_for_image"
        else:
            session.stage = "troubleshoot"
        session.troubleshooting_step_index = 0
        db.commit()

    if session.stage == "collect_email_for_image":
        email = _extract_email(utterance)
        if not email:
            response = _say_and_gather(
                "A photo can help diagnosis. Please say your email address clearly, for example name at mail dot com.",
                "/voice/respond",
            )
            return Response(content=str(response), media_type="application/xml")

        token = uuid4().hex
        session.customer_email = email
        session.image_upload_token = token
        session.stage = "troubleshoot"
        db.commit()

        upload_url = f"{settings.public_base_url.rstrip('/')}/media/upload/{token}"
        send_image_upload_email(email, upload_url)

        response = _say_and_gather(
            "Thank you. I just sent a secure photo upload link to your email. "
            "You can upload now or after this call. Let us continue troubleshooting.",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "troubleshoot":
        steps = troubleshooting_steps(session.appliance_type or "", session.symptom or "")
        if session.image_analysis_summary:
            steps = [f"Based on your uploaded photo: {session.image_analysis_summary}"] + steps
        idx = session.troubleshooting_step_index
        if idx < len(steps):
            session.troubleshooting_step_index += 1
            db.commit()
            response = _say_and_gather(
                f"Please try this step: {steps[idx]}. Say done when completed.",
                "/voice/respond",
            )
            return Response(content=str(response), media_type="application/xml")

        if "fixed" in utterance.lower() or "resolved" in utterance.lower():
            response = VoiceResponse()
            response.say(
                "Great news, I am glad that resolved the issue. Thank you for calling Sears Home Services.",
                voice="alice",
            )
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        session.stage = "collect_zip"
        db.commit()
        response = _say_and_gather(
            "Thanks for trying those steps. I can schedule a technician visit. "
            "Please say your five digit ZIP code.",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "collect_zip":
        zip_candidate = "".join(ch for ch in utterance if ch.isdigit())
        if len(zip_candidate) != 5:
            response = _say_and_gather(
                "I need a five digit ZIP code to match technicians. Please repeat your ZIP code.",
                "/voice/respond",
            )
            return Response(content=str(response), media_type="application/xml")
        session.zip_code = zip_candidate
        session.stage = "collect_window"
        db.commit()
        response = _say_and_gather(
            "What time works best for you: morning, afternoon, evening, or any time?",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "collect_window":
        preferred_window = parse_preferred_window(utterance)
        session.preferred_window = preferred_window

        matches = list(
            get_matching_slots(
                db,
                zip_code=session.zip_code or "",
                appliance_type=session.appliance_type or "",
                preferred_window=preferred_window,
            )
        )
        if not matches:
            response = VoiceResponse()
            response.say(
                "I am sorry, I could not find an available technician for that time window. "
                "A representative will follow up shortly.",
                voice="alice",
            )
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        tech, slot = matches[0]
        session.selected_availability_id = slot.id
        session.stage = "confirm_booking"
        db.commit()
        response = _say_and_gather(
            f"I found {tech.name} available on {slot.start_time.strftime('%A %B %d at %I:%M %p')}. "
            "Would you like me to book this appointment? Say yes to confirm.",
            "/voice/respond",
        )
        return Response(content=str(response), media_type="application/xml")

    if session.stage == "confirm_booking":
        if "yes" in utterance.lower() or "confirm" in utterance.lower():
            slot = db.get(TechnicianAvailability, session.selected_availability_id)
            if slot is None or slot.is_booked:
                response = VoiceResponse()
                response.say(
                    "That slot is no longer available. A representative will call you to finalize scheduling.",
                    voice="alice",
                )
                response.hangup()
                return Response(content=str(response), media_type="application/xml")

            slot.is_booked = True
            appointment = Appointment(
                call_sid=session.call_sid,
                customer_phone=From,
                appliance_type=session.appliance_type or "unknown",
                zip_code=session.zip_code or "",
                symptom_summary=(
                    f"Symptom: {session.symptom}; Started: {session.started_when}; "
                    f"Error: {session.error_code}; Sound: {session.unusual_sound}"
                ),
                technician_id=slot.technician_id,
                availability_id=slot.id,
            )
            db.add(appointment)
            db.commit()
            response = VoiceResponse()
            response.say(
                f"Your appointment is confirmed for {slot.start_time.strftime('%A %B %d at %I:%M %p')}. "
                "Thank you for calling Sears Home Services.",
                voice="alice",
            )
            response.hangup()
            return Response(content=str(response), media_type="application/xml")

        response = VoiceResponse()
        response.say(
            "No problem. I have not booked the appointment. A representative will follow up with you shortly.",
            voice="alice",
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    response = VoiceResponse()
    response.say(
        f"I encountered an unexpected state at {datetime.now(UTC).isoformat()}. "
        "Please call again shortly.",
        voice=settings.twilio_voice,
    )
    response.hangup()
    return Response(content=str(response), media_type="application/xml")
