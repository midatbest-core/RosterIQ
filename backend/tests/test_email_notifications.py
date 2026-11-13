import smtplib
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import get_settings
from app.core.email import send_email_sync, dispatch_email_background


def test_email_disabled_by_default():
    settings = get_settings()
    # By default in testing/dev, SMTP is disabled
    with patch.object(settings, "smtp_enabled", False):
        result = send_email_sync(["test@example.com"], "Test Subject", "Test Body")
        assert result is False


def test_email_empty_recipients():
    settings = get_settings()
    with patch.object(settings, "smtp_enabled", True), patch.object(settings, "smtp_host", "smtp.example.com"):
        result = send_email_sync([], "Test Subject", "Test Body")
        assert result is False


def test_email_missing_host():
    settings = get_settings()
    with patch.object(settings, "smtp_enabled", True), patch.object(settings, "smtp_host", ""):
        result = send_email_sync(["test@example.com"], "Test Subject", "Test Body")
        assert result is False


def test_email_successful_delivery():
    settings = get_settings()
    with patch.object(settings, "smtp_enabled", True), \
         patch.object(settings, "smtp_host", "smtp.example.com"), \
         patch.object(settings, "smtp_port", 587), \
         patch.object(settings, "smtp_user", "mailer"), \
         patch.object(settings, "smtp_password", "secretpass"), \
         patch.object(settings, "smtp_use_tls", True), \
         patch("smtplib.SMTP") as mock_smtp_cls:

        mock_smtp = MagicMock()
        mock_smtp_cls.return_value = mock_smtp

        result = send_email_sync(["user@example.com"], "Important Notice", "Shift updated.")
        assert result is True
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=10)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("mailer", "secretpass")
        mock_smtp.sendmail.assert_called_once()
        mock_smtp.quit.assert_called_once()


def test_email_smtp_ssl_delivery():
    settings = get_settings()
    with patch.object(settings, "smtp_enabled", True), \
         patch.object(settings, "smtp_host", "smtp.example.com"), \
         patch.object(settings, "smtp_port", 465), \
         patch.object(settings, "smtp_user", "mailer"), \
         patch.object(settings, "smtp_password", "secretpass"), \
         patch("smtplib.SMTP_SSL") as mock_smtp_ssl_cls:

        mock_smtp_ssl = MagicMock()
        mock_smtp_ssl_cls.return_value = mock_smtp_ssl

        result = send_email_sync(["user@example.com"], "SSL Notice", "Shift updated.")
        assert result is True
        mock_smtp_ssl_cls.assert_called_once_with("smtp.example.com", 465, timeout=10)
        mock_smtp_ssl.login.assert_called_once_with("mailer", "secretpass")
        mock_smtp_ssl.sendmail.assert_called_once()
        mock_smtp_ssl.quit.assert_called_once()


def test_email_authentication_failure():
    settings = get_settings()
    with patch.object(settings, "smtp_enabled", True), \
         patch.object(settings, "smtp_host", "smtp.example.com"), \
         patch.object(settings, "smtp_port", 587), \
         patch.object(settings, "smtp_user", "mailer"), \
         patch.object(settings, "smtp_password", "wrongpass"), \
         patch("smtplib.SMTP") as mock_smtp_cls:

        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
        mock_smtp_cls.return_value = mock_smtp

        result = send_email_sync(["user@example.com"], "Auth Fail", "Body")
        assert result is False


def test_dispatch_email_background_non_blocking():
    settings = get_settings()
    with patch.object(settings, "smtp_enabled", True), \
         patch("app.core.email.send_email_sync") as mock_sync:
        dispatch_email_background(["user@example.com"], "Background", "Body")
        # In synchronous context without running loop, executes safely
        mock_sync.assert_called_once()

