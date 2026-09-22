# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed
- `clean_text` no longer treats the domain of an email address as an
  @mention: `news@ukr.net` used to come out as `news.net`.
- Keycap emoji (`1️⃣`) are removed whole; the combining keycap U+20E3 used to
  survive as a stray `⃣`.
- A line starting with `)`, `»`, `,` and similar is no longer glued to the
  line above it when the space before punctuation is removed.

### Changed
- `fetch.py` docstrings now match the packaging: `telethon` and
  `python-dotenv` are required dependencies (Telethon is still imported
  lazily); the dead `ImportError` fallback for python-dotenv is gone.
- Adopted `ruff format` as the project formatter; the whole tree was
  reformatted in a single dedicated commit (see `.git-blame-ignore-revs`).
- `E501` disabled in `ruff check`: line length is the formatter's job, and
  the formatter cannot split string literals anyway.
- CI lint job now also runs `ruff format --check .`.

## [0.2.1] - 2026-08-08

### Added
- GitHub Actions CI: `ruff` lint job and a `pytest` matrix on Python 3.10-3.12.
- Ruff configuration in `pyproject.toml` (`RUF001-003` disabled: they flag
  Cyrillic letters as ambiguous look-alikes of Latin ones, which is a false
  positive in a project about Ukrainian text).
- Package metadata: `keywords`, `classifiers` and `[project.urls]`.
- Status badges in both READMEs.

### Changed
- `license` migrated to the PEP 639 SPDX form (`license = "MIT"` +
  `license-files`); build now requires `setuptools>=77`.
- Import order normalized by ruff; no behaviour changes.
- `TestCredentials` no longer depends on the absence of a local `.env`
  file; both tests are now hermetic.

## [0.2.0] — 2026-07-21

### Added
- `--strip-signature` flag for `tg-corpus clean`: auto-detects a repeated
  channel sign-off line (e.g. a "Subscribe" call-to-action appended to every
  post) and removes it before the word-count filter and deduplication run.
  Detection is per-channel and data-driven — nothing to configure by hand,
  and channels without a repeated sign-off are left untouched.
- `detect_signature()` / `strip_signature()` exposed as public library
  functions in `tgcorpus.clean`.
- CLI now reports what it detected: `detected sign-off, stripped: '...'` or
  `no repeated sign-off detected`.

### Notes
- Prompted by testing `fetch` + `clean` on a live channel, where a repeated
  author sign-off was inflating word frequencies in the output corpus.
- Detection matches an exact trailing line; a sign-off with varying wording
  between posts won't be caught (documented as a known limitation).

## [0.1.0] — 2026-07-19

### Added
- Initial release: two-stage pipeline, `fetch` (Telethon, network) and
  `clean` (pure functions, offline).
- Cleaning: emoji/pictograph stripping, URL and @mention removal
  (configurable), zero-width character removal, whitespace normalization.
- Filtering: empty messages, forwards (optional), minimum word count.
- Deduplication: case- and punctuation-insensitive, keeps first occurrence.
- Export to JSONL (full metadata), CSV, and plain text (one message per
  line).
- `.env` support via `python-dotenv` for `TG_API_ID` / `TG_API_HASH`.
- Test suite covering the full `clean` pipeline offline (no credentials
  needed).
