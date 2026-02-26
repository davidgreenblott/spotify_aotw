# Album Club Automation Pipeline — Product Requirements Document

---

## Problem Statement

Members of an album club manually paste Spotify album links into a desktop GUI app, which fetches metadata and updates a Google Sheet. This process is tedious, error-prone, and requires a specific person to be at their computer. When someone forgets, the sheet falls out of date and the club loses track of past picks. There is no shared website or archive — just a raw spreadsheet.

## Target Users

**Club Members**: A small group of friends who pick a new "Album of the Week" (AOTW) in a Telegram group chat. They want zero-friction album logging and a visual archive they can browse and share.

**Admin (You)**: Maintains the pipeline infrastructure. Needs visibility into errors and the ability to debug failures without deep diving into logs on multiple platforms.

## Success Metrics

- Zero manual data entry after initial setup
- Pipeline processes a trigger message and appends to Google Sheets within 60 seconds
- Website rebuilds and reflects the new album within 90 seconds of sheet update
- Telegram bot uptime on Railway >99%
- Website Lighthouse performance score >90

---

## Capability Tree

### Capability: Telegram Bot Trigger
Monitors the album club Telegram group chat and initiates the pipeline when a member posts a trigger message containing a Spotify link.

#### Feature: Message Monitoring
- **Description**: Listen for incoming messages in the configured Telegram group chat
- **Inputs**: Telegram Bot API token, group chat ID
- **Outputs**: Raw message object with sender info and text content
- **Behavior**: Long-poll the Telegram Bot API for new messages; filter to the target group chat

#### Feature: Trigger Pattern Matching
- **Description**: Detect messages that match the AOTW trigger pattern and contain a Spotify album URL
- **Inputs**: Message text
- **Outputs**: Extracted Spotify URL and sender username, or null if no match
- **Behavior**: Apply configurable regex (e.g., `AOTW:` or bot mention + Spotify URL); extract the first valid Spotify album URL from the message

#### Feature: Bot Response
- **Description**: Reply in the Telegram chat with confirmation or error after pipeline execution
- **Inputs**: Pipeline result (success with album title/artist, or error message)
- **Outputs**: Telegram message sent to the group chat
- **Behavior**: On success, reply with album title, artist, and album art. On duplicate, notify that the album already exists. On error, reply with a user-friendly error message.

### Capability: Spotify Metadata Extraction
Fetches rich album metadata from the Spotify Web API given a Spotify album URL.

#### Feature: URL Parsing
- **Description**: Extract a Spotify album ID from various URL formats
- **Inputs**: Raw URL string (open.spotify.com/album/..., spotify:album:..., short links)
- **Outputs**: Album ID string, or error if URL is invalid
- **Behavior**: Regex-based extraction supporting multiple Spotify URL formats; validate that the extracted ID looks like a valid Spotify ID

#### Feature: Album Metadata Fetch
- **Description**: Call the Spotify API to retrieve full album metadata
- **Inputs**: Spotify album ID, Spotify API credentials
- **Outputs**: Structured metadata object (title, artist(s), release date, genres, album art URL, track count, Spotify URL)
- **Behavior**: Authenticate via client credentials flow using spotipy; call Get Album endpoint; fall back to artist genres if album genres are empty

### Capability: Google Sheets Storage
Appends album metadata to a shared Google Sheet that serves as the single source of truth.

#### Feature: Sheet Authentication
- **Description**: Authenticate with Google Sheets API using a service account
- **Inputs**: Service account JSON key file path, target spreadsheet ID
- **Outputs**: Authenticated gspread client
- **Behavior**: Load credentials from JSON key; authorize with gspread; open the target spreadsheet

#### Feature: Deduplication Check
- **Description**: Prevent duplicate album entries by checking if a Spotify URL already exists
- **Inputs**: Spotify URL, authenticated sheet client
- **Outputs**: Boolean (is duplicate)
- **Behavior**: Read column G (Spotify Link); return true if the URL already exists

#### Feature: Row Append
- **Description**: Append a new row of album metadata to the sheet
- **Inputs**: Metadata object (title, artist, release date, genre, art URL, track count, Spotify URL, date added, added by)
- **Outputs**: Success/failure
- **Behavior**: Map metadata fields to columns A-I; append to the next empty row; retry up to 3 times on API failure

### Capability: Pipeline Orchestration
Wires together URL parsing, metadata fetch, deduplication, and sheet append into a single reliable pipeline.

