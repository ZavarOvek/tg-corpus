"""tgcorpus — turn a public Telegram channel into a clean text corpus."""

from .clean import (
    clean_text,
    detect_signature,
    normalize_for_dedup,
    strip_signature,
    word_count,
)
from .pipeline import PipelineResult, run_pipeline

__all__ = [
    "PipelineResult",
    "clean_text",
    "detect_signature",
    "normalize_for_dedup",
    "run_pipeline",
    "strip_signature",
    "word_count",
]
__version__ = "0.2.1"
