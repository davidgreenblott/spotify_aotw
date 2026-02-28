import time
from typing import Dict

from logging_config import setup_logging
from validation import (
    is_valid_spotify_album_url,
    extract_spotify_album_id,
    validate_album_metadata,
)
from github_push import export_and_push
from add_album import (
    get_spotify_api,
    get_album_info,
    get_google_sheet,
    find_header_cells,
    get_header_row_and_map,
    get_next_pick_number_and_date,
    build_row_from_header,
    check_duplicate,
)

logger = setup_logging()


async def process_album(url: str, sheet_id=None, sheet_tab=None, creds_path=None) -> Dict:
    """Main pipeline orchestrator.

    Returns: {'success': bool, 'message': str, 'data': dict}
    """
    start_time = time.time()

    # Step 1: URL validation
    if not is_valid_spotify_album_url(url):
        logger.warning('Invalid URL format: %s', url)
        return {
            'success': False,
            'message': "❌ Invalid Spotify album link. Please post a valid album URL.",
        }

    album_id = extract_spotify_album_id(url)
    logger.info('Processing album: %s', album_id)

    # Step 2: Get Google Sheet for dedup check
    try:
        worksheet = get_google_sheet(sheet_id, sheet_tab, creds_path)
    except Exception as e:
        logger.error('Sheet access failed: %s', e)
        return {
            'success': False,
            'message': "❌ Failed to access Google Sheet. Please try again later.",
        }

    # Step 3: Deduplication check
    is_duplicate, dup_message = check_duplicate(url, worksheet)
    if is_duplicate:
        logger.info('Duplicate detected: %s - %s', album_id, dup_message)
        return {
            'success': False,
            'message': f"❌ {dup_message}",
        }

    # Step 4: Fetch Spotify metadata
    try:
        sp = get_spotify_api()
        album_info = get_album_info(url=url, spot_api=sp)
        spotify_latency = time.time() - start_time
        logger.info('Spotify lookup succeeded in %.2fs', spotify_latency)
    except Exception as e:
        logger.error('Spotify lookup failed: %s', e)
        return {
            'success': False,
            'message': "❌ Couldn't fetch album info from Spotify. Please try again.",
        }

    if not album_info:
        return {
            'success': False,
            'message': "❌ Invalid album URL or missing album data.",
        }

    # Step 5: Validate metadata
    is_valid, validation_error = validate_album_metadata(album_info)
    if not is_valid:
        logger.error('Metadata validation failed: %s', validation_error)
        return {
            'success': False,
            'message': f"❌ {validation_error}",
        }

    # Step 6: Append to Google Sheet (pick # written as =ROW()-N formula)
    try:
        header_row, header_map = get_header_row_and_map(worksheet)
        pick_cell, date_cell = find_header_cells(worksheet)
        _, next_date = get_next_pick_number_and_date(
            worksheet, header_row, pick_cell.col, date_cell.col
        )
        row = build_row_from_header(header_map, '', next_date, album_info, header_row)
        worksheet.append_row(row, value_input_option='USER_ENTERED')
        logger.info('Sheet append succeeded for album: %s', album_id)
    except Exception as e:
        logger.error('Sheet append failed: %s', e)
        return {
            'success': False,
            'message': "❌ Failed to add album to sheet. Please try again.",
        }

    artist = album_info.get('Artist', 'Unknown')
    album_name = album_info.get('Album', 'Unknown')

    # Step 7: Export sheet to JSON and push to GitHub so the website stays in sync.
    # The sheet is the source of truth — if the push fails the album is still safely
    # stored, and the next successful run will self-heal the website.
    github_success, github_message = export_and_push(
        sheet_id=sheet_id,
        sheet_tab=sheet_tab,
        creds_path=creds_path,
        album_info=album_info,
    )

    if not github_success:
        logger.warning('GitHub push failed but sheet updated: %s', github_message)
        return {
            'success': True,          # Sheet write succeeded — album is safe
            'message': (
                f"✅ Added *{album_name}* by *{artist}* to sheet.\n"
                f"⚠️ {github_message}"
            ),
            'data': album_info,
            'partial_failure': True,  # Lets callers know the website hasn't updated yet
        }

    return {
        'success': True,
        'message': (
            f"✅ Added *{album_name}* by *{artist}*.\n"
            f"🌐 {github_message}"
        ),
        'data': album_info,
    }
