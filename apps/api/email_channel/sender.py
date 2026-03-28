"""Gmail SMTP sender — sends agent responses back via email."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings


def send_email_reply(to_address: str, subject: str, body: str) -> None:
    """Send an email reply via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = settings.renci_email
    msg["To"] = to_address
    msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.renci_email, settings.renci_email_app_password)
        server.send_message(msg)
