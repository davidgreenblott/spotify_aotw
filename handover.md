# AOTW Project Handover

## What This Is

An end-to-end pipeline for an "Album of the Week" music club. When a member posts a Spotify album link in a Telegram group chat, the system logs it to a Google Sheet and updates a public static website — no manual data entry required.

For full architecture and design decisions see `AOTW_Project_Summary_2026_02_23.md`.

---

## Current State (as of 2026-02-27)

All 26 tasks are code-complete. The system is deployed to Railway (bot) and the website repo (`aotw-website`) is ready for Netlify. **One blocker remains before Task 26 (end-to-end test) can be signed off: the Railway bot has a Telegram polling conflict.**

### Completed

| # | Task | Key Files |
|---|------|-----------|
| 1 | Google Sheet Pick # formula | `=ROW()-1` in Pick column |
| 2 | URL validation module | `src/validation.py` |
| 3 | Deduplication logic | `get_existing_album_ids()`, `check_duplicate()` in `add_album.py` |
| 4 | Extract Spotify album ID | `get_album_info()` returns `spotify_album_id` |
| 5 | Logging infrastructure | `src/logging_config.py` |
| 6 | Telegram bot core | `src/telegram_bot.py` — polling, whitelist, `@aotw` trigger |
| 7 | Pipeline orchestrator | `src/pipeline.py` — async, 7-step flow |
| 8 | Retry logic | `src/retry_utils.py` — exponential backoff decorator |
| 9 | JSON export | `src/export_json.py` — sheet → normalised `data.json` |
| 10 | GitHub API push | `src/github_push.py` — Contents API, base64 PUT |
| 11 | Partial failure handling | `pipeline.py` returns `partial_failure: True` if GitHub fails after sheet write |
| 12 | Wire Telegram bot to pipeline | `telegram_bot.py` passes env vars to `process_album`, `parse_mode='Markdown'` |
| 13 | Railway deployment config | `railway.json`, `requirements.txt`, `DEPLOYMENT.md` |
| 14 | React + Vite scaffold | `website/` — Vite, React, project structure |
| 15 | AlbumCard component | `website/src/components/AlbumCard.jsx` |
| 16 | SearchBar component | `website/src/components/SearchBar.jsx` |
| 17 | FilterBar component | `website/src/components/FilterBar.jsx` — year/picker/sort dropdowns |
| 18 | AlbumGrid with year grouping | `website/src/components/AlbumGrid.jsx` — flat < 50, grouped ≥ 50 |
| 19 | useAlbums hook | `website/src/hooks/useAlbums.js` |
| 20 | filterSort utils | `website/src/utils/filterSort.js` |
| 21 | Dark mode CSS | `website/src/index.css` — CSS variables + dark mode |
| 22 | Netlify config | `website/netlify.toml`, `DEPLOYMENT_WEBSITE.md` |
| 23 | GitHub website repo | `davidgreenblott/aotw-website` created, `data.json` at root, PAT set in Railway |
| 24 | Integration tests | `tests/test_integration.py` — 103 tests total, all passing |
| 25 | Env config + docs | `.env.example`, `DEPLOYMENT.md`, `DEPLOYMENT_WEBSITE.md` updated |

### Pending

| # | Task | Notes |
|---|------|-------|
| **26** | **End-to-end system test** | Blocked by Railway polling conflict (see below) |

---

## BLOCKER — Railway Telegram Polling Conflict

**Error:** `telegram.error.Conflict: terminated by other getUpdates request`

**What we know:**
- No webhook is set (confirmed via `getWebhookInfo`)
- Replicas is set to 1 in Railway
- `Procfile` has been removed (was causing duplicate process launch — now fixed)
- `drop_pending_updates=True` added to `run_polling()` (clears webhooks on start)
- Conflict persists across redeployments

**Likely cause:** Railway's rolling redeploy starts the new container before stopping the old one, causing a brief window where both poll Telegram simultaneously. With a polling bot this triggers the conflict on every deploy.

**Recommended fix (next session):** Switch from polling to webhooks. Railway provides a public HTTPS URL which can serve as the webhook endpoint. This is more robust and eliminates the conflict entirely.

**Webhook migration involves:**
1. Add a web server to `telegram_bot.py` (python-telegram-bot has built-in webhook support via `run_webhook()`)
2. Set `PORT` env var in Railway and expose it
3. Call Telegram's `setWebhook` API with the Railway public URL
4. Remove the `run_polling()` call

---

## Repo Structure

