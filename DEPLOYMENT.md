# Deployment Guide — Album of the Week Bot

The bot runs as a background worker on [Railway](https://railway.app).
It polls Telegram for messages, processes album submissions, updates the Google Sheet,
and pushes `data.json` to GitHub so the frontend website auto-updates.

---

## Architecture

```
Telegram group
     │  @aotw <spotify_url>
     ▼
telegram_bot.py  (Railway worker)
     │
     ▼
pipeline.py
  ├── validation.py       — URL format check
  ├── add_album.py        — dedup + Spotify fetch + sheet append
  ├── export_json.py      — read full sheet → data.json
  └── github_push.py      — push data.json to website repo
```

---

## Railway Setup

### 1. Create a new Railway project

1. Go to [railway.app](https://railway.app) and log in
2. Click **New Project → Deploy from GitHub repo**
3. Select the `spotify_aotw` repository
4. Railway will detect `railway.json` and use Nixpacks to build

### 2. Add environment variables

In the Railway dashboard go to your service → **Variables** and add all of the following:

#### Telegram
| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) — create a bot and copy the token |
| `TELEGRAM_ALLOWED_CHAT_ID` | The numeric ID of your Telegram group. Get it by adding [@RawDataBot](https://t.me/RawDataBot) to the group, or checking the bot logs on first message |

#### Spotify
| Variable | Description |
|---|---|
| `SPOTIFY_CLIENT_ID` | From [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | From Spotify Developer Dashboard |

#### Google Sheets
| Variable | Description |
|---|---|
| `GOOGLE_SHEET_ID` | The long ID from the sheet URL: `docs.google.com/spreadsheets/d/<ID>/edit` |
| `GOOGLE_SHEET_TAB` | Sheet tab name (default: `Sheet1`) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | **Full JSON content** of the service account key file (paste the entire contents of the `.json` file — Railway supports large env vars) |

> **Tip:** Open your service account `.json` file, select all, and paste the entire contents as the value. The app detects that it starts with `{` and handles it automatically — no file upload needed.

#### GitHub (for website auto-update)
| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | A fine-grained Personal Access Token with **Contents: Read and Write** permission on the website repo |
| `GITHUB_REPO_OWNER` | Your GitHub username |
| `GITHUB_REPO_NAME` | The website repo name (e.g. `aotw-website`) |

### 3. Deploy

Railway deploys automatically when you push to the connected branch.
To trigger a manual redeploy: **Dashboard → your service → Redeploy**.

---

## Verifying the deployment

1. Check Railway logs for:
   ```
   Bot starting in polling mode...
   ```
2. Send a test message to your Telegram group:
   ```
   @aotw https://open.spotify.com/album/...
   ```
3. The bot should reply within a few seconds. Check Railway logs for the full pipeline trace.
4. Verify the Google Sheet has a new row.
5. Verify a new commit appeared on the website GitHub repo.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Bot doesn't respond | `TELEGRAM_BOT_TOKEN` or `TELEGRAM_ALLOWED_CHAT_ID` wrong |
| "Failed to access Google Sheet" | `GOOGLE_SERVICE_ACCOUNT_JSON` malformed or service account not shared on the sheet |
| "Couldn't fetch album info from Spotify" | `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` wrong or expired |
| Album added to sheet but no GitHub commit | `GITHUB_TOKEN` missing or doesn't have write access to the repo |
| Bot crashes on startup | Check Railway build logs — likely a missing dependency in `requirements.txt` |

---

## Local development

See `environment.yml` for the full conda environment.

```bash
mamba env create -f environment.yml
mamba activate spotify-env

# Run the bot locally (requires all env vars set in your shell or a .env file)
python src/telegram_bot.py

# Run the GUI
python src/add_album_gui.py

# Run tests
pytest tests/ --ignore=tests/test_add_album.py --asyncio-mode=auto
```

Credentials for local dev:
- `spotify_credentials.json` — Spotify client ID/secret (gitignored)
- `aotw-488201-8465cf54c9d9.json` — Google service account key (gitignored)
