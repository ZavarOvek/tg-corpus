"""Fetching raw messages from a Telegram channel via Telethon.

This is the only module that touches the network. Telethon is imported
lazily so the rest of the package (the ``clean`` pipeline) works without it.

Credentials: pass ``api_id``/``api_hash`` explicitly or set the environment
variables ``TG_API_ID`` and ``TG_API_HASH`` (get them at https://my.telegram.org).
On first run Telethon interactively asks for your phone number and login code,
then stores a local ``.session`` file. Never commit ``*.session`` files.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator


class CredentialsError(RuntimeError):
    pass


def _load_dotenv() -> None:
    """Load a .env file from the current directory, if present.

    Optional: falls back silently if python-dotenv isn't installed, or if
    there's no .env file — real environment variables still work either way.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def get_credentials(api_id: int | None = None, api_hash: str | None = None) -> tuple[int, str]:
    _load_dotenv()
    api_id = api_id or int(os.environ.get("TG_API_ID", 0) or 0)
    api_hash = api_hash or os.environ.get("TG_API_HASH", "")
    if not api_id or not api_hash:
        raise CredentialsError(
            "Telegram API credentials missing: pass --api-id/--api-hash "
            "or set TG_API_ID and TG_API_HASH environment variables "
            "(create them at https://my.telegram.org)."
        )
    return api_id, api_hash


async def fetch_messages(
    channel: str,
    limit: int | None,
    api_id: int,
    api_hash: str,
    session: str = "tgcorpus",
) -> AsyncIterator[dict]:
    """Yield raw message records from ``channel`` (username or t.me link),
    newest first (Telegram API order)."""
    try:
        from telethon import TelegramClient
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("telethon is not installed; run: pip install telethon") from exc

    client = TelegramClient(session, api_id, api_hash)
    async with client:
        async for message in client.iter_messages(channel, limit=limit):
            yield {
                "id": message.id,
                "date": message.date.isoformat() if message.date else None,
                "text": message.raw_text or "",
                "views": message.views,
                "forwards": message.forwards,
                "is_forward": message.fwd_from is not None,
                "reply_to": message.reply_to_msg_id,
            }
