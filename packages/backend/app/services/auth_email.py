"""Auth email delivery helpers."""

from email.message import EmailMessage
import smtplib
from urllib.parse import urlencode

from app.core.config import settings
from deepeye.utils.logger import logger


def _send_email(to_email: str, subject: str, body: str) -> bool:
    smtp_host = settings.AUTH_SMTP_HOST
    sender = settings.AUTH_EMAIL_FROM
    if not smtp_host or not sender:
        logger.warning("[auth-email] SMTP not configured, skip sending email to %s", to_email)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, settings.AUTH_SMTP_PORT, timeout=15) as server:
            if settings.AUTH_SMTP_USE_TLS:
                server.starttls()
            if settings.AUTH_SMTP_USERNAME and settings.AUTH_SMTP_PASSWORD:
                server.login(settings.AUTH_SMTP_USERNAME, settings.AUTH_SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception as exc:
        logger.exception("[auth-email] Failed to send email to %s: %s", to_email, exc)
        return False


def send_verification_email(to_email: str, token: str) -> bool:
    """Send email verification message."""
    base_url = settings.AUTH_FRONTEND_BASE_URL.rstrip("/")
    verify_query = urlencode({"token": token, "email": to_email})
    verify_url = f"{base_url}/verify-email?{verify_query}"
    body = (
        "Please verify your DeepEye account email.\n\n"
        f"Verification link: {verify_url}\n\n"
        "If you did not create this account, you can ignore this message."
    )
    sent = _send_email(to_email, "DeepEye Email Verification", body)
    if not sent:
        logger.info("[auth-email] verification token for %s: %s", to_email, token)
    return sent


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send password reset message."""
    base_url = settings.AUTH_FRONTEND_BASE_URL.rstrip("/")
    reset_query = urlencode({"token": token, "email": to_email})
    reset_url = f"{base_url}/reset-password?{reset_query}"
    body = (
        "We received a request to reset your DeepEye password.\n\n"
        f"Reset link: {reset_url}\n\n"
        "If you did not request this reset, ignore this message."
    )
    sent = _send_email(to_email, "DeepEye Password Reset", body)
    if not sent:
        logger.info("[auth-email] password reset token for %s: %s", to_email, token)
    return sent
