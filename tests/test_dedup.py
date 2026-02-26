import pytest
import sys
import os
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import add_album


ALBUM_ID_A = "0SeRWS3scHWplJhMppd6rJ"
ALBUM_ID_B = "1BZnpfFBovJnGHhFrQjbWB"
URL_A = f"https://open.spotify.com/album/{ALBUM_ID_A}"
URL_B = f"https://open.spotify.com/album/{ALBUM_ID_B}"


def make_worksheet(url_values, pick_values=None, date_values=None, header=None):
    """Build a mock gspread worksheet with the given column data."""
    ws = MagicMock()
    # header row 0 = header, data starts at row 1
    header_row_values = header or ['Pick', 'Date', 'Artist', 'Album', 'Year', 'spotify_album_url', 'artwork_url']
    ws.row_values.return_value = header_row_values

    pick_cell = MagicMock(); pick_cell.row = 1; pick_cell.col = 1
    date_cell = MagicMock(); date_cell.row = 1; date_cell.col = 2
    ws.find.side_effect = lambda pattern: pick_cell if 'pick' in pattern.pattern.lower() else date_cell

    # col_values returns full column including header at index 0
    def col_values(col_idx):
        col_map = {
            1: ['Pick'] + (pick_values or []),
            2: ['Date'] + (date_values or []),
            6: ['spotify_album_url'] + url_values,
            7: ['artwork_url'],
        }
        return col_map.get(col_idx, [])

    ws.col_values.side_effect = col_values
    return ws


class TestGetExistingAlbumIds:

    def test_returns_known_album_ids(self):
        ws = make_worksheet([URL_A, URL_B], pick_values=['1', '2'], date_values=['1/5/2025', '1/12/2025'])
        result = add_album.get_existing_album_ids(ws)
        assert ALBUM_ID_A in result
        assert ALBUM_ID_B in result

    def test_empty_sheet_returns_empty_dict(self):
        ws = make_worksheet([])
        result = add_album.get_existing_album_ids(ws)
        assert result == {}

    def test_skips_rows_with_no_url(self):
        ws = make_worksheet(['', URL_A, ''], pick_values=['1', '2', '3'], date_values=['1/5/2025', '1/12/2025', '1/19/2025'])
        result = add_album.get_existing_album_ids(ws)
        assert len(result) == 1
        assert ALBUM_ID_A in result

    def test_returns_none_when_url_col_missing(self):
        ws = MagicMock()
        ws.row_values.return_value = ['Pick', 'Date', 'Artist']
        pick_cell = MagicMock(); pick_cell.row = 1; pick_cell.col = 1
        date_cell = MagicMock(); date_cell.row = 1; date_cell.col = 2
        ws.find.side_effect = lambda pattern: pick_cell if 'pick' in pattern.pattern.lower() else date_cell
        result = add_album.get_existing_album_ids(ws)
        assert result == {}


class TestCheckDuplicate:

    def test_detects_duplicate(self):
        ws = make_worksheet([URL_A], pick_values=['42'], date_values=['1/5/2025'])
        is_dup, msg = add_album.check_duplicate(URL_A, ws)
        assert is_dup is True
        assert '42' in msg
        assert '1/5/2025' in msg

    def test_no_duplicate_for_new_album(self):
        ws = make_worksheet([URL_A], pick_values=['1'], date_values=['1/5/2025'])
        is_dup, msg = add_album.check_duplicate(URL_B, ws)
        assert is_dup is False
        assert msg is None

    def test_invalid_url_returns_not_duplicate(self):
        ws = make_worksheet([URL_A])
        is_dup, msg = add_album.check_duplicate("not-a-url", ws)
        assert is_dup is False
        assert msg is None

    def test_empty_sheet_returns_not_duplicate(self):
        ws = make_worksheet([])
        is_dup, msg = add_album.check_duplicate(URL_A, ws)
        assert is_dup is False
