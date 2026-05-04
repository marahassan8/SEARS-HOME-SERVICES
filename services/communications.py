import logging
import re
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

# RFC 5322–style sanity check: must be local@domain, not a bare hostname.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _resolve_smtp_from() -> str:
    """
    SMTP servers require a valid mailbox in From (e.g. noreply@yourdomain.com).
    Bare hostnames like smtp.example.com or MailerSend sandbox IDs are invalid.
    """
    candidates = [settings.smtp_from_email, settings.smtp_username or ""]
    for raw in candidates:
        candidate = (raw or "").strip()
        if not candidate:
            continue
        if _EMAIL_RE.match(candidate):
            return candidate
        # User pasted only a domain — common mistake with transactional providers
        if "@" not in candidate and "." in candidate and " " not in candidate:
            guessed = f"noreply@{candidate.lstrip('@')}"
            if _EMAIL_RE.match(guessed):
                logger.warning(
                    "SMTP_FROM_EMAIL was not a full address; using %s (set SMTP_FROM_EMAIL to a verified sender)",
                    guessed,
                )
                return guessed
    return "no-reply@shs.local"


def send_image_upload_email(recipient: str, upload_url: str) -> None:
    if not settings.smtp_host:
        print(f"[DEV MODE] Upload link for {recipient}: {upload_url}")
        return

    from_addr = _resolve_smtp_from()
    message = EmailMessage()
    message["Subject"] = "Sears Home Services - Upload Appliance Photo"
    message["From"] = from_addr
    message["To"] = recipient
    message.set_content(
        "Thank you for contacting Sears Home Services.\n\n"
        "Please upload a clear photo of your appliance here:\n"
        f"{upload_url}\n\n"
        "This link is specific to your current support case."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except smtplib.SMTPException as exc:
        logger.exception("SMTP send failed; falling back to console log: %s", exc)
        print(f"[SMTP FAILED] Upload link for {recipient}: {upload_url}")
        print(f"[SMTP FAILED] Fix SMTP_FROM_EMAIL to a verified address like you@yourdomain.com — error: {exc}")


def send_email_entry_link_sms(to_number: str, email_entry_token: str) -> bool:
    """
    SMS a link where the customer can type their email (more reliable than voice STT).
    Requires Twilio credentials and a Twilio SMS-capable From number.
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_sms_from:
        logger.warning("Twilio SMS not configured; cannot send email-entry link.")
        return False
    url = f"{settings.public_base_url.rstrip('/')}/media/enter-email/{email_entry_token}"
    body = (
        "Sears Home Services: open this link to enter your email and get the photo upload link. "
        f"{url}"
    )
    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(body=body, from_=settings.twilio_sms_from, to=to_number)
        return True
    except Exception as exc:
        logger.exception("Twilio SMS failed: %s", exc)
        return False
