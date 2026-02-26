import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import github_push

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_JSON = json.dumps([{'spotify_album_id': 'abc123', 'album': 'OK Computer'}])
ENV_VARS = {
    'GITHUB_TOKEN':      'fake-token',
    'GITHUB_REPO_OWNER': 'testuser',
    'GITHUB_REPO_NAME':  'testrepo',
}


def make_get_response(status_code, sha=None):
    """Mock a GET response from the GitHub Contents API."""
    resp = MagicMock()
    resp.status_code = status_code
    if sha:
        resp.json.return_value = {'sha': sha}
    resp.raise_for_status = MagicMock()
    return resp


def make_put_response(status_code, commit_sha='abc1234567890'):
    """Mock a PUT response from the GitHub Contents API."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {'commit': {'sha': commit_sha}}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# push_data_to_github: creating a new file (GET returns 404)
# ---------------------------------------------------------------------------

def test_creates_new_file_when_not_exists(monkeypatch):
    """When the file doesn't exist yet (404), PUT should be called without a SHA."""
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    # Reload module so env vars are picked up
    import importlib
    importlib.reload(github_push)

    get_resp = make_get_response(404)
    put_resp = make_put_response(201)

    with patch('github_push.requests.get', return_value=get_resp), \
         patch('github_push.requests.put', return_value=put_resp) as mock_put:
        result = github_push.push_data_to_github(SAMPLE_JSON, 'test commit')

    assert result is True
    put_payload = mock_put.call_args.kwargs['json']
    assert 'sha' not in put_payload  # No SHA when creating for the first time


def test_updates_existing_file_with_sha(monkeypatch):
    """When the file exists (200), PUT must include the current SHA."""
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    get_resp = make_get_response(200, sha='existingsha1234567890123456789012')
    put_resp = make_put_response(200)

    with patch('github_push.requests.get', return_value=get_resp), \
         patch('github_push.requests.put', return_value=put_resp) as mock_put:
        result = github_push.push_data_to_github(SAMPLE_JSON, 'update commit')

    assert result is True
    put_payload = mock_put.call_args.kwargs['json']
    assert put_payload['sha'] == 'existingsha1234567890123456789012'


def test_put_includes_correct_commit_message(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    with patch('github_push.requests.get', return_value=make_get_response(404)), \
         patch('github_push.requests.put', return_value=make_put_response(201)) as mock_put:
        github_push.push_data_to_github(SAMPLE_JSON, 'Add Radiohead - OK Computer')

    assert mock_put.call_args.kwargs['json']['message'] == 'Add Radiohead - OK Computer'


def test_content_is_base64_encoded(monkeypatch):
    """The content field in the PUT payload must be base64-encoded."""
    import base64
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    with patch('github_push.requests.get', return_value=make_get_response(404)), \
         patch('github_push.requests.put', return_value=make_put_response(201)) as mock_put:
        github_push.push_data_to_github(SAMPLE_JSON, 'commit')

    encoded = mock_put.call_args.kwargs['json']['content']
    decoded = base64.b64decode(encoded).decode('utf-8')
    assert decoded == SAMPLE_JSON


# ---------------------------------------------------------------------------
# push_data_to_github: error handling
# ---------------------------------------------------------------------------

def test_raises_when_env_vars_missing():
    """Should raise ValueError immediately if config is incomplete."""
    import importlib
    # Patch module-level vars directly
    with patch.object(github_push, 'GITHUB_TOKEN', None):
        with pytest.raises(ValueError, match='GitHub config incomplete'):
            github_push.push_data_to_github(SAMPLE_JSON, 'commit')


def test_raises_on_unexpected_get_status(monkeypatch):
    """A non-200/404 GET response (e.g. 403 auth error) should raise."""
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    forbidden = make_get_response(403)
    forbidden.raise_for_status.side_effect = Exception('403 Forbidden')

    with patch('github_push.requests.get', return_value=forbidden), \
         patch('github_push.requests.put') as mock_put, \
         patch('retry_utils.time.sleep'):  # suppress retry delays
        with pytest.raises(Exception):
            github_push.push_data_to_github(SAMPLE_JSON, 'commit')

    mock_put.assert_not_called()


def test_raises_on_put_failure(monkeypatch):
    """A failed PUT should raise so the retry decorator can handle it."""
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    put_resp = make_put_response(422)
    put_resp.raise_for_status.side_effect = Exception('422 Unprocessable')

    with patch('github_push.requests.get', return_value=make_get_response(404)), \
         patch('github_push.requests.put', return_value=put_resp), \
         patch('retry_utils.time.sleep'):
        with pytest.raises(Exception):
            github_push.push_data_to_github(SAMPLE_JSON, 'commit')


# ---------------------------------------------------------------------------
# export_and_push orchestrator
# ---------------------------------------------------------------------------

def test_export_and_push_returns_success_message(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    album = {'Artist': 'Radiohead', 'Album': 'OK Computer'}

    with patch('github_push.export_sheet_to_json'), \
         patch('builtins.open', create=True) as mock_open, \
         patch('github_push.os.unlink'), \
         patch('github_push.push_data_to_github', return_value=True):
        mock_open.return_value.__enter__.return_value.read.return_value = SAMPLE_JSON
        success, message = github_push.export_and_push(album_info=album)

    assert success is True
    assert 'update shortly' in message


def test_export_and_push_uses_album_in_commit_message(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    album = {'Artist': 'Radiohead', 'Album': 'OK Computer'}

    with patch('github_push.export_sheet_to_json'), \
         patch('builtins.open', create=True) as mock_open, \
         patch('github_push.os.unlink'), \
         patch('github_push.push_data_to_github', return_value=True) as mock_push:
        mock_open.return_value.__enter__.return_value.read.return_value = SAMPLE_JSON
        github_push.export_and_push(album_info=album)

    commit_msg = mock_push.call_args[0][1]
    assert 'Radiohead' in commit_msg
    assert 'OK Computer' in commit_msg


def test_export_and_push_returns_failure_message_on_exception(monkeypatch):
    """If anything throws, export_and_push should return (False, message) gracefully."""
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    with patch('github_push.export_sheet_to_json', side_effect=Exception('sheet error')):
        success, message = github_push.export_and_push()

    assert success is False
    assert 'pending' in message


def test_export_and_push_uses_generic_commit_message_when_no_album_info(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')
    monkeypatch.setenv('GITHUB_REPO_OWNER', 'testuser')
    monkeypatch.setenv('GITHUB_REPO_NAME', 'testrepo')

    import importlib
    importlib.reload(github_push)

    with patch('github_push.export_sheet_to_json'), \
         patch('builtins.open', create=True) as mock_open, \
         patch('github_push.os.unlink'), \
         patch('github_push.push_data_to_github', return_value=True) as mock_push:
        mock_open.return_value.__enter__.return_value.read.return_value = SAMPLE_JSON
        github_push.export_and_push(album_info=None)

    commit_msg = mock_push.call_args[0][1]
    assert commit_msg == 'Update album data'
