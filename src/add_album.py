import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional
import os
import re
import gspread
from gspread.exceptions import GSpreadException
from validation import extract_spotify_album_id
from logging_config import setup_logging

logger = setup_logging()
try:
    from gspread.exceptions import CellNotFound
except ImportError:  # older gspread
    try:
        from gspread import CellNotFound
    except ImportError:
        CellNotFound = Exception


def get_user_args():
    """Accepts user input from command line
    """
    parser = argparse.ArgumentParser(
                description='Add url')
    parser.add_argument('--url',
                        type=str,
                        help='Spotify album url',
                        required=True)
    parser.add_argument('--sheet-id',
                        type=str,
                        help='Google Sheet ID (or set GOOGLE_SHEET_ID)',
                        required=False)
    parser.add_argument('--sheet-tab',
                        type=str,
                        help='Google Sheet tab name (or set GOOGLE_SHEET_TAB)',
                        required=False)
    parser.add_argument('--service-account-file',
                        type=str,
                        help='Service account JSON file (or set GOOGLE_SERVICE_ACCOUNT_FILE)',
                        required=False)
    return parser.parse_args()

# use spotify api to extract album info from given url
def get_album_info(url = '', spot_api = None):
    
    try:

        raw_info = spot_api.album(url)

    except SpotifyException as e:

        if e.http_status == 400:
            logger.error('Spotify API error fetching album', extra={'url': url, 'http_status': e.http_status})
            return None


    album_id = raw_info.get('id', '')
    artist = raw_info['artists'][0]['name']
    album = raw_info['name']
    release_date = raw_info['release_date']
    release_date_precision = raw_info['release_date_precision']

    if release_date_precision == 'day':

        year = datetime.strptime(release_date, '%Y-%m-%d').year
    else:

        year = release_date
    artwork_url = raw_info['images'][1]['url']

    to_return = {"spotify_album_id": album_id,
                 "Artist": artist,
                 "Album": album,
                 "Year": year,
                 "spotify_album_url": url,
                 "artwork_url": artwork_url}

    return to_return

def get_spotify_api():
    # Prefer env vars (used on Railway); fall back to local credentials file for dev
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

    if not CLIENT_ID or not CLIENT_SECRET:
        # Local dev: read from spotify_credentials.json at the repo root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        cred_path = os.path.join(repo_root, 'spotify_credentials.json')
        with open(cred_path, 'r') as cred_file:
            creds = json.load(cred_file)
        CLIENT_ID = creds.get('CLIENT_ID')
        CLIENT_SECRET = creds.get('CLIENT_SECRET')

    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    return spotipy.Spotify(auth_manager=auth_manager)

def get_default_creds_path():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    default_name = 'aotw-488201-8465cf54c9d9.json'
    candidate = os.path.join(repo_root, default_name)
    return candidate if os.path.isfile(candidate) else None

def get_google_sheet(sheet_id=None, sheet_tab=None, creds_path=None):
    import tempfile

    sheet_id  = sheet_id  or os.getenv('GOOGLE_SHEET_ID') or '1h1uDCZPqJovFfUKPzfPgUwUOHjFdCXHWVhUE6VvFA_s'
    sheet_tab = sheet_tab or os.getenv('GOOGLE_SHEET_TAB', 'Sheet1')

    if not sheet_id:
        raise ValueError('Missing Google Sheet ID. Set GOOGLE_SHEET_ID or pass --sheet-id.')

    # GOOGLE_SERVICE_ACCOUNT_JSON can be either:
    #   - JSON content as a string (Railway stores large secrets this way)
    #   - A file path (local dev or CI)
    # GOOGLE_SERVICE_ACCOUNT_FILE is kept for backward compatibility.
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

    if service_account_json and service_account_json.strip().startswith('{'):
        # It's raw JSON — write to a temp file so gspread can read it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write(service_account_json)
            tmp_path = f.name
        try:
            gc = gspread.service_account(filename=tmp_path)
        finally:
            os.unlink(tmp_path)  # Always clean up, even if gspread raises
    else:
        # File path: prefer explicit arg, then env vars, then default on-disk file
        resolved_path = (
            creds_path
            or service_account_json
            or os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
            or get_default_creds_path()
        )
        if not resolved_path:
            raise ValueError(
                'Missing service account credentials. '
                'Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE.'
            )
        gc = gspread.service_account(filename=resolved_path)

    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.worksheet(sheet_tab)
    return worksheet

