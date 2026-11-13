from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Sequence

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email_sync(
    to_emails: Sequence[str],
    subject: str,
    text_content: str,
    html_content: str | None = None,
) -> bool:
    """
    Synchronously sends an email via SMTP.
    Returns True if sent, False if disabled or failed.
    Never exposes passwords or sensitive credentials in logs.
    """
    settings = get_settings()
    if not settings.smtp_enabled:
        logger.debug("SMTP is disabled; skipping outbound email to %s", to_emails)
        return False

    if not to_emails:
        logger.warning("send_email called with empty recipient list.")
        return False

    if not settings.smtp_host:
        logger.error("SMTP is enabled but smtp_host is not configured.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = ", ".join(to_emails)

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    if html_content:
        msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            if settings.smtp_use_tls:
                server.starttls()

        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)

        server.sendmail(settings.smtp_from_email, list(to_emails), msg.as_string())
        server.quit()
        logger.info("Successfully sent email '%s' to %d recipient(s)", subject, len(to_emails))
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed for user %s at %s", settings.smtp_user, settings.smtp_host)
        return False
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending email '%s': %s", subject, type(exc).__name__)
        return False
    except Exception as exc:
        logger.error("Unexpected error delivering email '%s': %s", subject, type(exc).__name__)
        return False


def dispatch_email_background(
    to_emails: Sequence[str],
    subject: str,
    text_content: str,
    html_content: str | None = None,
) -> None:
    """
    Dispatches outbound email asynchronously to AnyIO / asyncio worker threadpool
    so HTTP request handlers are never blocked by SMTP socket I/O.
    """
    settings = get_settings()
    if not settings.smtp_enabled:
        return

    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, send_email_sync, to_emails, subject, text_content, html_content)
    except RuntimeError:
        # If outside event loop, execute synchronously or skip
        send_email_sync(to_emails, subject, text_content, html_content)

