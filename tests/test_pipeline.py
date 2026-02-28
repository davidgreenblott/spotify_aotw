import pytest
import sys
import os
from datetime import date
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

VALID_URL = "https://open.spotify.com/album/4LH4d3cOWNNsVw41Gqt2kv"
ALBUM_INFO = {
    'spotify_album_id': '4LH4d3cOWNNsVw41Gqt2kv',
    'Artist': 'Radiohead',
    'Album': 'OK Computer',
    'Year': 1997,
    'spotify_album_url': VALID_URL,
    'artwork_url': 'https://example.com/art.jpg',
}

# Shared patch targets
_SHEET = 'pipeline.get_google_sheet'
_DEDUP = 'pipeline.check_duplicate'
_SP_API = 'pipeline.get_spotify_api'
_ALBUM_INFO = 'pipeline.get_album_info'
_VALIDATE = 'pipeline.validate_album_metadata'
_HEADER_MAP = 'pipeline.get_header_row_and_map'
_HEADER_CELLS = 'pipeline.find_header_cells'
_NEXT_DATE = 'pipeline.get_next_pick_number_and_date'
_BUILD_ROW = 'pipeline.build_row_from_header'
_GITHUB = 'pipeline.export_and_push'


def make_worksheet():
    ws = MagicMock()
    ws.append_row.return_value = None
    return ws


def make_header_mocks():
    """Return consistent mocks for the sheet-append helpers."""
    header_map = {'pick': 0, 'date': 1, 'artist': 2, 'album': 3}
    pick_cell = MagicMock(); pick_cell.col = 1
    date_cell = MagicMock(); date_cell.col = 2
    return header_map, pick_cell, date_cell


# --- Step 1: URL validation ---

@pytest.mark.asyncio
async def test_invalid_url_returns_error():
    import pipeline
    result = await pipeline.process_album("https://open.spotify.com/track/abc123")
    assert result['success'] is False
    assert "Invalid Spotify album link" in result['message']


@pytest.mark.asyncio
async def test_invalid_url_does_not_call_sheet():
    import pipeline
    with patch(_SHEET) as mock_sheet:
        await pipeline.process_album("not-a-url")
    mock_sheet.assert_not_called()


# --- Step 2: Sheet access failure ---

@pytest.mark.asyncio
async def test_sheet_access_failure_returns_error():
    import pipeline
    with patch(_SHEET, side_effect=Exception("network error")):
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is False
    assert "Failed to access Google Sheet" in result['message']


# --- Step 3: Deduplication ---

@pytest.mark.asyncio
async def test_duplicate_album_returns_error():
    import pipeline
    ws = make_worksheet()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(True, "Already added — Pick #5 on 1/12/2025")):
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is False
    assert "Already added" in result['message']


@pytest.mark.asyncio
async def test_duplicate_does_not_call_spotify():
    import pipeline
    ws = make_worksheet()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(True, "Already added — Pick #5 on 1/12/2025")), \
         patch(_SP_API) as mock_sp:
        await pipeline.process_album(VALID_URL)
    mock_sp.assert_not_called()


# --- Step 4: Spotify API failure ---

@pytest.mark.asyncio
async def test_spotify_api_exception_returns_error():
    import pipeline
    ws = make_worksheet()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(False, None)), \
         patch(_SP_API, side_effect=Exception("Spotify down")):
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is False
    assert "fetch album info" in result['message']


@pytest.mark.asyncio
async def test_spotify_returns_none_returns_error():
    import pipeline
    ws = make_worksheet()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(False, None)), \
         patch(_SP_API, return_value=MagicMock()), \
         patch(_ALBUM_INFO, return_value=None):
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is False
    assert "missing album data" in result['message']


# --- Step 5: Metadata validation ---

@pytest.mark.asyncio
async def test_invalid_metadata_returns_error():
    import pipeline
    ws = make_worksheet()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(False, None)), \
         patch(_SP_API, return_value=MagicMock()), \
         patch(_ALBUM_INFO, return_value=ALBUM_INFO), \
         patch(_VALIDATE, return_value=(False, "Missing required fields: Artist")):
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is False
    assert "Missing required fields" in result['message']


# --- Step 6: Sheet append failure ---

@pytest.mark.asyncio
async def test_sheet_append_failure_returns_error():
    import pipeline
    ws = make_worksheet()
    ws.append_row.side_effect = Exception("quota exceeded")
    header_map, pick_cell, date_cell = make_header_mocks()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(False, None)), \
         patch(_SP_API, return_value=MagicMock()), \
         patch(_ALBUM_INFO, return_value=ALBUM_INFO), \
         patch(_VALIDATE, return_value=(True, "")), \
         patch(_HEADER_MAP, return_value=(1, header_map)), \
         patch(_HEADER_CELLS, return_value=(pick_cell, date_cell)), \
         patch(_NEXT_DATE, return_value=(1, date(2025, 1, 12))):
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is False
    assert "Failed to add album" in result['message']