#### Feature: Pipeline Executor
- **Description**: Execute the full pipeline from Spotify URL to sheet append
- **Inputs**: Spotify URL string, sender username
- **Outputs**: Pipeline result (success with album info, duplicate notice, or error)
- **Behavior**: Parse URL → fetch metadata → check for duplicate → append row → trigger site rebuild. Wrap in try/catch with structured logging at each step.

#### Feature: Netlify Deploy Hook Trigger
- **Description**: Trigger a Netlify site rebuild after successfully appending a new album
- **Inputs**: Netlify deploy hook URL
- **Outputs**: HTTP response (success/failure)
- **Behavior**: POST to the Netlify deploy hook URL; log result; do not fail the pipeline if rebuild trigger fails

### Capability: Album Archive Website
A React application displaying all albums in a searchable, sortable, interactive grid.

#### Feature: Build-Time Data Fetch
- **Description**: Pull album data from Google Sheets at build time and generate a static JSON file
- **Inputs**: Google Sheets API credentials, spreadsheet ID
- **Outputs**: Static JSON file (albums.json) in the build output
- **Behavior**: Fetch all rows from the sheet; transform into a JSON array of album objects; write to public directory

#### Feature: Album Grid Display
- **Description**: Render album cards in a responsive grid layout
- **Inputs**: Album data (from static JSON)
- **Outputs**: Visual grid of album cards with art, title, artist, year
- **Behavior**: Responsive grid (3-4 cols desktop, 1-2 mobile); lazy-load album art images; hover/tap reveals genre, track count, and Spotify link

#### Feature: Search
- **Description**: Client-side full-text search across album title, artist, and genre
- **Inputs**: User query string, album data
- **Outputs**: Filtered album list
- **Behavior**: Instant filtering on keypress; case-insensitive matching; clear feedback when no results match

#### Feature: Sort & Filter
- **Description**: Sort albums by various fields and filter by genre
- **Inputs**: Sort field selection, genre filter selection
- **Outputs**: Reordered/filtered album list
- **Behavior**: Sort by date added (default, newest first), artist A-Z, title A-Z, or release year; genre tag chips for filtering

#### Feature: Dark Theme & Polish
- **Description**: Apply a polished dark visual theme with animations
- **Inputs**: None (design system)
- **Outputs**: Styled UI
- **Behavior**: Dark background with vibrant album art as focus; smooth hover animations; mobile-first responsive; accessible (keyboard nav, alt text, contrast)

---

## Repository Structure

```
album-club-pipeline/
├── bot/                        # Maps to: Telegram Bot Trigger
│   ├── telegram_bot.py         # Message monitoring + trigger matching
│   ├── responses.py            # Bot response formatting
│   └── __init__.py
├── pipeline/                   # Maps to: Pipeline Orchestration
│   ├── orchestrator.py         # Pipeline executor
│   ├── deploy_hook.py          # Netlify deploy hook trigger
│   └── __init__.py
├── spotify/                    # Maps to: Spotify Metadata Extraction
│   ├── url_parser.py           # URL parsing
│   ├── metadata.py             # Album metadata fetch
│   └── __init__.py
├── sheets/                     # Maps to: Google Sheets Storage
│   ├── auth.py                 # Sheet authentication
│   ├── dedup.py                # Deduplication check
│   ├── writer.py               # Row append
│   └── __init__.py
├── config/                     # Configuration & environment
│   ├── settings.py             # Env var loading, constants
│   └── __init__.py
├── website/                    # Maps to: Album Archive Website
│   ├── public/
│   │   └── albums.json         # Generated at build time
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── AlbumGrid.jsx   # Album grid display
│   │   │   ├── AlbumCard.jsx   # Individual album card
│   │   │   ├── SearchBar.jsx   # Search feature
│   │   │   ├── SortControls.jsx# Sort & filter
│   │   │   └── GenreChips.jsx  # Genre filter chips
│   │   └── hooks/
│   │       └── useAlbums.js    # Data loading + filtering logic
│   ├── scripts/
│   │   └── fetch_data.py       # Build-time data fetch from Sheets
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── test_url_parser.py
│   ├── test_metadata.py
│   ├── test_sheets.py
│   ├── test_orchestrator.py
│   └── test_bot.py
├── pyproject.toml
├── requirements.txt
├── Procfile                    # Railway process definition
└── README.md
```

## Module Definitions

