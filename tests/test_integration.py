"""Integration tests for the full AOTW pipeline.

Covers pipeline orchestration (process_album) and GitHub push end-to-end,
with all external services mocked. JSON export is tested in test_export_json.py.
"""
import json
import os
import sys
import pytest
from contextlib import contextmanager
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pipeline import process_album
from github_push import push_data_to_github


# ---------------------------------------------------------------------------
# Shared constants and fixtures
# ---------------------------------------------------------------------------

SAMPLE_URL = 'https://open.spotify.com/album/0SeRWS3scHWplJhMppd6rJ'
SAMPLE_ALBUM_ID = '0SeRWS3scHWplJhMppd6rJ'

SAMPLE_ALBUM_INFO = {
    'spotify_album_id': SAMPLE_ALBUM_ID,
    'Artist': 'Dave Matthews Band',
    'Album': 'Under the Table and Dreaming',
    'Year': 1994,
    'spotify_album_url': SAMPLE_URL,
    'artwork_url': 'https://i.scdn.co/image/medium.jpg',
}

HEADER = ['Pick', 'Date', 'Artist', 'Album', 'Year', 'spotify_album_url', 'artwork_url', 'Picker']
HEADER_MAP = {col.lower(): idx for idx, col in enumerate(HEADER)}


@pytest.fixture
def mock_worksheet():
    ws = MagicMock()
    ws.row_values.return_value = HEADER
    ws.find.side_effect = [
        Mock(row=1, col=1),  # Pick header cell
        Mock(row=1, col=2),  # Date header cell
    ]
    ws.col_values.return_value = ['Pick', '1', '2', '3']
    ws.append_row.return_value = None
    ws.get_all_values.return_value = [HEADER]
    return ws


@contextmanager
def _apply_patches(patch_dict):
    """Start all patches in a dict, yield, then stop them all."""
    active = [patch(target, new=mock) for target, mock in patch_dict.items()]
    for p in active:
        p.start()
    try:
        yield
    finally:
        for p in active:
            p.stop()