# --- Steps 7+8: GitHub push and success ---

def _success_patches(ws, header_map, pick_cell, date_cell, github_result=(True, 'Website will update shortly')):
    """Return a context manager stack for a fully successful pipeline run."""
    return [
        patch(_SHEET, return_value=ws),
        patch(_DEDUP, return_value=(False, None)),
        patch(_SP_API, return_value=MagicMock()),
        patch(_ALBUM_INFO, return_value=ALBUM_INFO),
        patch(_VALIDATE, return_value=(True, "")),
        patch(_HEADER_MAP, return_value=(1, header_map)),
        patch(_HEADER_CELLS, return_value=(pick_cell, date_cell)),
        patch(_NEXT_DATE, return_value=(1, date(2025, 1, 12))),
        patch(_GITHUB, return_value=github_result),
    ]


@pytest.mark.asyncio
async def test_successful_pipeline_returns_success():
    import pipeline
    ws = make_worksheet()
    header_map, pick_cell, date_cell = make_header_mocks()
    patches = _success_patches(ws, header_map, pick_cell, date_cell)
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patches[5], patches[6], patches[7], patches[8]:
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is True
    assert "OK Computer" in result['message']
    assert "Radiohead" in result['message']
    assert result['data'] == ALBUM_INFO


@pytest.mark.asyncio
async def test_successful_pipeline_calls_append_row():
    import pipeline
    ws = make_worksheet()
    header_map, pick_cell, date_cell = make_header_mocks()
    patches = _success_patches(ws, header_map, pick_cell, date_cell)
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patches[5], patches[6], patches[7], patches[8]:
        await pipeline.process_album(VALID_URL)
    ws.append_row.assert_called_once()


@pytest.mark.asyncio
async def test_successful_pipeline_passes_header_row_for_pick_formula():
    """Pipeline must pass header_row so build_row_from_header writes =ROW()-N formula."""
    import pipeline
    ws = make_worksheet()
    header_map, pick_cell, date_cell = make_header_mocks()
    with patch(_SHEET, return_value=ws), \
         patch(_DEDUP, return_value=(False, None)), \
         patch(_SP_API, return_value=MagicMock()), \
         patch(_ALBUM_INFO, return_value=ALBUM_INFO), \
         patch(_VALIDATE, return_value=(True, "")), \
         patch(_HEADER_MAP, return_value=(1, header_map)), \
         patch(_HEADER_CELLS, return_value=(pick_cell, date_cell)), \
         patch(_NEXT_DATE, return_value=(1, date(2025, 1, 12))), \
         patch(_BUILD_ROW) as mock_build, \
         patch(_GITHUB, return_value=(True, 'Website will update shortly')):
        mock_build.return_value = [''] * 4
        await pipeline.process_album(VALID_URL)
    # pick_value arg is '' (unused); header_row (5th arg) is passed so the formula is written
    args = mock_build.call_args[0]
    assert args[1] == ''       # pick_value unused
    assert args[4] == 1        # header_row passed so formula =ROW()-1 is written


@pytest.mark.asyncio
async def test_github_failure_returns_partial_failure():
    """If GitHub push fails, success=True (sheet is safe) but partial_failure flag is set."""
    import pipeline
    ws = make_worksheet()
    header_map, pick_cell, date_cell = make_header_mocks()
    patches = _success_patches(
        ws, header_map, pick_cell, date_cell,
        github_result=(False, 'Website update pending (will sync on next run)'),
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patches[5], patches[6], patches[7], patches[8]:
        result = await pipeline.process_album(VALID_URL)
    assert result['success'] is True
    assert result.get('partial_failure') is True
    assert "OK Computer" in result['message']
    assert "pending" in result['message']


@pytest.mark.asyncio
async def test_github_success_includes_website_message():
    """Full success message should include the GitHub/website confirmation."""
    import pipeline
    ws = make_worksheet()
    header_map, pick_cell, date_cell = make_header_mocks()
    patches = _success_patches(ws, header_map, pick_cell, date_cell)
    with patches[0], patches[1], patches[2], patches[3], patches[4], \
         patches[5], patches[6], patches[7], patches[8]:
        result = await pipeline.process_album(VALID_URL)
    assert 'partial_failure' not in result
    assert "Website will update shortly" in result['message']
