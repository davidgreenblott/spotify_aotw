import json
import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from export_json import export_sheet_to_json

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALBUM_ID_A = '0SeRWS3scHWplJhMppd6rJ'
ALBUM_ID_B = '1BZnpfFBovJnGHhFrQjbWB'
URL_A = f'https://open.spotify.com/album/{ALBUM_ID_A}'
URL_B = f'https://open.spotify.com/album/{ALBUM_ID_B}'

# Column order used by make_worksheet / sample rows below
HEADER = ['Pick', 'Date', 'Artist', 'Album', 'Year', 'spotify_album_url', 'artwork_url', 'picker']


def make_worksheet(data_rows):
    """Build a mock worksheet that returns the given rows after a 1-row header."""
    ws = MagicMock()

    # get_all_values() returns header + data rows
    ws.get_all_values.return_value = [HEADER] + data_rows

    # Simulate find() so get_header_row_and_map works
    pick_cell = MagicMock(); pick_cell.row = 1; pick_cell.col = 1
    date_cell = MagicMock(); date_cell.row = 1; date_cell.col = 2
    ws.find.side_effect = lambda pattern: (
        pick_cell if 'pick' in pattern.pattern.lower() else date_cell
    )

    # row_values() is called by get_header_row_and_map to read the header
    ws.row_values.return_value = HEADER

    return ws


def run_export(data_rows):
    """Run export_sheet_to_json with a mock worksheet and return (albums, json_path)."""
    ws = make_worksheet(data_rows)
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        json_path = f.name

    with patch('export_json.get_google_sheet', return_value=ws):
        albums = export_sheet_to_json(output_path=json_path)

    return albums, json_path


# ---------------------------------------------------------------------------
# Tests: happy path
# ---------------------------------------------------------------------------

def test_exports_single_valid_row():
    rows = [['1', '1/5/2025', 'Radiohead', 'OK Computer', '1997', URL_A, 'http://art.jpg', 'dave']]
    albums, path = run_export(rows)

    assert len(albums) == 1
    a = albums[0]
    assert a['spotify_album_id'] == ALBUM_ID_A
    assert a['pick_number'] == 1
    assert a['picked_at'] == '2025-01-05'
    assert a['artist'] == 'Radiohead'
    assert a['album'] == 'OK Computer'
    assert a['year'] == '1997'
    assert a['artwork_url'] == 'http://art.jpg'
    assert a['spotify_url'] == URL_A
    assert a['picker'] == 'dave'


def test_writes_valid_json_to_file():
    rows = [['1', '1/5/2025', 'Artist', 'Album', '2000', URL_A, '', '']]
    _, path = run_export(rows)

    with open(path) as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert data[0]['spotify_album_id'] == ALBUM_ID_A
    os.unlink(path)


def test_exports_multiple_rows():
    rows = [
        ['1', '1/5/2025',  'Artist A', 'Album A', '2000', URL_A, '', ''],
        ['2', '1/12/2025', 'Artist B', 'Album B', '2001', URL_B, '', ''],
    ]
    albums, _ = run_export(rows)
    assert len(albums) == 2


def test_sorted_by_pick_number():
    """Rows in the sheet may be out of order — output should be sorted."""
    rows = [
        ['3', '1/19/2025', 'C', 'C', '2003', URL_B, '', ''],
        ['1', '1/5/2025',  'A', 'A', '2001', URL_A, '', ''],
    ]
    albums, _ = run_export(rows)
    assert albums[0]['pick_number'] == 1
    assert albums[1]['pick_number'] == 3


# ---------------------------------------------------------------------------
# Tests: date normalisation
# ---------------------------------------------------------------------------

def test_normalises_mm_dd_yyyy_date():
    rows = [['1', '3/15/2024', 'A', 'B', '2020', URL_A, '', '']]
    albums, _ = run_export(rows)
    assert albums[0]['picked_at'] == '2024-03-15'


def test_normalises_iso_date():
    rows = [['1', '2024-03-15', 'A', 'B', '2020', URL_A, '', '']]
    albums, _ = run_export(rows)
    assert albums[0]['picked_at'] == '2024-03-15'


def test_empty_date_becomes_empty_string():
    rows = [['1', '', 'A', 'B', '2020', URL_A, '', '']]
    albums, _ = run_export(rows)
    assert albums[0]['picked_at'] == ''


# ---------------------------------------------------------------------------
# Tests: invalid / missing data
# ---------------------------------------------------------------------------

def test_skips_row_with_no_spotify_url():
    rows = [
        ['1', '1/5/2025', 'Good', 'Album', '2020', URL_A, '', ''],
        ['2', '1/12/2025', 'Bad',  'Album', '2020', '',    '', ''],
    ]
    albums, _ = run_export(rows)
    assert len(albums) == 1
    assert albums[0]['spotify_album_id'] == ALBUM_ID_A


def test_skips_row_with_invalid_spotify_url():
    rows = [['1', '1/5/2025', 'A', 'B', '2020', 'https://example.com/notspotify', '', '']]
    albums, _ = run_export(rows)
    assert len(albums) == 0


def test_empty_sheet_returns_empty_list():
    albums, _ = run_export([])
    assert albums == []


def test_skips_blank_rows():
    rows = [
        ['1', '1/5/2025', 'A', 'B', '2020', URL_A, '', ''],
        ['', '', '', '', '', '', '', ''],  # blank row
        ['2', '1/12/2025', 'C', 'D', '2021', URL_B, '', ''],
    ]
    albums, _ = run_export(rows)
    assert len(albums) == 2


def test_unparseable_pick_number_defaults_to_zero():
    rows = [['N/A', '1/5/2025', 'A', 'B', '2020', URL_A, '', '']]
    albums, _ = run_export(rows)
    assert albums[0]['pick_number'] == 0
