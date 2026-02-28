import json
from typing import List, Dict

from logging_config import setup_logging
from add_album import get_google_sheet, get_header_row_and_map, parse_sheet_date
from validation import extract_spotify_album_id

logger = setup_logging()


def export_sheet_to_json(
    sheet_id=None,
    sheet_tab=None,
    creds_path=None,
    output_path='data.json',
) -> List[Dict]:
    """Read the Google Sheet and write a normalized data.json.

    Each album row is normalized to a consistent structure suitable for
    the frontend. Rows with invalid/missing Spotify URLs are skipped.

    Normalized fields per album:
        spotify_album_id  — 22-char Spotify ID extracted from the URL
        pick_number       — int, 0 if missing/unparseable
        picked_at         — ISO date string (YYYY-MM-DD), '' if missing
        artist, album, year, artwork_url, spotify_url, apple_music_url, picker

    Returns the list of normalized album dicts (also written to output_path).
    """
    worksheet = get_google_sheet(sheet_id, sheet_tab, creds_path)

    # header_row is the 0-based index of the header row in the sheet values;
    # header_map maps lowercase column names → index in each row list.
    header_row, header_map = get_header_row_and_map(worksheet)

    # Fetch every cell in one API call — list of lists, one per row
    all_values = worksheet.get_all_values()

    # Everything after the header row is data
    data_rows = all_values[header_row:]

    albums = []
    for row in data_rows:
        # Skip completely empty rows (can appear at end of sheet)
        if not row or not any(cell.strip() for cell in row):
            continue

        # Build a dict from the header map so we can look up by column name
        row_dict = {}
        for col_name, col_idx in header_map.items():
            row_dict[col_name] = row[col_idx].strip() if col_idx < len(row) else ''

        # A valid Spotify URL is required — rows without one are silently skipped
        spotify_url = row_dict.get('spotify_album_url', '')
        album_id = extract_spotify_album_id(spotify_url)
        if not album_id:
            logger.warning('Skipping row with invalid Spotify URL: %r', spotify_url)
            continue

        # Coerce pick number to int; default to 0 if cell is empty or a formula placeholder
        try:
            pick_number = int(float(row_dict.get('pick', '') or 0))
        except (ValueError, TypeError):
            pick_number = 0

        # Normalise the date to ISO format (YYYY-MM-DD) regardless of sheet format
        raw_date = row_dict.get('date', '')
        parsed_date = parse_sheet_date(raw_date)
        picked_at = parsed_date.isoformat() if parsed_date else ''

        albums.append({
            'spotify_album_id': album_id,
            'pick_number':      pick_number,
            'picked_at':        picked_at,
            'artist':           row_dict.get('artist', ''),
            'album':            row_dict.get('album', ''),
            'year':             row_dict.get('year', ''),
            'label':            row_dict.get('label', ''),
            'genres':           row_dict.get('genres', ''),
            'total_tracks':     row_dict.get('total_tracks', ''),
            'artwork_url':      row_dict.get('artwork_url', ''),
            'spotify_url':      spotify_url,
            'apple_music_url':  row_dict.get('apple_music_url', ''),
            'picker':           row_dict.get('picker', ''),
        })

    # Sort ascending by pick number so the frontend gets them in order
    albums.sort(key=lambda x: x['pick_number'])

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    logger.info('Exported %d albums to %s', len(albums), output_path)
    return albums


if __name__ == '__main__':
    # Quick manual test — writes data.json in the current directory
    export_sheet_to_json()
