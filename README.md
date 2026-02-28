# Album of the Week — Automated Pipeline

End-to-end system for a music club: post a Spotify album link in Telegram, it logs to Google Sheets and updates a public website automatically.

## Features

- Telegram bot trigger (`@aotw <spotify_url>`)
- URL validation and duplicate detection
- Google Sheets as canonical data store
- React website with search and filter
- Auto-deploy to Netlify on every new pick
- Direct Spotify API integration for metadata

## Tech Stack

| Layer | Tech |
|---|---|
| Bot | python-telegram-bot, Railway |
| Backend | Python 3.10, spotipy, gspread |
| Website | React + Vite, Netlify |
| Data flow | Google Sheets → JSON → GitHub → Netlify |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRIGGER                                  │
│  Telegram Group: "@aotw https://open.spotify.com/album/..."     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BACKEND (Railway)                              │
│                                                                 │
│  telegram_bot.py  ──►  pipeline.py (7 steps)                   │
│  (webhook mode)         │                                       │
│                         ├─ 1. validate URL       validation.py  │
│                         ├─ 2. dedup check        add_album.py   │
│                         ├─ 3. Spotify fetch      add_album.py   │
│                         ├─ 4. validate metadata  validation.py  │
│                         ├─ 5. Google Sheet append add_album.py  │
│                         ├─ 6. export Google Sheet as JSON       │
│                         │                        export_json.py │
│                         └─ 7. GitHub push        github_push.py │
└──────────┬──────────────────────────────┬──────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────┐           ┌──────────────────────┐
│  Google Sheets   │           │  GitHub Repo          │
│  (canonical DB)  │           │  (data.json)          │
│                  │           └──────────┬───────────┘
│  - All picks     │                      │
│  - Row formula   │                      │ auto-deploy
│    =ROW()-1      │                      ▼
└──────────────────┘           ┌──────────────────────┐
                               │  Netlify (website)   │
                               │                      │
                               │  Picks page          │
                               │  Analytics page      │
                               │  About page          │
                               │                      │
                               │  reads /data.json    │
                               └──────────────────────┘
```

**External APIs:** Spotify (album metadata), Google Sheets API (read/write), GitHub Contents API (file push), Telegram Bot API (webhook).

## How It Works

1. Someone posts `@aotw https://open.spotify.com/album/...` in the Telegram group
2. The bot validates the URL and checks for duplicates
3. Album metadata is fetched from Spotify
4. A new row is appended to the Google Sheet
5. The full sheet is exported as `data.json` and pushed to the website GitHub repo
6. Netlify detects the commit and redeploys — site updates within ~1 minute

## Local Development

```bash
mamba env create -f environment.yml
mamba activate spotify-env
cp .env.example .env
# Fill in .env with your credentials
python src/telegram_bot.py
```

## Website Development

```bash
cd website/
npm install
npm run dev
```

## Tests

```bash
# All mocked tests (no credentials needed)
mamba run -n spotify-env pytest tests/ --ignore=tests/test_add_album.py -v --asyncio-mode=auto

# Live Spotify API tests (requires valid credentials)
mamba run -n spotify-env pytest tests/test_add_album.py -v
```

## Deployment

- **Bot**: See [DEPLOYMENT.md](DEPLOYMENT.md) for Railway setup
- **Website**: See [DEPLOYMENT_WEBSITE.md](DEPLOYMENT_WEBSITE.md) for Netlify setup

## Project Structure

```
src/                    # Python backend
  telegram_bot.py       # Bot: polls Telegram, triggers pipeline
  pipeline.py           # Orchestrator: validate → dedup → fetch → append → push
  add_album.py          # Core: Spotify fetch + Google Sheets append
  export_json.py        # Sheet → normalised data.json
  github_push.py        # Push data.json to GitHub via Contents API
  validation.py         # URL + metadata validation
  retry_utils.py        # Exponential backoff decorator
  logging_config.py     # Structured stdout logging

tests/                  # pytest test suite (87+ tests, all mocked)

website/                # React frontend
  src/
    App.jsx
    components/         # AlbumGrid, AlbumCard, SearchBar, FilterBar
    hooks/useAlbums.js
    utils/filterSort.js
  public/data.json      # Sample data; real data pushed by pipeline
```