### Module: config
- **Maps to capability**: Foundation (shared by all)
- **Responsibility**: Load and validate environment variables and constants
- **Exports**:
  - `Settings` — dataclass with all config (Telegram token, Spotify creds, Google service account path, sheet ID, Netlify hook URL)

### Module: spotify
- **Maps to capability**: Spotify Metadata Extraction
- **Responsibility**: Parse Spotify URLs and fetch album metadata
- **Exports**:
  - `parse_spotify_url(url) → album_id`
  - `fetch_album_metadata(album_id) → AlbumMetadata`

### Module: sheets
- **Maps to capability**: Google Sheets Storage
- **Responsibility**: Authenticate, deduplicate, and append rows to Google Sheets
- **Exports**:
  - `get_sheet_client() → gspread.Worksheet`
  - `is_duplicate(spotify_url) → bool`
  - `append_album(metadata) → bool`

### Module: pipeline
- **Maps to capability**: Pipeline Orchestration
- **Responsibility**: Wire together spotify + sheets + deploy hook into a single execution
- **Exports**:
  - `run_pipeline(spotify_url, added_by) → PipelineResult`

### Module: bot
- **Maps to capability**: Telegram Bot Trigger
- **Responsibility**: Listen for trigger messages and invoke the pipeline
- **Exports**:
  - `start_bot()` — entry point, starts polling

### Module: website
- **Maps to capability**: Album Archive Website
- **Responsibility**: React app for browsing the album archive
- **Exports**: Deployed static site on Netlify

---

## Dependency Chain

### Foundation Layer (Phase 0)
No dependencies — these are built first.

- **config**: Provides environment variable loading and validated settings used by every other module
- **spotify/url_parser**: Pure utility function with no external dependencies beyond regex

### Data Layer (Phase 1)
- **spotify/metadata**: Depends on [config, spotify/url_parser] — needs API credentials from config and album ID from URL parser
- **sheets/auth**: Depends on [config] — needs service account path and sheet ID
- **sheets/dedup**: Depends on [sheets/auth] — needs authenticated sheet client
- **sheets/writer**: Depends on [sheets/auth] — needs authenticated sheet client

### Orchestration Layer (Phase 2)
- **pipeline/orchestrator**: Depends on [spotify/url_parser, spotify/metadata, sheets/dedup, sheets/writer] — wires together the full data flow
- **pipeline/deploy_hook**: Depends on [config] — needs Netlify hook URL

### Integration Layer (Phase 3)
- **bot/telegram_bot**: Depends on [config, pipeline/orchestrator] — listens for messages and invokes the pipeline
- **bot/responses**: Depends on [spotify/metadata] — formats album metadata into Telegram messages

### Website Layer (Phase 4)
- **website/scripts/fetch_data**: Depends on [sheets/auth] — reads album data from Google Sheets at build time
- **website/src/components**: Depends on [website/scripts/fetch_data] — consumes the generated albums.json

### Deployment Layer (Phase 5)
- **Railway deployment**: Depends on [bot/telegram_bot, pipeline/orchestrator] — deploys the bot + pipeline as a long-running process
- **Netlify deployment**: Depends on [website/src/components, website/scripts/fetch_data] — deploys the React app with build-time data fetch

---

## Development Phases

### Phase 0: Foundation
**Goal**: Establish project scaffolding, configuration, and the simplest utility (URL parsing) so all subsequent modules can build on top.

**Entry Criteria**: Clean repository initialized

**Tasks**:
- [ ] Initialize Git repo with Python project structure (pyproject.toml, requirements.txt, README) (depends on: none)
  - Acceptance criteria: `pip install -e .` works; linting passes
  - Test strategy: CI runs ruff/black checks
- [ ] Implement `config/settings.py` with environment variable loading (depends on: none)
  - Acceptance criteria: Settings dataclass loads all required env vars; raises clear errors for missing vars
  - Test strategy: Unit test with mock env vars
- [ ] Implement `spotify/url_parser.py` (depends on: none)
  - Acceptance criteria: Correctly extracts album ID from open.spotify.com, spotify:album:, and short link formats; returns error for invalid URLs
  - Test strategy: Unit tests covering all URL formats + edge cases

**Exit Criteria**: Project installable, config loads, URL parser tested

**Delivers**: Foundation that all other modules import from

---

### Phase 1: Spotify + Google Sheets Clients
**Goal**: Standalone functions that can fetch album metadata and read/write the Google Sheet — testable independently via CLI.

