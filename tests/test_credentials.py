"""Tests for env-var-based credential loading in add_album.py."""
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import add_album


# ---------------------------------------------------------------------------
# get_spotify_api — env var vs file fallback
# ---------------------------------------------------------------------------

def test_spotify_api_reads_from_env_vars(monkeypatch):
    """When SPOTIFY_CLIENT_ID/SECRET are set, no file should be read."""
    monkeypatch.setenv('SPOTIFY_CLIENT_ID', 'env-client-id')
    monkeypatch.setenv('SPOTIFY_CLIENT_SECRET', 'env-client-secret')

    with patch('add_album.SpotifyClientCredentials') as mock_creds, \
         patch('add_album.spotipy.Spotify') as mock_sp:
        mock_creds.return_value = MagicMock()
        add_album.get_spotify_api()

    mock_creds.assert_called_once_with(
        client_id='env-client-id',
        client_secret='env-client-secret',
    )


def test_spotify_api_falls_back_to_file_when_env_missing(monkeypatch):
    """When env vars are absent, credentials should be read from the JSON file."""
    monkeypatch.delenv('SPOTIFY_CLIENT_ID', raising=False)
    monkeypatch.delenv('SPOTIFY_CLIENT_SECRET', raising=False)

    fake_creds = json.dumps({'CLIENT_ID': 'file-id', 'CLIENT_SECRET': 'file-secret'})

    with patch('builtins.open', mock_open(read_data=fake_creds)), \
         patch('add_album.SpotifyClientCredentials') as mock_creds, \
         patch('add_album.spotipy.Spotify'):
        mock_creds.return_value = MagicMock()
        add_album.get_spotify_api()

    mock_creds.assert_called_once_with(
        client_id='file-id',
        client_secret='file-secret',
    )


# ---------------------------------------------------------------------------
# get_google_sheet — JSON content string vs file path
# ---------------------------------------------------------------------------

def _make_gspread_mock():
    """Return a mock gspread chain: gc.open_by_key().worksheet()."""
    worksheet = MagicMock()
    sheet = MagicMock()
    sheet.worksheet.return_value = worksheet
    gc = MagicMock()
    gc.open_by_key.return_value = sheet
    return gc, worksheet


def test_google_sheet_uses_json_content_env_var(monkeypatch, tmp_path):
    """When GOOGLE_SERVICE_ACCOUNT_JSON starts with '{', treat it as JSON content."""
    json_content = json.dumps({'type': 'service_account', 'project_id': 'test'})
    monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT_JSON', json_content)
    monkeypatch.setenv('GOOGLE_SHEET_ID', 'sheet-id')

    gc, worksheet = _make_gspread_mock()

    with patch('add_album.gspread.service_account', return_value=gc) as mock_sa, \
         patch('add_album.os.unlink'):
        result = add_album.get_google_sheet()

    # gspread.service_account should be called with a temp file path (not the raw string)
    called_path = mock_sa.call_args[1]['filename']
    assert called_path.endswith('.json')
    assert result == worksheet


def test_google_sheet_json_content_temp_file_is_cleaned_up(monkeypatch):
    """The temp credentials file must be deleted after use."""
    json_content = json.dumps({'type': 'service_account'})
    monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT_JSON', json_content)
    monkeypatch.setenv('GOOGLE_SHEET_ID', 'sheet-id')

    gc, _ = _make_gspread_mock()
    unlinked = []

    with patch('add_album.gspread.service_account', return_value=gc), \
         patch('add_album.os.unlink', side_effect=lambda p: unlinked.append(p)):
        add_album.get_google_sheet()

    assert len(unlinked) == 1
    assert unlinked[0].endswith('.json')


def test_google_sheet_uses_file_path_env_var(monkeypatch):
    """When GOOGLE_SERVICE_ACCOUNT_JSON is a file path (not JSON), use it directly."""
    monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT_JSON', '/path/to/creds.json')
    monkeypatch.setenv('GOOGLE_SHEET_ID', 'sheet-id')

    gc, _ = _make_gspread_mock()

    with patch('add_album.gspread.service_account', return_value=gc) as mock_sa:
        add_album.get_google_sheet()

    mock_sa.assert_called_once_with(filename='/path/to/creds.json')


def test_google_sheet_raises_when_no_credentials(monkeypatch):
    """Should raise ValueError if no credentials can be resolved."""
    monkeypatch.delenv('GOOGLE_SERVICE_ACCOUNT_JSON', raising=False)
    monkeypatch.delenv('GOOGLE_SERVICE_ACCOUNT_FILE', raising=False)
    monkeypatch.setenv('GOOGLE_SHEET_ID', 'sheet-id')

    # Ensure no default file is found on disk
    with patch('add_album.get_default_creds_path', return_value=None):
        with pytest.raises(ValueError, match='Missing service account credentials'):
            add_album.get_google_sheet()
