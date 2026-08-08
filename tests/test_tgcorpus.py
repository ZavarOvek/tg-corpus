"""Tests for tgcorpus — all offline, on synthetic records."""
import json
from pathlib import Path

import pytest

from tgcorpus import io
from tgcorpus.clean import (
    clean_text,
    detect_signature,
    normalize_for_dedup,
    strip_signature,
    word_count,
)
from tgcorpus.cli import main
from tgcorpus.fetch import CredentialsError, get_credentials
from tgcorpus.pipeline import run_pipeline


class TestCleanText:
    def test_strips_emoji(self):
        assert clean_text("Привіт 😀🔥 світе") == "Привіт світе"

    def test_strips_urls_by_default(self):
        assert "http" not in clean_text("дивись https://example.com тут")

    def test_keep_urls_flag(self):
        assert "https://example.com" in clean_text(
            "дивись https://example.com", keep_urls=True
        )

    def test_strips_mentions_keeps_hashtags(self):
        out = clean_text("пише @someuser про #мову")
        assert "@someuser" not in out
        assert "#мову" in out

    def test_zero_width_removed(self):
        assert clean_text("сло\u200bво") == "слово"

    def test_whitespace_collapsed(self):
        assert clean_text("а   б\n\n\nв") == "а б\nв"


class TestDedupNormalize:
    def test_case_and_punct_insensitive(self):
        a = normalize_for_dedup("Слава Україні!")
        b = normalize_for_dedup("слава україні")
        assert a == b

    def test_word_count(self):
        assert word_count("два слова, м'ята") == 3


class TestSignature:
    def test_detects_repeated_sign_off(self):
        texts = [
            "Перший пост про мову.\nІлля Кива. Підписатися.",
            "Другий пост про статистику.\nІлля Кива. Підписатися.",
            "Третій пост про корпуси.\nІлля Кива. Підписатися.",
        ]
        assert detect_signature(texts) == "Ілля Кива. Підписатися."

    def test_no_signature_when_no_pattern(self):
        texts = ["Один текст.", "Зовсім інший текст.\nЗ іншим другим рядком."]
        assert detect_signature(texts) is None

    def test_below_ratio_not_detected(self):
        # sign-off appears in only 1 of 4 multiline texts -> below min_ratio
        texts = [
            "А.\nПідпис.",
            "Б.\nЗовсім інше.",
            "В.\nЩе інше.",
            "Г.\nІ ще.",
        ]
        assert detect_signature(texts, min_ratio=0.3) is None

    def test_single_line_texts_ignored(self):
        assert detect_signature(["Один рядок.", "Ще один рядок."]) is None

    def test_strip_signature_removes_trailing_line(self):
        text = "Основний текст.\nІлля Кива. Підписатися."
        assert strip_signature(text, "Ілля Кива. Підписатися.") == "Основний текст."

    def test_strip_signature_noop_when_absent(self):
        text = "Текст без підпису."
        assert strip_signature(text, "Якийсь підпис.") == text


class TestPipelineSignature:
    def test_strip_channel_signature_end_to_end(self):
        raw = [
            make_raw(
                id=i,
                text=f"Повідомлення номер {i} з достатньою довжиною.\nІлля Кива. Підписатися.",
            )
            for i in range(1, 5)
        ]
        result = run_pipeline(raw, strip_channel_signature=True)
        assert result.detected_signature == "Ілля Кива. Підписатися."
        assert all("Підписатися" not in r["text"] for r in result.records)

    def test_disabled_by_default(self):
        raw = [
            make_raw(
                id=i,
                text=f"Повідомлення номер {i} з достатньою довжиною.\nІлля Кива. Підписатися.",
            )
            for i in range(1, 5)
        ]
        result = run_pipeline(raw)
        assert result.detected_signature is None
        assert all("Підписатися" in r["text"] for r in result.records)


def make_raw(**overrides):
    base = {
        "id": 1,
        "date": "2026-07-01T10:00:00+00:00",
        "text": "Це достатньо довге тестове повідомлення",
        "views": 10,
        "forwards": 0,
        "is_forward": False,
    }
    base.update(overrides)
    return base


class TestPipeline:
    def test_keeps_valid_message(self):
        result = run_pipeline([make_raw()])
        assert result.stats["kept"] == 1
        assert result.records[0]["n_words"] == 5

    def test_drops_empty(self):
        result = run_pipeline([make_raw(text="")])
        assert result.stats["no_text"] == 1
        assert not result.records

    def test_drops_short(self):
        result = run_pipeline([make_raw(text="два слова")], min_words=3)
        assert result.stats["too_short"] == 1

    def test_drops_forwards_when_asked(self):
        result = run_pipeline(
            [make_raw(is_forward=True)], drop_forwards=True
        )
        assert result.stats["forward"] == 1

    def test_keeps_forwards_by_default(self):
        result = run_pipeline([make_raw(is_forward=True)])
        assert result.stats["kept"] == 1

    def test_dedup_keeps_first(self):
        first = make_raw(id=1)
        dup = make_raw(id=2, text="це ДОСТАТНЬО довге тестове повідомлення!")
        result = run_pipeline([first, dup])
        assert result.stats["duplicate"] == 1
        assert result.records[0]["id"] == 1

    def test_message_dropped_if_only_emoji_and_url(self):
        result = run_pipeline([make_raw(text="🔥🔥 https://t.me/spam")])
        assert result.stats["too_short"] == 1


class TestIo:
    def test_jsonl_roundtrip(self, tmp_path: Path):
        records = [make_raw(), make_raw(id=2)]
        path = io.write_jsonl(records, tmp_path / "x.jsonl")
        assert list(io.read_jsonl(path)) == records

    def test_invalid_jsonl_raises(self, tmp_path: Path):
        path = tmp_path / "bad.jsonl"
        path.write_text("{oops", encoding="utf-8")
        with pytest.raises(ValueError):
            list(io.read_jsonl(path))

    def test_plain_text_one_line_per_message(self, tmp_path: Path):
        records = [{"text": "рядок один\nрядок два"}, {"text": "друге"}]
        path = io.write_plain_text(records, tmp_path / "c.txt")
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines == ["рядок один рядок два", "друге"]


class TestCredentials:
    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.delenv("TG_API_ID", raising=False)
        monkeypatch.delenv("TG_API_HASH", raising=False)
        with pytest.raises(CredentialsError):
            get_credentials()

    def test_env_credentials(self, monkeypatch):
        monkeypatch.setenv("TG_API_ID", "12345")
        monkeypatch.setenv("TG_API_HASH", "abc")
        assert get_credentials() == (12345, "abc")


class TestCliClean:
    def test_end_to_end(self, tmp_path: Path):
        raw = [
            make_raw(id=3, date="2026-07-03T10:00:00+00:00"),
            make_raw(id=1, date="2026-07-01T10:00:00+00:00",
                     text="Перше повідомлення каналу про мову"),
            make_raw(id=2, date="2026-07-02T10:00:00+00:00", text="коротко"),
        ]
        src = tmp_path / "raw.jsonl"
        src.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in raw),
            encoding="utf-8",
        )
        out = tmp_path / "corpus"
        code = main(["clean", str(src), "-o", str(out)])
        assert code == 0
        for name in ("corpus.jsonl", "corpus.csv", "corpus.txt"):
            assert (out / name).exists()
        # chronological order restored despite shuffled input
        kept = list(io.read_jsonl(out / "corpus.jsonl"))
        assert [r["id"] for r in kept] == [1, 3]

    def test_missing_input(self, tmp_path: Path):
        assert main(["clean", str(tmp_path / "nope.jsonl")]) == 1
