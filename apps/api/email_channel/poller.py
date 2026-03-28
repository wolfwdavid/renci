"""Background email poller — checks Gmail for new messages on an interval."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("renci.email_poller")

_running = False
_executor = ThreadPoolExecutor(max_workers=1)


def _fetch_emails_sync() -> list:
    """Blocking IMAP fetch — runs in thread pool to avoid blocking the event loop."""
    from email_channel.receiver import fetch_unread_emails
    return fetch_unread_emails()


async def poll_emails_once() -> int:
    """Check for and process new emails. Returns count of processed emails."""
    loop = asyncio.get_event_loop()
    try:
        emails = await loop.run_in_executor(_executor, _fetch_emails_sync)
    except Exception as e:
        logger.error(f"Failed to fetch emails: {e}")
        return 0

    count = 0
    for msg in emails:
        try:
            from email_channel.handler import handle_email
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

    # Delay first poll so uvicorn responds to Cloud Run health check
    await asyncio.sleep(15)

    while _running:
        try:
            await poll_emails_once()
        except Exception as e:
            logger.error(f"Poll cycle error: {e}")
        await asyncio.sleep(interval_seconds)


def stop_email_poller() -> None:
    """Stop the background email polling loop."""
    global _running
    _running = False
    logger.info("Email poller stopped")
