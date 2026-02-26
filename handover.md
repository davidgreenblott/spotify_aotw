# AOTW Project Handover

## What This Is

An end-to-end pipeline for an "Album of the Week" music club. When a member posts a Spotify album link in a Telegram group chat, the system logs it to a Google Sheet and updates a public static website — no manual data entry required.

For full architecture and design decisions see `AOTW_Project_Summary_2026_02_23.md`.

---

## Current State (as of 2026-02-24)

Tasks 1–6 of 26 are complete. The backend foundation is in place.

### Completed

| # | Task | Notes |
|---|------|-------|
| 1 | Google Sheet Pick # formula | `=ROW()-1` in Pick column — code no longer computes pick numbers |
| 2 | URL validation module | `src/validation.py` |
| 3 | Deduplication logic | `get_existing_album_ids()`, `check_duplicate()` in `add_album.py` |
| 4 | Extract Spotify album ID | `get_album_info()` now returns `spotify_album_id` |
| 5 | Logging infrastructure | `src/logging_config.py`, structured stdout via Python `logging` |
| 6 | Telegram bot core | `src/telegram_bot.py`, polling mode, chat whitelist, `@aotw` trigger |

### Up Next

| # | Task |
|---|------|
| 7 | Refactor `add_album.py` into a pipeline module (`src/pipeline.py`) |
| 8 | Retry logic for external API calls |
| 9 | JSON export (`data.json` generation from sheet) |
| 10 | GitHub API integration to push `data.json` |
| 11 | Partial failure handling (sheet OK but GitHub push failed) |
| 12 | Wire Telegram bot to the completed pipeline |
| 13 | Railway deployment config |
| 14–23 | React + Vite frontend, Netlify deployment |
| 24–26 | Integration tests, docs, end-to-end validation |

---

## Repo Structure

```
src/
  add_album.py        # Core logic: Spotify fetch, sheet append, dedup
  add_album_gui.py    # PyQt5 GUI (existing, unchanged)
  logging_config.py   # setup_logging() → structured stdout logger
  telegram_bot.py     # Telegram bot (polling, whitelist, @aotw trigger)
  validation.py       # is_valid_spotify_album_url, extract_spotify_album_id,
                      #   validate_album_metadata

tests/
  test_add_album.py   # Live Spotify API tests (require real credentials)
  test_dedup.py       # Dedup logic tests (mocked sheet)
  test_telegram_bot.py# Async bot handler tests (mocked)
  test_validation.py  # URL + metadata validation tests
```

---

## Environment

```bash
mamba env create -f environment.yml
mamba activate spotify-env

# Run tests (no live credentials needed)
mamba run -n spotify-env pytest tests/test_validation.py tests/test_dedup.py tests/test_telegram_bot.py -v --asyncio-mode=auto

# Run live Spotify tests (requires spotify_credentials.json)
mamba run -n spotify-env pytest tests/test_add_album.py -v
```

---

## Credentials Needed (never committed)

| File / Env Var | Used For |
|---|---|
| `spotify_credentials.json` | Spotify API (CLIENT_ID, CLIENT_SECRET) |
| `aotw-488201-8465cf54c9d9.json` | Google service account |
| `TELEGRAM_BOT_TOKEN` | Railway env var |
| `TELEGRAM_ALLOWED_CHAT_ID` | Railway env var — Telegram group chat ID |
| `GITHUB_TOKEN` | Railway env var — fine-grained PAT, Contents:write on website repo |
| `GOOGLE_SHEET_ID` | Defaults to hardcoded value in `add_album.py` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Defaults to `aotw-488201-8465cf54c9d9.json` |

---

## Key Design Decisions

- **No pick number in code** — sheet formula `=ROW()-1` handles it; eliminates race conditions
- **Dedup by album ID** — checked against `spotify_album_url` column before any writes
- **No database** — Google Sheet is the canonical record; `data.json` is a generated copy pushed to GitHub
- **Partial failure safe** — if GitHub push fails after sheet write, data is safe; next run regenerates JSON from sheet
- **Secrets in env vars only** — never logged, never committed