```
src/
  add_album.py        # Core: Spotify fetch, sheet append, dedup; reads creds from env vars
  add_album_gui.py    # PyQt5 GUI (unchanged)
  logging_config.py   # setup_logging() → structured stdout
  telegram_bot.py     # Bot: polling, whitelist, passes env vars to process_album
  validation.py       # is_valid_spotify_album_url, extract_spotify_album_id, validate_album_metadata
  pipeline.py         # Async orchestrator: validate → dedup → fetch → append → push
  retry_utils.py      # @retry_with_backoff decorator (exponential backoff)
  export_json.py      # Reads full sheet, normalises rows, writes data.json
  github_push.py      # push_data_to_github() via GitHub Contents API; export_and_push()

tests/
  test_add_album.py       # Live Spotify API tests (require real creds)
  test_dedup.py           # Dedup logic (mocked sheet)
  test_telegram_bot.py    # Async bot handler (mocked)
  test_validation.py      # URL + metadata validation
  test_pipeline.py        # 14 async tests (all steps + partial failure)
  test_retry_utils.py     # 10 tests (backoff timing, exception filtering)
  test_export_json.py     # 12 tests (normalisation, date formats, invalid row skipping)
  test_github_push.py     # 11 tests (create/update, base64, error handling)
  test_credentials.py     # 6 tests (env var credential loading)

website/
  src/
    App.jsx                    # Root: useAlbums hook, searchTerm + filters state
    index.css                  # Global styles: CSS reset, design tokens (--accent: #1db954)
    hooks/useAlbums.js         # Fetches /data.json → {albums, loading, error}
    utils/filterSort.js        # filterAndSort(), uniqueValues()
    components/
      AlbumCard.jsx            # Card: artwork (onError → cd-placeholder.svg), Spotify link
      AlbumGrid.jsx            # FLAT GRID (Task 18 will upgrade to year-grouped)
      SearchBar.jsx            # Controlled search input
      FilterBar.jsx            # Year/picker/sort dropdowns
  public/
    data.json                  # Sample data (3 albums); real data comes from pipeline
    cd-placeholder.svg         # CD disc SVG fallback image
  netlify.toml                 # Build config, SPA redirect, cache headers

railway.json                   # Nixpacks builder, restart on failure
requirements.txt               # Runtime deps only (no pytest/PyQt)
DEPLOYMENT.md                  # Railway setup guide + env var table
DEPLOYMENT_WEBSITE.md          # Netlify setup guide
```

---

## Test Suite Status

**103 tests passing** across all test files (except `test_add_album.py` which needs live Spotify creds).

```bash
# Run all mocked tests
mamba run -n spotify-env pytest tests/ --ignore=tests/test_add_album.py -v --asyncio-mode=auto

# Run live Spotify tests
mamba run -n spotify-env pytest tests/test_add_album.py -v
```

---

## Environment

```bash
mamba env create -f environment.yml
mamba activate spotify-env
```

---

## Credentials Needed (never committed)

| File / Env Var | Used For |
|---|---|
| `spotify_credentials.json` | Spotify API local dev fallback |
| `aotw-488201-8465cf54c9d9.json` | Google service account local dev fallback |
| `SPOTIFY_CLIENT_ID` | Railway env var (overrides file) |
| `SPOTIFY_CLIENT_SECRET` | Railway env var (overrides file) |
| `TELEGRAM_BOT_TOKEN` | Railway env var |
| `TELEGRAM_ALLOWED_CHAT_ID` | Railway env var |
| `GITHUB_TOKEN` | Railway env var — fine-grained PAT, Contents:write |
| `GITHUB_REPO_OWNER` | Railway env var |
| `GITHUB_REPO_NAME` | Railway env var |
| `GOOGLE_SHEET_ID` | Default: `1h1uDCZPqJovFfUKPzfPgUwUOHjFdCXHWVhUE6VvFA_s` |
| `GOOGLE_SHEET_TAB` | Sheet tab name |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Raw JSON string (Railway) or file path (local) |

---

## Key Design Decisions

- **No pick number in code** — sheet formula `=ROW()-1` handles it
- **Dedup by album ID** — checked against `spotify_album_url` column before any writes
- **No database** — Google Sheet is canonical; `data.json` is a generated copy pushed to GitHub
- **Partial failure safe** — if GitHub push fails after sheet write, `success: True` + `partial_failure: True`; sheet data is safe
- **Secrets in env vars only** — `GOOGLE_SERVICE_ACCOUNT_JSON` accepts raw JSON string or file path
- **CD placeholder** — `AlbumCard` falls back to `/cd-placeholder.svg` via `onError` when artwork URL is broken
- **Netlify cache** — 5-min `must-revalidate` for `data.json`, 1-year immutable for hashed JS/CSS assets
