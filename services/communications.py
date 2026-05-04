import smtplib
from email.message import EmailMessage

from app.config import settings


def send_image_upload_email(recipient: str, upload_url: str) -> None:
    if not settings.smtp_host:
        print(f"[DEV MODE] Upload link for {recipient}: {upload_url}")
        return

    message = EmailMessage()
    message["Subject"] = "Sears Home Services - Upload Appliance Photo"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "Thank you for contacting Sears Home Services.\n\n"
        "Please upload a clear photo of your appliance here:\n"
        f"{upload_url}\n\n"
        "This link is specific to your current support case."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
