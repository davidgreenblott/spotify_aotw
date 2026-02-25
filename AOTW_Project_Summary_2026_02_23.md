# Album of the Week — Automation & Website Project (v3)

## What We're Building

An end-to-end automated pipeline for an "Album of the Week" music club. When a club member posts a Spotify album link in a Telegram group chat, the system automatically pulls album metadata, logs it to a Google Sheet, and updates a public-facing website — no manual data entry required.

## Current State

We have a working **PyQt5 GUI application** (`add_album_gui.py`) that:

- Accepts a Spotify album URL
- Fetches metadata via the Spotify API (artist, album name, year, artwork URL, Spotify link)
- Appends a new row to a Google Sheet (via `gspread` with a service account)
- Auto-calculates the next pick number and date (weekly increments)
- Discovers sheet structure dynamically using regex on header cells

The core logic lives in `add_album.py` with functions like `get_album_info()`, `get_google_sheet()`, `build_row_from_header()`, and `parse_sheet_date()`.

There are currently **300+ albums** in the sheet, with one new album added each week (typically Sunday or Monday).

---

## Target Architecture

```
Telegram Group Chat (whitelisted chat ID only)
    │  member posts: "@aotw https://open.spotify.com/album/..."
    │
    ▼
Telegram Bot (python-telegram-bot, polling mode)
    │  regex validates keyword + Spotify album URL
    │  hosted on Railway (free tier)
    │
    ▼
Validation Layer
    │  ├── URL is a Spotify *album* link (not track/playlist/artist)
    │  ├── Spotify API returns all required fields
    │  └── Dedup check: album ID not already in sheet
    │
    ▼
Pipeline (Python, reusing existing add_album.py logic)
    ├──► Google Sheet (append row via gspread — canonical backup, human-editable)
    │     └── Pick # derived from formula column (=ROW()-1), not computed by code
    └──► Read full sheet → generate data.json (with cached derived fields)
              │
              ▼
         Push data.json to GitHub repo via GitHub REST API
              │  (retry up to 3x with backoff on transient failures)
              ▼
         Netlify detects new commit → auto-deploys static site
              │
              ▼
         Public Website (React + Vite, served as static files from Netlify CDN)
```

---

## How the Data Gets to the Website

There is no database. The website repo on GitHub contains the frontend code AND a single `data.json` file with all album data. When the pipeline runs, it updates `data.json` in the repo via the GitHub API (a single REST call — no git CLI or SSH keys needed on Railway). Netlify watches the repo and re-deploys on every commit.

At deploy time, Netlify copies everything from the repo and serves it as static files on its CDN. The deployed site looks like:

```
index.html
app.js
styles.css
data.json     ← all 300+ albums, ~200-500KB, one flat file
```

When a user visits the site, their browser downloads `data.json` and React handles all filtering, sorting, and rendering client-side. No database, no server, no API calls at page load. For a few hundred records that update once a week, a single JSON file is the simplest and cheapest approach.

---

## Component Breakdown

### 1. Trigger — Telegram Bot