**Entry Criteria**: Phase 0 complete

**Tasks**:
- [ ] Register Spotify app and implement `spotify/metadata.py` using spotipy (depends on: config, url_parser)
  - Acceptance criteria: Given a valid album ID, returns complete AlbumMetadata object with all required fields; handles missing genre gracefully by falling back to artist genres
  - Test strategy: Unit test with mocked Spotify API responses; one integration test against real API
- [ ] Set up GCP project, service account, and implement `sheets/auth.py` (depends on: config)
  - Acceptance criteria: Returns authenticated gspread worksheet; raises clear error if credentials are invalid
  - Test strategy: Integration test connecting to a test spreadsheet
- [ ] Implement `sheets/dedup.py` (depends on: sheets/auth)
  - Acceptance criteria: Returns True for existing Spotify URLs, False for new ones
  - Test strategy: Unit test with mocked sheet data
- [ ] Implement `sheets/writer.py` (depends on: sheets/auth)
  - Acceptance criteria: Appends a row with all 9 columns; retries up to 3 times on failure
  - Test strategy: Integration test appending to a test sheet

**Exit Criteria**: Can run `python -c "from spotify import fetch_album_metadata; print(fetch_album_metadata('ALBUM_ID'))"` and see metadata; can append a row to Google Sheets programmatically

**Delivers**: Working Spotify and Sheets clients usable from any entry point

---

### Phase 2: Pipeline Orchestration
**Goal**: A single function that takes a Spotify URL and sender name, runs the full pipeline, and returns a result. This is the core product logic.

**Entry Criteria**: Phase 1 complete (Spotify client and Sheets client working)

**Tasks**:
- [ ] Implement `pipeline/orchestrator.py` (depends on: spotify/url_parser, spotify/metadata, sheets/dedup, sheets/writer)
  - Acceptance criteria: `run_pipeline(url, sender)` parses URL → fetches metadata → checks duplicate → appends row → returns PipelineResult; structured logging at each step; errors caught and returned gracefully
  - Test strategy: Unit test with all dependencies mocked; integration test with real APIs
- [ ] Implement `pipeline/deploy_hook.py` (depends on: config)
  - Acceptance criteria: POSTs to configured Netlify deploy hook URL; logs success/failure; does not throw if hook fails
  - Test strategy: Unit test with mocked HTTP; integration test against real hook
- [ ] Wire deploy hook into orchestrator (depends on: pipeline/orchestrator, pipeline/deploy_hook)
  - Acceptance criteria: After successful append, deploy hook is triggered; pipeline still succeeds if hook fails
  - Test strategy: Integration test

**Exit Criteria**: `run_pipeline("https://open.spotify.com/album/xyz", "username")` works end-to-end from CLI

**Delivers**: Complete pipeline logic, runnable as a script for manual testing

---

### Phase 3: Telegram Bot
**Goal**: A running Telegram bot that listens in the group chat and triggers the pipeline automatically. This is the user-facing trigger.

**Entry Criteria**: Phase 2 complete (pipeline orchestrator works end-to-end)

**Tasks**:
- [ ] Create Telegram bot via BotFather, implement `bot/telegram_bot.py` with message handler (depends on: config, pipeline/orchestrator)
  - Acceptance criteria: Bot connects to Telegram; receives messages in the target group; matches trigger pattern; invokes `run_pipeline`; sends confirmation or error reply
  - Test strategy: Unit test message handler with mocked pipeline; manual integration test in Telegram
- [ ] Implement `bot/responses.py` for formatting bot replies (depends on: spotify/metadata types)
  - Acceptance criteria: Formats success message with album title, artist, and art; formats duplicate and error messages clearly
  - Test strategy: Unit test response formatting
- [ ] Deploy bot to Railway (depends on: bot/telegram_bot)
  - Acceptance criteria: Bot runs persistently on Railway; environment variables configured; bot responds within 5 seconds of trigger message
  - Test strategy: Manual end-to-end test: send trigger in Telegram → verify sheet updated

**Exit Criteria**: Send a trigger message in Telegram → album appears in Google Sheet within 60 seconds

**Delivers**: Fully automated trigger. Club members can now add albums by sending a message.

---

### Phase 4: Website MVP
**Goal**: A live React website on Netlify that displays the album archive with search and sort. Get to something visible as fast as possible.

