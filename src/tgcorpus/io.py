"""Read raw JSONL dumps; write clean corpora as JSONL, CSV and plain text."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Iterator

FIELDS = ["id", "date", "text", "n_words", "views", "forwards", "is_forward"]


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON") from exc


def write_jsonl(records: Iterable[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def write_csv(records: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key) for key in FIELDS})
    return path


def write_plain_text(records: Iterable[dict], path: Path) -> Path:
    """One message per line, newlines inside a message replaced by spaces.
    Ready to feed into downstream tools (e.g. a frequency-dictionary CLI)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record["text"].replace("\n", " ") + "\n")
    return path
