"""Email sending via SMTP (#231, #234).

Uses the stdlib ``smtplib`` — no extra dependency. Sends multipart
emails (text/plain + text/html) rendered from Jinja2 templates.
Silent no-op when SMTP is not configured.
"""

import smtplib
import uuid
from contextlib import suppress
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Any

from flask import Flask, render_template

from dashboard.config import Config
from dashboard.logging import get_logger

log = get_logger("email")

_app: Flask | None = None


def init_email(app: Flask) -> None:
    """Store a reference to the Flask app for template rendering."""
    global _app  # noqa: PLW0603
    _app = app
    if Config.SMTP_ENABLED:
        log.info("email_enabled", host=Config.SMTP_HOST, port=Config.SMTP_PORT)
    else:
        log.info("email_disabled")


def send_email(to: str, subject: str, template: str, **ctx: Any) -> bool:
    """Send a multipart email (text + HTML) rendered from Jinja2 templates.

    The ``template`` parameter should be the HTML template path (e.g.
    ``email/password_reset.html``). The text version is derived by
    replacing ``.html`` with ``.txt``. If the text template does not
    exist, only the HTML part is sent.

    Returns True on success, False on failure (logged, never raises).
    """
    if not Config.SMTP_ENABLED:
        log.warning("email_not_configured", to=to, subject=subject)
        return False
    if _app is None:
        log.error("email_app_not_initialized")
        return False

    try:
        with _app.app_context():
            html = render_template(template, **ctx)
            text = None
            txt_template = template.replace(".html", ".txt")
            with suppress(Exception):
                text = render_template(txt_template, **ctx)
    except Exception:
        log.error("email_render_error", template=template, exc_info=True)
        return False

    # Extract domain from SMTP_FROM for the Message-ID
    from_domain = (
        Config.SMTP_FROM.rsplit("@", 1)[-1] if "@" in Config.SMTP_FROM else "kenboard"
    )
    msg = MIMEMultipart("alternative")
    msg["From"] = Config.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(idstring=uuid.uuid4().hex[:8], domain=from_domain)
    # text/plain first, then text/html — RFC 2046: last part is preferred
    if text:
        msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as srv:
            if Config.SMTP_USE_TLS:
                srv.starttls()
            if Config.SMTP_USER:
                srv.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            srv.sendmail(Config.SMTP_FROM, to, msg.as_string())
        log.info("email_sent", to=to, subject=subject)
        return True
    except Exception:
        log.error("email_send_error", to=to, subject=subject, exc_info=True)
        return False
