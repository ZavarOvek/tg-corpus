"""tgcorpus — turn a public Telegram channel into a clean text corpus."""
from .clean import (
    clean_text,
    detect_signature,
    normalize_for_dedup,
    strip_signature,
    word_count,
)
from .pipeline import PipelineResult, run_pipeline

__all__ = ["clean_text", "normalize_for_dedup", "word_count",
           "detect_signature", "strip_signature",
           "PipelineResult", "run_pipeline"]
__version__ = "0.2.0"
