"""Command-line interface with two subcommands:

``tg-corpus fetch @channel -o raw.jsonl``   — download raw messages (network)
``tg-corpus clean raw.jsonl -o out/``       — build a clean corpus (offline)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import io
from .pipeline import run_pipeline

load_dotenv()  # reads .env in the current working directory, if present


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tg-corpus",
        description="Turn a public Telegram channel into a clean text corpus.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="download raw messages to JSONL")
    f.add_argument("channel", help="channel username or t.me link")
    f.add_argument("-o", "--out", type=Path, default=Path("raw.jsonl"))
    f.add_argument("--limit", type=int, default=None, help="max messages to fetch (default: all)")
    f.add_argument("--api-id", type=int, default=None)
    f.add_argument("--api-hash", default=None)
    f.add_argument(
        "--session", default="tgcorpus", help="Telethon session name (default: tgcorpus)"
    )

    c = sub.add_parser("clean", help="build a clean corpus from raw JSONL")
    c.add_argument("input", type=Path, help="raw JSONL file from `fetch`")
    c.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("corpus"),
        help="output directory (default: ./corpus)",
    )
    c.add_argument(
        "--min-words", type=int, default=3, help="drop messages shorter than N words (default: 3)"
    )
    c.add_argument("--drop-forwards", action="store_true", help="drop forwarded messages")
    c.add_argument("--keep-urls", action="store_true")
    c.add_argument("--keep-mentions", action="store_true")
    c.add_argument("--drop-hashtags", action="store_true")
    c.add_argument(
        "--strip-signature",
        action="store_true",
        help="auto-detect and remove a repeated channel sign-off "
        "line (e.g. a 'Subscribe' CTA) before filtering/dedup",
    )
    c.add_argument(
        "--formats", nargs="+", default=["jsonl", "csv", "txt"], choices=["jsonl", "csv", "txt"]
    )
    return p


def _cmd_fetch(args: argparse.Namespace) -> int:
    from .fetch import CredentialsError, fetch_messages, get_credentials

    try:
        api_id, api_hash = get_credentials(args.api_id, args.api_hash)
    except CredentialsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    async def run() -> int:
        count = 0
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as handle:
            import json

            async for record in fetch_messages(
                args.channel, args.limit, api_id, api_hash, args.session
            ):
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                if count % 500 == 0:
                    print(f"fetched: {count}", file=sys.stderr)
        print(f"fetched {count} messages -> {args.out}")
        return 0

    return asyncio.run(run())


def _cmd_clean(args: argparse.Namespace) -> int:
    try:
        raw = list(io.read_jsonl(args.input))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Telegram API returns newest first; restore chronological order
    raw.sort(key=lambda r: (r.get("date") or "", r.get("id") or 0))

    result = run_pipeline(
        raw,
        min_words=args.min_words,
        drop_forwards=args.drop_forwards,
        keep_urls=args.keep_urls,
        keep_mentions=args.keep_mentions,
        keep_hashtags=not args.drop_hashtags,
        strip_channel_signature=args.strip_signature,
    )

    if args.strip_signature:
        if result.detected_signature:
            print(f"detected sign-off, stripped: {result.detected_signature!r}")
        else:
            print("no repeated sign-off detected")

    written = []
    if "jsonl" in args.formats:
        written.append(io.write_jsonl(result.records, args.out / "corpus.jsonl"))
    if "csv" in args.formats:
        written.append(io.write_csv(result.records, args.out / "corpus.csv"))
    if "txt" in args.formats:
        written.append(io.write_plain_text(result.records, args.out / "corpus.txt"))

    s = result.stats
    print(f"total: {s['total']}  kept: {s['kept']}")
    dropped = {k: s[k] for k in ("no_text", "forward", "too_short", "duplicate") if s[k]}
    if dropped:
        print("dropped: " + ", ".join(f"{k}={v}" for k, v in dropped.items()))
    for path in written:
        print(f"written: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "fetch":
        return _cmd_fetch(args)
    return _cmd_clean(args)


if __name__ == "__main__":
    raise SystemExit(main())
