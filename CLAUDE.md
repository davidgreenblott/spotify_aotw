# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An automated "Album of the Week" pipeline. When a member posts a Spotify album link in a Telegram group chat (prefixed with `@aotw`), the system fetches album metadata, appends it to a Google Sheet, exports the full sheet to `data.json`, and pushes it to GitHub so a Netlify-hosted React website auto-deploys with the new pick.

## Environment Setup

```bash
mamba env create -f environment.yml
mamba activate spotify-env
```

## Common Commands

**Run the Telegram bot:**
```bash
python src/telegram_bot.py
```

**Run the GUI (legacy, still works):**
```bash
python src/add_album_gui.py
```

**Run all mocked tests:**
```bash
mamba run -n spotify-env pytest tests/ --ignore=tests/test_add_album.py -v --asyncio-mode=auto
```

**Run live Spotify tests (requires credentials):**
```bash
mamba run -n spotify-env pytest tests/test_add_album.py -v
```

**Run website dev server:**
```bash
cd website && npm run dev
```

## Architecture

### Backend (Python, deployed on Railway)

1. **`src/telegram_bot.py`** — Polls Telegram. Triggers pipeline on `@aotw <url>` messages from whitelisted chat.
2. **`src/pipeline.py`** — Async orchestrator. Seven steps: validate URL → dedup check → Spotify fetch → metadata validate → sheet append → JSON export → GitHub push.
3. **`src/add_album.py`** — Core: `get_spotify_api()`, `get_album_info()`, `get_google_sheet()`, `build_row_from_header()`, `check_duplicate()`.
4. **`src/export_json.py`** — Reads full sheet, normalises rows, writes `data.json`.
5. **`src/github_push.py`** — Pushes `data.json` to GitHub via Contents API. `export_and_push()` is the main entry point.
6. **`src/validation.py`** — `is_valid_spotify_album_url()`, `extract_spotify_album_id()`, `validate_album_metadata()`.
7. **`src/retry_utils.py`** — `@retry_with_backoff` decorator (exponential backoff, configurable exceptions).

### Website (React + Vite, deployed on Netlify)

- `website/src/App.jsx` — Root component, state for searchTerm + filters.
- `website/src/hooks/useAlbums.js` — Fetches `/data.json`, exports `useAlbums()` and `useAlbumMetadata()`.
- `website/src/utils/filterSort.js` — `filterAndSort()`, `processAlbums()`, `groupByYear()`, `uniqueValues()`.
- `website/src/components/` — `AlbumGrid`, `AlbumCard`, `SearchBar`, `FilterBar`.
- `website/public/data.json` — Sample data for local dev; real data comes from the pipeline.

## Testing

Always write unit tests for new functions and significant changes. Use `pytest`.

- Cover the happy path, sad path, and edge cases
- Mock all external API calls (Spotify, Google Sheets, GitHub) — tests must not need live credentials
- Place tests in `tests/` mirroring the source structure
- Tests in `test_add_album.py` are the exception: they make real Spotify API calls

## Key Design Decisions

- **No pick number in code** — sheet formula `=ROW()-1` handles it; pick numbers are never computed in Python
- **Dedup by album ID** — checked against `spotify_album_url` column before any writes
- **No database** — Google Sheet is canonical; `data.json` is a generated copy pushed to GitHub
- **Partial failure safe** — if GitHub push fails after sheet write, returns `success: True, partial_failure: True`; album is safe
- **Secrets in env vars only** — `GOOGLE_SERVICE_ACCOUNT_JSON` accepts raw JSON string or file path
- **AlbumGrid threshold** — < 50 albums → flat grid; ≥ 50 → grouped by pick year with collapse/expand

## External Credentials (gitignored)

- `spotify_credentials.json` — Spotify API credentials (local dev fallback)
- `aotw-488201-8465cf54c9d9.json` — Google service account key (local dev fallback)
- See `.env.example` for the full list of environment variables required
