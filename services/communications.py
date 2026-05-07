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

    Two-pass: prefer a fully-valid candidate (so SMTP_USERNAME — typically the
    verified trial sender — beats a domain-only SMTP_FROM_EMAIL); only as a
    last resort do we synthesize a noreply@<domain> address.
    """
    candidates = [
        (settings.smtp_from_email or "").strip(),
        (settings.smtp_username or "").strip(),
    ]

    for candidate in candidates:
        if candidate and _EMAIL_RE.match(candidate):
            return candidate

    for candidate in candidates:
        if candidate and "@" not in candidate and "." in candidate and " " not in candidate:
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
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        logger.info("Sent appliance upload link to %s from %s", recipient, from_addr)
    except (smtplib.SMTPException, OSError) as exc:
        logger.exception("SMTP send failed (from=%s, to=%s): %s", from_addr, recipient, exc)
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