def parse_sheet_date(value):
    if not value:
        return None
    value = str(value).strip()
    for fmt in ('%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None

def format_sheet_date(value):
    if not value:
        return ''
    try:
        return value.strftime('%-m/%-d/%Y')
    except ValueError:
        return value.strftime('%m/%d/%Y')

def find_header_cells(worksheet):
    try:
        pick_cell = worksheet.find(re.compile(r'^Pick$', re.I))
        date_cell = worksheet.find(re.compile(r'^Date$', re.I))
    except CellNotFound:
        raise ValueError('Missing required columns: Pick, Date.')
    return pick_cell, date_cell

def get_header_row_and_map(worksheet):
    pick_cell, date_cell = find_header_cells(worksheet)
    header_row = max(pick_cell.row, date_cell.row)
    header_values = worksheet.row_values(header_row)
    header_map = {str(name).strip().lower(): idx for idx, name in enumerate(header_values)}
    return header_row, header_map

def get_next_pick_number_and_date(worksheet, header_row, pick_col, date_col):
    pick_values = worksheet.col_values(pick_col)
    date_values = worksheet.col_values(date_col)

    last_pick = None
    last_date = None

    for value in pick_values[header_row:]:
        if str(value).strip():
            try:
                last_pick = int(float(value))
            except ValueError:
                pass

    for value in date_values[header_row:]:
        if str(value).strip():
            parsed = parse_sheet_date(value)
            if parsed:
                last_date = parsed

    next_pick = (last_pick + 1) if last_pick is not None else 1
    next_date = (last_date + timedelta(days = 7)) if last_date else None
    return next_pick, next_date

def build_row_from_header(header_map, pick_value, date_value, album_info):
    header_len = max(header_map.values()) + 1 if header_map else 0
    row = [''] * header_len

    def set_if_present(header_name, value):
        idx = header_map.get(header_name)
        if idx is not None:
            row[idx] = value

    set_if_present('pick', str(pick_value))
    set_if_present('date', format_sheet_date(date_value))
    set_if_present('artist', album_info.get('Artist', ''))
    set_if_present('album', album_info.get('Album', ''))
    set_if_present('year', str(album_info.get('Year', '')))
    set_if_present('spotify_album_id', album_info.get('spotify_album_id', ''))
    set_if_present('spotify_album_url', album_info.get('spotify_album_url', ''))
    set_if_present('artwork_url', album_info.get('artwork_url', ''))

    return row

def get_existing_album_ids(worksheet) -> dict:
    """Return dict mapping album_id -> (pick, date) for all rows in the sheet."""
    header_row, header_map = get_header_row_and_map(worksheet)
    url_col_idx = header_map.get('spotify_album_url')
    if url_col_idx is None:
        return {}

    url_values = worksheet.col_values(url_col_idx + 1)  # gspread is 1-indexed
    pick_col_idx = header_map.get('pick')
    date_col_idx = header_map.get('date')
    pick_values = worksheet.col_values(pick_col_idx + 1) if pick_col_idx is not None else []
    date_values = worksheet.col_values(date_col_idx + 1) if date_col_idx is not None else []

    existing = {}
    for i, url in enumerate(url_values[header_row:], start=header_row):
        if url:
            album_id = extract_spotify_album_id(url)
            if album_id:
                pick = pick_values[i] if i < len(pick_values) else ''
                date = date_values[i] if i < len(date_values) else ''
                existing[album_id] = (pick, date)
    return existing


def check_duplicate(url: str, worksheet) -> tuple:
    """Check if album already exists in the sheet.

    Returns (is_duplicate, message).
    """
    album_id = extract_spotify_album_id(url)
    if not album_id:
        return False, None

    existing = get_existing_album_ids(worksheet)
    if album_id in existing:
        pick, date = existing[album_id]
        return True, f"Already added — Pick #{pick} on {date}"
    return False, None


def add_album(url = '', sheet_id = None, sheet_tab = None, creds_path = None):

    try:
        worksheet = get_google_sheet(sheet_id = sheet_id, sheet_tab = sheet_tab, creds_path = creds_path)
    except (GSpreadException, ValueError) as exc:
        logger.error('Failed to connect to Google Sheet: %s', exc)
        return False

    is_dup, dup_msg = check_duplicate(url, worksheet)
    if is_dup:
        logger.info(dup_msg)
        return False

    sp = get_spotify_api()

    #get new album info and append
    next_album_info = get_album_info(url = url, spot_api = sp)

    if next_album_info is None:
        return False
    try:
        header_row, header_map = get_header_row_and_map(worksheet)
        pick_cell, date_cell = find_header_cells(worksheet)
        next_pick, next_date = get_next_pick_number_and_date(
            worksheet,
            header_row,
            pick_cell.col,
            date_cell.col
        )
        row = build_row_from_header(header_map, next_pick, next_date, next_album_info)
        worksheet.append_row(row, value_input_option = 'USER_ENTERED')
    except (GSpreadException, ValueError) as exc:
        logger.error('Failed to append row to Google Sheet: %s', exc)
        return False

    logger.info('Successfully added "%s" by %s to the sheet', next_album_info.get('Album'), next_album_info.get('Artist'))
    return True

def main():

    args = get_user_args()
    url = args.url
    add_album(url = url,
              sheet_id = args.sheet_id,
              sheet_tab = args.sheet_tab,
              creds_path = args.service_account_file)

if __name__ == "__main__":
    main()
