"""Gmail IMAP receiver — polls inbox for new messages from business owners."""

import imaplib
import email
from email.header import decode_header
from dataclasses import dataclass
from config import settings


@dataclass
class IncomingEmail:
    from_address: str
    subject: str
    body: str
    message_id: str


def connect_imap() -> imaplib.IMAP4_SSL:
    """Connect to Gmail IMAP."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(settings.renci_email, settings.renci_email_app_password)
    return imap


def fetch_unread_emails() -> list[IncomingEmail]:
    """Fetch all unread emails from the inbox."""
    imap = connect_imap()
    imap.select("INBOX")

    _, message_numbers = imap.search(None, "UNSEEN")
    emails = []

    for num in message_numbers[0].split():
        _, msg_data = imap.fetch(num, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        # Extract sender
        from_addr = email.utils.parseaddr(msg["From"])[1]

        # Extract subject
        subject = ""
        try:
            if msg["Subject"]:
                decoded = decode_header(msg["Subject"])
                subject = decoded[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode(decoded[0][1] or "utf-8", errors="replace")
        except Exception:
            subject = ""

        # Extract body
        body = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode(charset, errors="replace")
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors="replace")
        except Exception:
            body = ""

        # Mark as read
        imap.store(num, "+FLAGS", "\\Seen")

        emails.append(IncomingEmail(
            from_address=from_addr,
            subject=subject.strip(),
            body=body.strip(),
            message_id=msg.get("Message-ID", ""),
        ))

    imap.close()
    imap.logout()
    return emails
