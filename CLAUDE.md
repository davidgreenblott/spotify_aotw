# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A PyQt5 GUI application for adding Spotify albums to a master tracking Google Sheet (Album of the Week). The app fetches album metadata from Spotify and appends it as a new row to a configured Google Sheet.

## Environment Setup

```bash
mamba env create -f environment.yml
mamba activate spotify-env
```

## Common Commands

**Run the GUI:**
```bash
python src/add_album_gui.py
```

**Run the CLI:**
```bash
./run.sh "https://open.spotify.com/album/..."
# Or: python src/add_album.py --url "https://open.spotify.com/album/..."
```

**Run tests:**
```bash
pytest tests/test_add_album.py
```

**Run a single test:**
```bash
pytest tests/test_add_album.py::test_get_album_info
```

## Architecture

The project has two layers:

**GUI Layer** (`src/add_album_gui.py`): `AlbumWindow` (PyQt5) accepts a Spotify URL and calls the core logic.

**Core Logic** (`src/add_album.py`): Main entry point is `add_album(url, sheet_id, sheet_tab, creds_path)`, which:
1. Calls `get_spotify_api()` using credentials from `spotify_credentials.json`
2. Calls `get_album_info(url, spot_api)` → returns artist, album name, year, Spotify URL, artwork URL (uses image index `[1]`)
3. Calls `get_google_sheet(sheet_id, sheet_tab, creds_path)` via `gspread` service account auth
4. Reads the sheet's existing rows to determine the next pick number and date (weekly increments)
5. Appends a new row built by `build_row_from_header()`

The sheet structure is discovered dynamically: `find_header_cells()` uses regex to locate "Pick" and "Date" columns, so column order in the sheet is flexible.

## Testing

Always write unit tests for new functions and any significant changes. Use `pytest`.

- Cover the happy path, sad path (expected failures/errors), and edge cases
- Mock all external API calls (Spotify, Google Sheets) so tests don't require live credentials or network access
- Place tests in a `tests/` directory mirroring the structure of the main code
- Tests should be runnable with `pytest` from the project root

## External Credentials (gitignored)

- `spotify_credentials.json` — Spotify API client credentials
- `aotw-488201-8465cf54c9d9.json` — Google service account key (default path; can be overridden via CLI arg)
- `aotw_master_list.xlsx` — legacy local Excel file, no longer used

## Key Design Notes

- Date parsing (`parse_sheet_date`) handles multiple formats: `MM/DD/YYYY`, `YYYY-MM-DD`, and ISO timestamps.
- The next date is always computed as a weekly increment from the last entry in the sheet.
- Tests in `test_add_album.py` make real Spotify API calls and require valid credentials to run.
