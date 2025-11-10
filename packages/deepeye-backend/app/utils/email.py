"""Email utility functions."""

import aiosmtplib
from email.message import EmailMessage

from app.config import settings


async def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email."""
    if not settings.SMTP_HOST:
        # If SMTP is not configured, log and return True (for development)
        print(f"[Email] Would send to {to}: {subject}\n{body}")
        return True

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER if settings.SMTP_USER else None,
            password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
            use_tls=settings.SMTP_TLS,
        )
        return True
    except Exception as e:
        print(f"[Email] Failed to send email: {e}")
        return False