def _success_mocks(worksheet, github_result=(True, 'Website will update shortly')):
    """Return a patch dict for a fully successful pipeline run."""
    return {
        'pipeline.get_google_sheet':            Mock(return_value=worksheet),
        'pipeline.check_duplicate':             Mock(return_value=(False, '')),
        'pipeline.get_spotify_api':             Mock(return_value=Mock()),
        'pipeline.get_album_info':              Mock(return_value=SAMPLE_ALBUM_INFO),
        'pipeline.validate_album_metadata':     Mock(return_value=(True, '')),
        'pipeline.find_header_cells':           Mock(return_value=(Mock(col=1), Mock(col=2))),
        'pipeline.get_header_row_and_map':      Mock(return_value=(0, HEADER_MAP)),
        'pipeline.get_next_pick_number_and_date': Mock(return_value=(4, '2025-01-26')),
        'pipeline.build_row_from_header':       Mock(return_value=[]),
        'pipeline.export_and_push':             Mock(return_value=github_result),
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestPipelineSuccess:

    @pytest.mark.asyncio
    async def test_returns_success_true(self, mock_worksheet):
        with _apply_patches(_success_mocks(mock_worksheet)):
            result = await process_album(SAMPLE_URL)
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_message_contains_artist_and_album(self, mock_worksheet):
        with _apply_patches(_success_mocks(mock_worksheet)):
            result = await process_album(SAMPLE_URL)
        assert 'Dave Matthews Band' in result['message']
        assert 'Under the Table and Dreaming' in result['message']

    @pytest.mark.asyncio
    async def test_appends_row_to_sheet(self, mock_worksheet):
        with _apply_patches(_success_mocks(mock_worksheet)):
            await process_album(SAMPLE_URL)
        mock_worksheet.append_row.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_export_and_push(self, mock_worksheet):
        mocks = _success_mocks(mock_worksheet)
        with _apply_patches(mocks):
            await process_album(SAMPLE_URL)
        mocks['pipeline.export_and_push'].assert_called_once()


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------

class TestPipelineFailures:

    @pytest.mark.asyncio
    async def test_invalid_url_rejected_without_hitting_sheet(self):
        track_url = 'https://open.spotify.com/track/5SBMNVrRM8xZpyGYTYtfR9'
        with patch('pipeline.get_google_sheet') as mock_sheet:
            result = await process_album(track_url)
        assert result['success'] is False
        assert 'Invalid' in result['message']
        mock_sheet.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_album_rejected(self, mock_worksheet):
        with patch('pipeline.get_google_sheet', return_value=mock_worksheet), \
             patch('pipeline.check_duplicate', return_value=(
                 True, 'Already added: Dave Matthews Band - Under the Table and Dreaming'
             )):
            result = await process_album(SAMPLE_URL)
        assert result['success'] is False
        assert 'Already added' in result['message']

    @pytest.mark.asyncio
    async def test_sheet_access_failure(self):
        with patch('pipeline.get_google_sheet', side_effect=Exception('Network error')):
            result = await process_album(SAMPLE_URL)
        assert result['success'] is False
        assert 'Google Sheet' in result['message']

    @pytest.mark.asyncio
    async def test_spotify_lookup_failure(self, mock_worksheet):
        with patch('pipeline.get_google_sheet', return_value=mock_worksheet), \
             patch('pipeline.check_duplicate', return_value=(False, '')), \
             patch('pipeline.get_spotify_api', side_effect=Exception('Spotify down')):
            result = await process_album(SAMPLE_URL)
        assert result['success'] is False
        assert 'Spotify' in result['message']

    @pytest.mark.asyncio
    async def test_sheet_append_failure(self, mock_worksheet):
        mock_worksheet.append_row.side_effect = Exception('Write quota exceeded')
        mocks = _success_mocks(mock_worksheet)
        with _apply_patches(mocks):
            result = await process_album(SAMPLE_URL)
        assert result['success'] is False
        mock_worksheet.append_row.assert_called_once()
        # export_and_push must not be called if the sheet write failed
        mocks['pipeline.export_and_push'].assert_not_called()


# ---------------------------------------------------------------------------
# Partial failure (sheet OK, GitHub down)
# ---------------------------------------------------------------------------

class TestPipelinePartialFailure:

    @pytest.mark.asyncio
    async def test_github_failure_still_returns_success(self, mock_worksheet):
        mocks = _success_mocks(mock_worksheet, github_result=(False, 'GitHub push failed'))
        with _apply_patches(mocks):
            result = await process_album(SAMPLE_URL)
        assert result['success'] is True
        assert result.get('partial_failure') is True

    @pytest.mark.asyncio
    async def test_partial_failure_message_contains_album(self, mock_worksheet):
        mocks = _success_mocks(mock_worksheet, github_result=(False, 'GitHub push failed'))
        with _apply_patches(mocks):
            result = await process_album(SAMPLE_URL)
        assert 'Dave Matthews Band' in result['message']

    @pytest.mark.asyncio
    async def test_partial_failure_sheet_row_was_written(self, mock_worksheet):
        mocks = _success_mocks(mock_worksheet, github_result=(False, 'GitHub push failed'))
        with _apply_patches(mocks):
            await process_album(SAMPLE_URL)
        mock_worksheet.append_row.assert_called_once()


# ---------------------------------------------------------------------------
# GitHub push
# ---------------------------------------------------------------------------

class TestGitHubPush:

    def test_creates_new_file_omits_sha(self):
        with patch('github_push.GITHUB_TOKEN', 'tok'), \
             patch('github_push.GITHUB_REPO_OWNER', 'owner'), \
             patch('github_push.GITHUB_REPO_NAME', 'repo'), \
             patch('github_push.requests.get') as mock_get, \
             patch('github_push.requests.put') as mock_put:
            mock_get.return_value = Mock(status_code=404)
            mock_put.return_value = Mock(
                status_code=201,
                json=lambda: {'commit': {'sha': 'abc1234567890abc1'}}
            )
            result = push_data_to_github(json.dumps([{'id': 1}]), 'Add album')
        assert result is True
        payload = mock_put.call_args.kwargs['json']
        assert 'sha' not in payload

    def test_updates_existing_file_includes_sha(self):
        existing_sha = 'deadbeef01234567'
        with patch('github_push.GITHUB_TOKEN', 'tok'), \
             patch('github_push.GITHUB_REPO_OWNER', 'owner'), \
             patch('github_push.GITHUB_REPO_NAME', 'repo'), \
             patch('github_push.requests.get') as mock_get, \
             patch('github_push.requests.put') as mock_put:
            mock_get.return_value = Mock(status_code=200, json=lambda: {'sha': existing_sha})
            mock_put.return_value = Mock(
                status_code=200,
                json=lambda: {'commit': {'sha': 'newsha01234567890'}}
            )
            result = push_data_to_github(json.dumps([{'id': 1}]), 'Update albums')
        assert result is True
        payload = mock_put.call_args.kwargs['json']
        assert payload['sha'] == existing_sha

    def test_content_is_base64_encoded(self):
        raw = json.dumps([{'album': 'test'}])
        with patch('github_push.GITHUB_TOKEN', 'tok'), \
             patch('github_push.GITHUB_REPO_OWNER', 'owner'), \
             patch('github_push.GITHUB_REPO_NAME', 'repo'), \
             patch('github_push.requests.get') as mock_get, \
             patch('github_push.requests.put') as mock_put:
            mock_get.return_value = Mock(status_code=404)
            mock_put.return_value = Mock(
                status_code=201,
                json=lambda: {'commit': {'sha': 'abc1234567890abc1'}}
            )
            push_data_to_github(raw, 'Test')
        import base64
        payload = mock_put.call_args.kwargs['json']
        decoded = base64.b64decode(payload['content']).decode('utf-8')
        assert decoded == raw

    def test_missing_credentials_raises(self):
        with patch('github_push.GITHUB_TOKEN', None), \
             patch('github_push.GITHUB_REPO_OWNER', None), \
             patch('github_push.GITHUB_REPO_NAME', None):
            with pytest.raises(ValueError, match='GitHub config incomplete'):
                push_data_to_github('{}', 'Test')
