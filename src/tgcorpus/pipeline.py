"""Corpus-building pipeline: raw message records -> clean, deduplicated corpus.

A raw record is a dict with at least ``id``, ``date``, ``text``; optional
fields: ``views``, ``forwards``, ``is_forward``, ``reply_to``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from .clean import (
    clean_text,
    detect_signature,
    normalize_for_dedup,
    strip_signature,
    word_count,
)


@dataclass
class PipelineResult:
    records: list[dict]
    stats: Counter = field(default_factory=Counter)
    detected_signature: str | None = None


def run_pipeline(
    raw_records: Iterable[dict],
    min_words: int = 3,
    drop_forwards: bool = False,
    keep_urls: bool = False,
    keep_mentions: bool = False,
    keep_hashtags: bool = True,
    strip_channel_signature: bool = False,
) -> PipelineResult:
    """Filter, clean and deduplicate raw Telegram records.

    Drop reasons are counted in ``stats``: ``no_text``, ``forward``,
    ``too_short``, ``duplicate``; ``kept`` and ``total`` are also tracked.
    Deduplication keeps the first occurrence (chronological order if the
    input is sorted by date).

    If ``strip_channel_signature`` is set, a repeated sign-off line (e.g. a
    channel's "Subscribe" call-to-action) is auto-detected across all
    messages and removed before the word-count filter and deduplication run
    — see :func:`tgcorpus.clean.detect_signature`.
    """
    stats: Counter = Counter()
    stage1: list[tuple[dict, str]] = []

    for raw in raw_records:
        stats["total"] += 1
        text = (raw.get("text") or "").strip()
        if not text:
            stats["no_text"] += 1
            continue
        if drop_forwards and raw.get("is_forward"):
            stats["forward"] += 1
            continue

        cleaned = clean_text(
            text,
            keep_urls=keep_urls,
            keep_mentions=keep_mentions,
            keep_hashtags=keep_hashtags,
        )
        stage1.append((raw, cleaned))

    signature = None
    if strip_channel_signature and stage1:
        signature = detect_signature([cleaned for _, cleaned in stage1])
        if signature:
            stage1 = [
                (raw, strip_signature(cleaned, signature))
                for raw, cleaned in stage1
            ]

    seen: set[str] = set()
    kept: list[dict] = []

    for raw, cleaned in stage1:
        n_words = word_count(cleaned)
        if n_words < min_words:
            stats["too_short"] += 1
            continue

        key = normalize_for_dedup(cleaned)
        if key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(key)

        kept.append(
            {
                "id": raw.get("id"),
                "date": raw.get("date"),
                "text": cleaned,
                "n_words": n_words,
                "views": raw.get("views"),
                "forwards": raw.get("forwards"),
                "is_forward": bool(raw.get("is_forward")),
            }
        )
        stats["kept"] += 1

    return PipelineResult(records=kept, stats=stats, detected_signature=signature)
