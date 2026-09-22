"""Text cleaning for Telegram messages.

Pure functions only — no network, fully testable.
"""

from __future__ import annotations

import re

_URL = re.compile(r"https?://\S+|t\.me/\S+|www\.\S+", re.IGNORECASE)
# Not preceded by a word char or a dot, so the "@ukr.net" in "news@ukr.net" is
# left alone instead of being cut down to "news.net".
_MENTION = re.compile(r"(?<![\w.])@\w{3,}")
_HASHTAG = re.compile(r"#\w+")
# Emoji and pictographs (main Unicode blocks) + variation selectors
_EMOJI = re.compile(
    "["
    "\U0001f000-\U0001faff"  # emoji, symbols, pictographs
    "\U00002600-\U000027bf"  # misc symbols, dingbats
    "\U0001f1e6-\U0001f1ff"  # regional indicators (flags)
    "\ufe0e\ufe0f\u200d"  # variation selectors, ZWJ
    "\u20e3"  # combining enclosing keycap (the box in 1️⃣)
    "]+"
)
_ZERO_WIDTH = re.compile(r"[\u200B\u200C\u2060\uFEFF]")
_WS = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{2,}")


def clean_text(
    text: str,
    keep_urls: bool = False,
    keep_mentions: bool = False,
    keep_hashtags: bool = True,
) -> str:
    """Normalize one message: strip emoji, zero-width chars, extra whitespace,
    and (by default) URLs and @mentions."""
    text = _ZERO_WIDTH.sub("", text)
    text = _EMOJI.sub(" ", text)
    if not keep_urls:
        text = _URL.sub(" ", text)
    if not keep_mentions:
        text = _MENTION.sub(" ", text)
    if not keep_hashtags:
        text = _HASHTAG.sub(" ", text)
    text = _WS.sub(" ", text)
    # Spaces only: with \s+ a line starting with ")" was glued to the line above.
    text = re.sub(r"[ \t]+([,.:;!?»)\]])", r"\1", text)
    text = _MULTI_NL.sub("\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def normalize_for_dedup(text: str) -> str:
    """Casefold and collapse whitespace/punctuation for duplicate detection."""
    text = re.sub(r"[^\w\s']", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"[\w']+", text))


def detect_signature(
    texts: list[str], min_ratio: float = 0.3, min_occurrences: int = 3
) -> str | None:
    """Detect a boilerplate sign-off line repeated at the end of many messages
    (e.g. a channel's "Subscribe" call-to-action).

    Looks at the last non-empty line of each multi-line text (single-line
    texts have nothing to strip and are skipped) and returns the most common
    one, if it recurs in at least ``min_ratio`` of multi-line texts and at
    least ``min_occurrences`` times overall. Returns ``None`` otherwise —
    channels without a repeated sign-off should not have anything stripped.
    """
    from collections import Counter

    last_lines: Counter[str] = Counter()
    multiline_total = 0
    for text in texts:
        lines = [line for line in text.split("\n") if line.strip()]
        if len(lines) < 2:
            continue
        multiline_total += 1
        last_lines[lines[-1].strip()] += 1

    if not last_lines:
        return None
    line, count = last_lines.most_common(1)[0]
    if count >= min_occurrences and count / multiline_total >= min_ratio:
        return line
    return None


def strip_signature(text: str, signature: str) -> str:
    """Remove a trailing signature line (as returned by ``detect_signature``)
    from a single message, if present."""
    lines = text.split("\n")
    while lines and lines[-1].strip() == signature:
        lines.pop()
    return "\n".join(lines).strip()
