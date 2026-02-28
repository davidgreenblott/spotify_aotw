# AOTW Project Handover

## What This Is

An end-to-end pipeline for an "Album of the Week" music club. When a member posts a Spotify album link in a Telegram group chat, the system logs it to a Google Sheet and updates a public static website — no manual data entry required.

For full architecture and design decisions see `AOTW_Project_Summary_2026_02_23.md`.

---

## Current State (as of 2026-02-28)

All 26 tasks are complete and the system is fully deployed and end-to-end tested.

- **Railway** — Telegram bot running on webhooks (`run_webhook()`), no polling conflicts
- **Google Sheet** — canonical data store, pick numbers auto-filled by `=ROW()-1`
- **GitHub (`aotw-website`)** — `data.json` at repo root, pushed by bot on every new pick
- **Netlify** — auto-deploys on every `aotw-website` commit, site live within ~1 min

---

## Repo Structure

```
src/
  add_album.py        # Core: Spotify fetch, sheet append, dedup
  add_album_gui.py    # PyQt5 GUI (legacy, still works)
  logging_config.py   # setup_logging() → structured stdout
  telegram_bot.py     # Bot: webhook mode, whitelist, @aotw trigger
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
    App.jsx                      # Router: BrowserRouter, sticky header, nav links
    index.css                    # Global styles, CSS variables (--accent: #1db954)
    hooks/useAlbums.js           # useAlbums() → {albums, loading, error}; useAlbumMetadata()
    utils/filterSort.js          # filterAndSort(), processAlbums(), groupByYear(), uniqueDecades()
    components/
      AlbumCard.jsx              # Card: artwork, Spotify link, pick # badge
      AlbumGrid.jsx              # Grouped by pick year (default) or flat (when sorted)
      SearchBar.jsx              # Controlled search input
      FilterBar.jsx              # Decade + Sort By dropdowns
    pages/
      PicksPage.jsx              # Main page: search + filter + AlbumGrid
      AboutPage.jsx              # About page (static)
      AnalyticsPage.jsx          # Analytics: release decade bar chart (Recharts)
  public/
    data.json                    # Gitignored locally; real data copied from aotw-website for dev
    cd-placeholder.svg           # CD disc SVG fallback image
  netlify.toml                   # Build config, SPA redirect, cache headers

railway.json                     # Nixpacks builder, restart on failure, no healthcheck path
requirements.txt                 # python-telegram-bot[webhooks] + runtime deps
DEPLOYMENT.md                    # Railway setup guide + env var table
DEPLOYMENT_WEBSITE.md            # Netlify setup guide
```

---

## Website Pages

| Path | Page | Notes |
|---|---|---|
| `/` | the picks | Album grid with search, decade filter, sort |
| `/about` | about | Static description of the club |
| `/analytics` | analytics | Release decade bar chart (Recharts) |

---

## Local Dev

```bash
# Copy real data for local dev (gitignored)
cp /path/to/aotw-website/data.json website/public/data.json

# Run website dev server
cd website && npm run dev

# Run bot locally
mamba run -n spotify-env python src/telegram_bot.py

# Run tests
mamba run -n spotify-env pytest tests/ --ignore=tests/test_add_album.py -v --asyncio-mode=auto
```

---

## Railway Env Vars

| Variable | Notes |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_ALLOWED_CHAT_ID` | Group chat ID |
| `SPOTIFY_CLIENT_ID` | From Spotify developer dashboard |
| `SPOTIFY_CLIENT_SECRET` | From Spotify developer dashboard |
| `GOOGLE_SHEET_ID` | Default: `1h1uDCZPqJovFfUKPzfPgUwUOHjFdCXHWVhUE6VvFA_s` |
| `GOOGLE_SHEET_TAB` | Sheet tab name |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Raw JSON string |
| `GITHUB_TOKEN` | Fine-grained PAT, Contents:write on `aotw-website` |
| `GITHUB_REPO_OWNER` | `davidgreenblott` |
| `GITHUB_REPO_NAME` | `aotw-website` |
| `WEBHOOK_SECRET_TOKEN` | Random hex string for webhook verification |
| `RAILWAY_PUBLIC_DOMAIN` | Auto-injected by Railway |
| `PORT` | Auto-injected by Railway |

---

## Key Design Decisions

- **Webhooks not polling** — `run_webhook()` eliminates Railway rolling-deploy conflict
- **No pick number in code** — sheet formula `=ROW()-1` handles it
- **Dedup by album ID** — checked against `spotify_album_url` column before any writes
- **No database** — Google Sheet is canonical; `data.json` is a generated copy pushed to GitHub
- **Partial failure safe** — if GitHub push fails after sheet write, returns `success: True, partial_failure: True`
- **Flat grid when sorted** — year grouping only shown on default (unsorted) picks page
- **Netlify cache** — 5-min `must-revalidate` for `data.json`, 1-year immutable for hashed assets