**Entry Criteria**: Phase 1 complete (Sheets client works — website doesn't depend on bot)

**Tasks**:
- [ ] Scaffold React + Vite project in `website/` (depends on: none within website)
  - Acceptance criteria: `npm run dev` serves a page; `npm run build` produces static output; deployed to Netlify
  - Test strategy: Build succeeds; Netlify deploy preview works
- [ ] Implement `website/scripts/fetch_data.py` build-time data fetcher (depends on: sheets/auth)
  - Acceptance criteria: Fetches all rows from Google Sheet; outputs `albums.json` in `website/public/`; runs as part of Netlify build command
  - Test strategy: Script produces valid JSON matching expected schema
- [ ] Build `AlbumCard` and `AlbumGrid` components (depends on: React scaffold, fetch_data)
  - Acceptance criteria: Renders album cards with art, title, artist, year in responsive grid; lazy-loads images; hover reveals genre + track count + Spotify link
  - Test strategy: Visual review; responsive at 320px, 768px, 1280px widths
- [ ] Build `SearchBar` component (depends on: AlbumGrid)
  - Acceptance criteria: Filters albums by title, artist, genre on keypress; shows "no results" state
  - Test strategy: Type "Beatles" → only Beatles albums shown
- [ ] Build `SortControls` and `GenreChips` components (depends on: AlbumGrid)
  - Acceptance criteria: Sort by date added, artist, title, release year; genre chips filter by genre
  - Test strategy: Click sort → order changes correctly; click genre → filters correctly
- [ ] Set up Netlify deploy hook and wire into pipeline (depends on: Netlify deployment, pipeline/deploy_hook)
  - Acceptance criteria: After pipeline appends a row, Netlify rebuilds; new album appears on site within 90 seconds
  - Test strategy: End-to-end: trigger in Telegram → album on website

**Exit Criteria**: Live website at a Netlify URL showing all albums with working search and sort

**Delivers**: The full user-facing product — browse, search, sort the album archive

---

### Phase 5: Polish & Hardening
**Goal**: Dark theme, animations, monitoring, and end-to-end tests.

**Entry Criteria**: Phases 3 and 4 complete

**Tasks**:
- [ ] Apply dark theme and design polish (depends on: website components)
  - Acceptance criteria: Dark background, vibrant album art focus, smooth hover animations, mobile-first responsive, accessible (keyboard nav, alt text, WCAG contrast)
  - Test strategy: Lighthouse accessibility score >90; visual review on mobile
- [ ] Add structured logging and Telegram error notifications (depends on: bot, pipeline)
  - Acceptance criteria: Pipeline logs each step with structured JSON; errors send a message to a Telegram admin chat or the group; Railway health checks configured
  - Test strategy: Trigger an intentional failure → error notification received
- [ ] Write end-to-end integration tests (depends on: all previous phases)
  - Acceptance criteria: Automated test covering: Telegram trigger → metadata fetch → sheet append → Netlify rebuild → album visible on site
  - Test strategy: CI-runnable test suite with mocked external services

**Exit Criteria**: Production-ready system with monitoring and test coverage

**Delivers**: Reliable, polished product ready for ongoing use

---

## Test Pyramid

```
        /\
       /E2E\       ← 10% (Full pipeline: Telegram → Sheet → Website)
      /------\
     /Integration\ ← 30% (Spotify API, Sheets API, Telegram Bot API)
    /------------\
   /  Unit Tests  \ ← 60% (URL parser, dedup logic, response formatting, filters)
  /----------------\
```

## Coverage Requirements
- Line coverage: 80% minimum
- Branch coverage: 70% minimum
- Function coverage: 90% minimum

## Critical Test Scenarios

### Spotify URL Parser
**Happy path**: open.spotify.com/album/6dVIqQ8qmQ5GBnJ9shOYGE → extracts ID correctly
**Edge cases**: URLs with query params (?si=...), short links, spotify: URI format
**Error cases**: Non-Spotify URLs, playlist URLs, track URLs, empty string

### Pipeline Orchestrator
**Happy path**: Valid URL → metadata fetched → not duplicate → appended → deploy hook triggered
**Edge cases**: Album with no genres (falls back to artist genres); very long artist names
**Error cases**: Invalid URL, Spotify API down (retry logic), Sheets API down (retry logic), duplicate album (skip + notify)
**Integration**: Full pipeline from URL string to sheet row

### Telegram Bot
**Happy path**: Trigger message with valid Spotify URL → pipeline runs → confirmation reply
**Edge cases**: Message with multiple URLs (take first); trigger keyword in different cases
**Error cases**: No Spotify URL in message; Spotify URL for non-album (track, playlist)

---

## System Components

| Component | Technology | Hosting | Purpose |
|-----------|-----------|---------|---------|
| Telegram Bot | python-telegram-bot | Railway (long-running) | Monitors group chat, triggers pipeline |
| Pipeline | Python 3.11+ | Railway (same process as bot) | Orchestrates URL → metadata → sheet → rebuild |
| Spotify Client | spotipy | — (library) | Fetches album metadata from Spotify Web API |
| Sheets Client | gspread + google-auth | — (library) | Reads/writes Google Sheets via service account |
| Website | React + Vite | Netlify (static) | Album archive with search/sort/filter |
| Build Script | Python | Netlify (build step) | Fetches sheet data → generates albums.json |

## Data Models

### AlbumMetadata
```python
@dataclass
class AlbumMetadata:
    title: str
    artist: str          # Comma-joined if multiple
    release_date: str    # YYYY-MM-DD
    genres: str          # Comma-joined
    art_url: str         # 640px album art
    track_count: int
    spotify_url: str
    date_added: str      # ISO timestamp
    added_by: str        # Telegram username
```

### Google Sheet Schema
| Column | Field | Example |
|--------|-------|---------|
| A | Title | OK Computer |
| B | Artist | Radiohead |
| C | Release Date | 1997-06-16 |
| D | Genre | alternative rock, art rock |
| E | Art URL | https://i.scdn.co/image/... |
| F | Tracks | 12 |
| G | Spotify Link | https://open.spotify.com/album/... |
| H | Date Added | 2026-02-23T14:30:00Z |
| I | Added By | @username |

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | Python 3.11+ | Rich ecosystem for all three APIs (Telegram, Spotify, Sheets) |
| Telegram | python-telegram-bot | Well-maintained, async support, simple polling setup |
| Spotify | spotipy | De facto Python Spotify client, handles auth + pagination |
| Sheets | gspread + google-auth | Clean API, service account support, widely used |
| Frontend | React + Vite | Fast builds, component model, large ecosystem |
| Bot Hosting | Railway | Persistent process hosting, easy env vars, affordable |
| Site Hosting | Netlify | Free tier, deploy hooks, automatic builds from Git |
| CI | GitHub Actions | Free, integrates with both Railway and Netlify |

---

## Technical Risks

**Risk**: Spotify album genres are often empty
- **Impact**: Medium — genre filtering on the website would be sparse
- **Likelihood**: High — Spotify's genre data is notoriously incomplete at the album level
- **Mitigation**: Fall back to artist genres via a second API call
- **Fallback**: Allow manual genre tagging via a Telegram bot command

**Risk**: Google Sheets API rate limits
- **Impact**: Low — we're doing ~1 write per week
- **Likelihood**: Low
- **Mitigation**: Retry with exponential backoff (3 attempts)
- **Fallback**: Queue writes and batch them

**Risk**: Railway free tier limitations
- **Impact**: Medium — bot could go down if hours are exhausted
- **Likelihood**: Medium — depends on Railway's current free tier
- **Mitigation**: Monitor usage; bot is lightweight (minimal CPU/RAM)
- **Fallback**: Move to a $5/month hobby plan or self-host on a VPS

**Risk**: Netlify build times for data fetch
- **Impact**: Low — delays between trigger and site update
- **Likelihood**: Low — build is simple (fetch JSON + build React)
- **Mitigation**: Keep build lean; cache node_modules
- **Fallback**: Switch to client-side fetch from a published sheet CSV if build times are unacceptable

## Scope Risks

**Risk**: Feature creep into ratings, reviews, or multi-platform support
- **Impact**: High — delays core delivery
- **Mitigation**: Strict v1 scope (this PRD); ratings and Discord/iMessage support are explicitly non-goals
- **Fallback**: Maintain a backlog for v2 features

---

## Glossary

- **AOTW**: Album of the Week — the weekly album pick by a club member
- **Deploy Hook**: A webhook URL that triggers a site rebuild on Netlify
- **Service Account**: A Google Cloud identity used for server-to-server API auth (no user login required)
- **Polling**: The Telegram bot repeatedly asks the API "any new messages?" (simpler than webhooks)
- **spotipy**: Python library for the Spotify Web API
- **gspread**: Python library for Google Sheets