- **Library**: `python-telegram-bot`
- **Hosting**: Railway (free tier, ~$5/mo credit, more than enough for a bot that's idle 99% of the time)
- **Mode**: Polling (simple, low traffic — no need for webhooks)
- **Behavior**: Bot sits in a Telegram group chat. When a message matches a pattern like `@aotw <spotify_url>`, it extracts the URL and triggers the pipeline. Bot replies with a confirmation message in the chat (e.g., "Added *Album Name* by *Artist* — Pick #312 ✅").
- **Access control**: Bot only responds to messages from a whitelisted Telegram chat ID. Messages from other chats are ignored silently.
- **Scope**: Core pipeline only — no additional bot features for now.

### 2. Validation Layer

Before writing anything to the sheet or committing JSON, the pipeline validates:

**Input validation:**
- Message matches trigger pattern (`@aotw <url>`)
- URL is a Spotify **album** URL (not track, playlist, or artist) — validated via regex

**Spotify response validation:**
- Required fields present: artist name, album name, release year, artwork URL, Spotify link
- Fail fast with a clear Telegram error message if any are missing

**Deduplication:**
- Check existing sheet rows for matching Spotify album ID
- If duplicate: do not append, reply with "Already added — Pick #X on [date]"

**On any validation failure:**
- Do not write to sheet or push to GitHub
- Reply in Telegram with a clear error: "Couldn't add this album (reason: …). Please post a Spotify album link."
- Log the failure

### 3. Pipeline — Spotify + Google Sheets + JSON Export

- **Spotify API**: Existing `get_album_info()` fetches artist, album, year, artwork URL, Spotify link
- **Google Sheets**: Existing `add_album()` appends a row using `gspread` service account auth
- **Pick number**: Derived from a formula column in the sheet (`=ROW()-1`), not computed by the pipeline. The pipeline writes the row without a pick number; the sheet formula fills it in automatically. This eliminates race conditions.
- **JSON Export**: After appending to the sheet, read the full sheet and generate `data.json` with these fields per album:
  - `spotify_album_id` (string — unique key, used for dedup)
  - `pick_number` (int — read from the formula column)
  - `picked_at` (ISO date string — normalized from whatever format the sheet uses)
  - `artist`, `album`, `year`, `artwork_url`, `spotify_url`, `picker`
- **Push to GitHub**: Via GitHub REST API. Retry up to 3 times with exponential backoff on transient failures (429, 5xx, timeouts).
- **Trigger frequency**: Runs once per week when a member posts a new album pick. Not on a cron — triggered directly by the Telegram message.
- **Google Sheet role**: Canonical backup and human-editable record. Not exposed publicly. If the JSON ever gets corrupted, it can be regenerated from the sheet.

### 4. Partial Failure Handling

The pipeline handles mid-pipeline failures gracefully:

- **Spotify fails**: Telegram reply with error, nothing written.
- **Sheet write succeeds but GitHub push fails**: Data is safe in the sheet. Telegram reply: "Added to sheet ✅, website update pending (will sync on next run)." Next successful run regenerates JSON from the full sheet, so it self-heals.
- **All retries exhausted**: Log the failure, notify in Telegram, data remains consistent in the sheet.

### 5. Logging

- **Where**: Railway captures stdout automatically. Use Python's `logging` module to print structured output.
- **What to log** (at minimum):
  - Message received (who, what URL)
  - Spotify lookup result (success/error, latency)
  - Sheet append result (success/error, row number)
  - GitHub push result (success/error)
- **Keep it simple**: No external log services, no request ID correlation, no Sentry — Railway logs are sufficient for a once-a-week pipeline. Can add Sentry later if needed.

### 6. Website — Static Album Grid

- **Framework**: React (via Vite for fast builds and small bundle)
- **Hosting**: Netlify (auto-deploys from GitHub repo on push, serves static files from CDN)
- **Data source**: `data.json` fetched at page load (~200-500KB for 300+ albums)
- **Design**: Minimal, clean, dark mode
- **Features**:
  - Interactive grid of album art cards
  - Each card shows: artwork, artist, album name, year, date picked, who picked it
  - **Not all albums rendered at once** — paginated or filtered by year to keep performance snappy
  - Real-time search/filter bar
  - Sort by: date, artist, album, picker, genre, year
  - Click card → opens Spotify link or expands with more detail
  - Album artwork served directly from Spotify CDN (no image hosting needed)

**Why React over vanilla JS**: With 300+ albums plus search, sort, year-based filtering, and growing data, React keeps the code organized. Vanilla JS would work but gets messy at this scale of interactivity. Vite keeps the build fast and the bundle small.

---

## Security

### Credential Management
- **All secrets stored in Railway environment variables** — never in code, never committed to any repo
  - Telegram bot token
  - Spotify client ID + client secret
  - Google service account JSON (or its contents as an env var)
  - GitHub personal access token
- **`.gitignore`** covers all credential files (already in place)

### Token Scoping (principle of least privilege)
- **GitHub token**: Fine-grained personal access token scoped to only the website repo, with only "Contents: write" permission. If leaked, blast radius is one repo.
- **Google service account**: Sheet shared only with the service account email. No broader Google Cloud access.
- **Telegram bot token**: Treat as a password. Revocable instantly via @BotFather if compromised.

### Bot Access Control
- **Whitelist the Telegram group chat ID**: Bot only processes messages from the specific album club chat. Messages from other chats (if bot is added elsewhere) are silently ignored.
- Optional: whitelist specific user IDs within the group for an additional layer.

### Logging Safety
- **Never log secrets**: Ensure logging does not accidentally dump tokens, API keys, or service account contents. Redact or exclude sensitive fields.

---

## Tech Stack Summary

| Component         | Technology                          | Hosting/Cost          |
|-------------------|-------------------------------------|-----------------------|
| Group chat        | Telegram                            | Free                  |
| Bot               | python-telegram-bot (polling)       | Railway (free tier)   |
| Album metadata    | Spotify Web API (spotipy)           | Free                  |
| Data backup       | Google Sheets (gspread)             | Free (Google Cloud)   |
| Website data      | data.json (generated from sheet)    | GitHub repo (free)    |
| Website frontend  | React + Vite                        | Netlify (free tier)   |
| Deploy trigger    | GitHub commit → Netlify auto-deploy | Free                  |

**Total ongoing cost: $0** (all services on free tiers)

**Note**: Railway free tier may sleep inactive services. If the bot misses messages due to sleeping, upgrade to the $5/month hobby tier. This is the only potential cost.

---

## Key Design Decisions

1. **Telegram over iMessage/Discord** — proper bot API, runs in the cloud, no always-on Mac required
2. **Railway for bot hosting** — free tier is sufficient, easy GitHub repo connection, no server management
3. **Google Sheet as backup, JSON as primary site data** — sheet stays private, JSON is a generated copy pushed to GitHub
4. **No database** — a single JSON file is sufficient for hundreds of albums updating once per week
5. **Pick # from sheet formula** — eliminates race conditions, zero code needed
6. **Validation before writes** — URL check, required fields, dedup prevents bad data
7. **GitHub API for pushing data** — simpler than git CLI from a container, just a REST call
8. **Netlify for website hosting** — free, fast CDN, custom domain support, auto-deploys from GitHub
9. **React + Vite for frontend** — handles 300+ albums with search/sort/filter cleanly, small bundle
10. **Year-based pagination** — avoids rendering all albums at once, keeps the site fast as data grows
11. **All secrets in env vars, tokens scoped to minimum permissions** — defense in depth

---

## Implementation Priorities

### Do Now (high value, low effort)
- Formula-based Pick # column in the sheet (`=ROW()-1`)
- URL validation + Spotify response validation + dedup check
- Bot whitelist (restrict to specific Telegram group chat ID)
- All secrets in Railway env vars with proper token scoping
- Basic stdout logging via Python `logging`
- Simple retry wrapper (2-3 attempts with backoff) for API calls
- Clear Telegram error/success messages

### Do Now (keep simple)
- `spotify_album_id`, `pick_number`, `picked_at` (ISO) in `data.json`
- Partial failure handling (sheet OK but GitHub failed → inform user, self-heals next run)

### Skip for Now
- Normalized/lowercase search fields in JSON (JS handles this fine client-side)
- JSON schema validation (if sheet data is valid, JSON will be valid)
- Request ID correlation in logs
- Sentry / external logging services
- Concurrency locking (weekly frequency makes this a non-issue)
- Schema versioning in JSON
- Additional bot features (status commands, analytics, etc.)
