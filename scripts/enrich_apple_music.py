"""
One-time script to enrich data.json and Google Sheet with Apple Music URLs via the Odesli API.

Usage:
    mamba run -n spotify-env python scripts/enrich_apple_music.py [path/to/data.json]

Defaults to website/public/data.json if no path given.
- Saves progress to data.json every 25 albums
- Writes all Apple Music URLs to the Google Sheet in a single batch update at the end
- Albums already enriched are skipped for fetching but still queued for the sheet update
"""

import json
import os
import sys
import time

import gspread.utils
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from add_album import get_google_sheet, get_header_row_and_map

ODESLI_API = 'https://api.song.link/v1-alpha.1/links'
RATE_LIMIT_DELAY = 0.5  # seconds between requests — safe for free tier


def fetch_apple_music_url(spotify_url: str) -> str | None:
    try:
        resp = requests.get(ODESLI_API, params={'url': spotify_url}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('linksByPlatform', {}).get('appleMusic', {}).get('url')
        elif resp.status_code == 404:
            return None
        else:
            resp.raise_for_status()
    except Exception as e:
        print(f'  error: {e}')
        return None


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'website/public/data.json'

    with open(path, 'r', encoding='utf-8') as f:
        albums = json.load(f)

    # --- Connect to Google Sheet ---
    print('Connecting to Google Sheet...')
    worksheet = get_google_sheet()
    header_row, header_map = get_header_row_and_map(worksheet)

    apple_col_idx = header_map.get('apple_music_url')
    if apple_col_idx is None:
        print("ERROR: 'apple_music_url' column not found in sheet. Add the column header first.")
        sys.exit(1)

    url_col_idx = header_map.get('spotify_album_url')

    # Build map: spotify_url → 1-based sheet row number
    all_values = worksheet.get_all_values()
    url_to_sheet_row = {}
    for i, row in enumerate(all_values[header_row:]):
        sheet_row = header_row + 1 + i
        if url_col_idx < len(row) and row[url_col_idx].strip():
            url_to_sheet_row[row[url_col_idx].strip()] = sheet_row

    total = len(albums)
    already_done = sum(1 for a in albums if 'apple_music_url' in a)
    print(f'{total} albums total, {already_done} already processed\n')

    updated = 0
    not_found = 0
    sheet_updates = []

    for i, album in enumerate(albums):
        spotify_url = album.get('spotify_url', '')

        # Already processed — skip fetch, but still queue sheet update if URL exists
        if 'apple_music_url' in album:
            if album['apple_music_url'] and spotify_url in url_to_sheet_row:
                sheet_updates.append((url_to_sheet_row[spotify_url], album['apple_music_url']))
            continue

        label = f"{album.get('artist')} - {album.get('album')}"

        if not spotify_url:
            print(f'[{i+1}/{total}] SKIP (no spotify_url): {label}')
            album['apple_music_url'] = ''
            continue

        print(f'[{i+1}/{total}] {label} ... ', end='', flush=True)

        apple_url = fetch_apple_music_url(spotify_url)
        album['apple_music_url'] = apple_url or ''

        if apple_url:
            print('✓')
            updated += 1
            if spotify_url in url_to_sheet_row:
                sheet_updates.append((url_to_sheet_row[spotify_url], apple_url))
        else:
            print('not found')
            not_found += 1

        time.sleep(RATE_LIMIT_DELAY)

        # Save data.json progress every 25 albums
        if (i + 1) % 25 == 0:
            _save(path, albums)
            print(f'  — data.json saved ({i+1}/{total})\n')

    _save(path, albums)
    print(f'\ndata.json saved: {updated} newly enriched, {not_found} not on Apple Music')

    # --- Batch update Google Sheet ---
    if sheet_updates:
        print(f'Writing {len(sheet_updates)} Apple Music URLs to Google Sheet...')
        col_letter = gspread.utils.rowcol_to_a1(1, apple_col_idx + 1)[:-1]
        batch = [
            {'range': f'{col_letter}{row}', 'values': [[url]]}
            for row, url in sheet_updates
        ]
        worksheet.batch_update(batch)
        print('Sheet updated ✓')
    else:
        print('No sheet updates needed.')

    _copy_to_website(path)
    print(f'\nDone.')


def _save(path: str, albums: list) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)


def _copy_to_website(src: str) -> None:
    """Copy the enriched data.json to the aotw-website public/ directory if it exists."""
    import shutil
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dest = os.path.join(repo_root, '..', 'aotw-website', 'public', 'data.json')
    dest = os.path.normpath(dest)
    if os.path.isdir(os.path.dirname(dest)):
        shutil.copy2(src, dest)
        print(f'Copied to {dest}')


if __name__ == '__main__':
    main()
