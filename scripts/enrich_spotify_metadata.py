"""
One-time script to enrich data.json and Google Sheet with additional Spotify metadata:
  label, genres (album → artist fallback), total_tracks

Usage:
    mamba run -n spotify-env python scripts/enrich_spotify_metadata.py [path/to/data.json]

Defaults to website/public/data.json if no path given.
- Saves progress to data.json every 25 albums
- Writes all new fields to the Google Sheet in a single batch update at the end
- Albums already enriched (all three fields present) are skipped
"""

import json
import os
import sys
import time

import gspread.utils

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from add_album import get_google_sheet, get_header_row_and_map, get_spotify_api

RATE_LIMIT_DELAY = 0.2  # Spotify rate limits are generous; 0.2s is safe


def fetch_metadata(sp, spotify_album_id: str) -> dict:
    try:
        raw = sp.album(f'spotify:album:{spotify_album_id}')

        label = raw.get('label', '')
        total_tracks = raw.get('total_tracks', '')

        genres = raw.get('genres', [])
        if not genres:
            artist_id = raw['artists'][0].get('id', '')
            if artist_id:
                try:
                    artist_info = sp.artist(artist_id)
                    genres = artist_info.get('genres', [])
                except Exception:
                    genres = []

        return {
            'label': label,
            'genres': ', '.join(genres),
            'total_tracks': str(total_tracks),
        }
    except Exception as e:
        print(f'  error: {e}')
        return {}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'website/public/data.json'

    with open(path, 'r', encoding='utf-8') as f:
        albums = json.load(f)

    print('Connecting to Spotify...')
    sp = get_spotify_api()

    print('Connecting to Google Sheet...')
    worksheet = get_google_sheet()
    header_row, header_map = get_header_row_and_map(worksheet)

    # Verify required columns exist
    missing = [c for c in ('label', 'genres', 'total_tracks') if c not in header_map]
    if missing:
        print(f"ERROR: Missing sheet columns: {missing}. Add them first.")
        sys.exit(1)

    url_col_idx = header_map.get('spotify_album_url')

    # Build map: spotify_url → 1-based sheet row number
    all_values = worksheet.get_all_values()
    url_to_sheet_row = {}
    for i, row in enumerate(all_values[header_row:]):
        sheet_row = header_row + 1 + i
        if url_col_idx < len(row) and row[url_col_idx].strip():
            url_to_sheet_row[row[url_col_idx].strip()] = sheet_row

    ENRICHED_FIELDS = ('label', 'genres', 'total_tracks')
    total = len(albums)
    already_done = sum(1 for a in albums if all(f in a for f in ENRICHED_FIELDS))
    print(f'{total} albums total, {already_done} already enriched\n')

    updated = 0
    failed = 0
    sheet_updates = []  # list of (sheet_row, col_idx, value)

    for i, album in enumerate(albums):
        # Already enriched — queue sheet updates in case sheet is missing them
        if all(f in album for f in ENRICHED_FIELDS):
            spotify_url = album.get('spotify_url', '')
            if spotify_url in url_to_sheet_row:
                row_num = url_to_sheet_row[spotify_url]
                for field in ENRICHED_FIELDS:
                    if album.get(field):
                        sheet_updates.append((row_num, header_map[field], album[field]))
            continue

        album_id = album.get('spotify_album_id', '')
        label = f"{album.get('artist')} - {album.get('album')}"

        if not album_id:
            print(f'[{i+1}/{total}] SKIP (no album_id): {label}')
            continue

        print(f'[{i+1}/{total}] {label} ... ', end='', flush=True)

        metadata = fetch_metadata(sp, album_id)

        if metadata:
            album.update(metadata)
            print(f"✓  label={metadata['label'] or '—'}  genres={metadata['genres'][:40] or '—'}")
            updated += 1
            spotify_url = album.get('spotify_url', '')
            if spotify_url in url_to_sheet_row:
                row_num = url_to_sheet_row[spotify_url]
                for field in ENRICHED_FIELDS:
                    sheet_updates.append((row_num, header_map[field], metadata.get(field, '')))
        else:
            print('failed')
            failed += 1

        time.sleep(RATE_LIMIT_DELAY)

        if (i + 1) % 25 == 0:
            _save(path, albums)
            print(f'  — data.json saved ({i+1}/{total})\n')

    _save(path, albums)
    print(f'\ndata.json saved: {updated} enriched, {failed} failed')

    # Batch update Google Sheet
    if sheet_updates:
        print(f'Writing {len(sheet_updates)} cells to Google Sheet...')
        batch = [
            {
                'range': gspread.utils.rowcol_to_a1(row, col + 1),
                'values': [[val]]
            }
            for row, col, val in sheet_updates
        ]
        worksheet.batch_update(batch)
        print('Sheet updated ✓')
    else:
        print('No sheet updates needed.')

    _copy_to_website(path)
    print('\nDone.')


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
