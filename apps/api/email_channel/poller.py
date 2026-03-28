"""Background email poller — checks Gmail for new messages on an interval."""

import asyncio
import logging
from email_channel.receiver import fetch_unread_emails
from email_channel.handler import handle_email

logger = logging.getLogger("renci.email_poller")

_running = False


async def poll_emails_once() -> int:
    """Check for and process new emails. Returns count of processed emails."""
    try:
        emails = fetch_unread_emails()
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        return 0

    count = 0
    for msg in emails:
        try:
            await handle_email(msg)
            count += 1
            logger.info(f"Processed email from {msg.from_address}")
        except Exception as e:
            logger.error(f"Failed to handle email from {msg.from_address}: {e}")

    return count


async def start_email_poller(interval_seconds: int = 15) -> None:
    """Start the background email polling loop."""
    global _running
    if _running:
        return
    _running = True
    logger.info(f"Email poller started (every {interval_seconds}s)")

    while _running:
        await poll_emails_once()
        await asyncio.sleep(interval_seconds)


def stop_email_poller() -> None:
    """Stop the background email polling loop."""
    global _running
    _running = False
    logger.info("Email poller stopped")
