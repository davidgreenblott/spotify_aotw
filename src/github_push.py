import base64
import json
import os
import tempfile
from typing import Optional, Tuple

import requests

from export_json import export_sheet_to_json
from logging_config import setup_logging
from retry_utils import retry_with_backoff

logger = setup_logging()

# ---------------------------------------------------------------------------
# Configuration — all read from environment variables so nothing is hardcoded
# ---------------------------------------------------------------------------

GITHUB_TOKEN      = os.getenv('GITHUB_TOKEN')
GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER')  # e.g. 'davidgreenblott'
GITHUB_REPO_NAME  = os.getenv('GITHUB_REPO_NAME')   # e.g. 'aotw-website'
GITHUB_FILE_PATH  = 'public/data.json'               # path inside the repo (Vite serves public/ at root)
GITHUB_BRANCH     = 'main'


# ---------------------------------------------------------------------------
# Core push function
# ---------------------------------------------------------------------------

@retry_with_backoff(
    max_attempts=3,
    base_delay=2.0,
    exceptions=(requests.exceptions.RequestException,),
)
def push_data_to_github(json_content: str, commit_message: str) -> bool:
    """Push data.json to a GitHub repo via the REST API.

    Uses the GitHub Contents API (PUT /repos/:owner/:repo/contents/:path).
    If the file already exists in the repo, its current SHA is fetched first
    (GitHub requires it to update an existing file).

    Args:
        json_content:   The JSON string to write into the file.
        commit_message: Git commit message for the change.

    Returns:
        True on success. Raises on failure (triggers retry decorator).
    """
    if not all([GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
        raise ValueError(
            'GitHub config incomplete. '
            'Set GITHUB_TOKEN, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME env vars.'
        )

    api_url = (
        f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/'
        f'{GITHUB_REPO_NAME}/contents/{GITHUB_FILE_PATH}'
    )
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }

    # --- Step 1: Get the current file SHA (required to update an existing file) ---
    logger.info('Fetching current %s SHA from GitHub...', GITHUB_FILE_PATH)
    get_resp = requests.get(api_url, headers=headers, params={'ref': GITHUB_BRANCH})

    current_sha: Optional[str] = None
    if get_resp.status_code == 200:
        current_sha = get_resp.json()['sha']
        logger.info('Found existing file (SHA: %s)', current_sha[:7])
    elif get_resp.status_code == 404:
        logger.info('File does not exist yet — will create it.')
    else:
        # Any other status (401, 403, 5xx…) is unexpected — raise to trigger retry
        get_resp.raise_for_status()

    # --- Step 2: Encode the JSON content to base64 (GitHub API requirement) ---
    content_b64 = base64.b64encode(json_content.encode('utf-8')).decode('utf-8')

    # --- Step 3: Build the request body ---
    payload = {
        'message': commit_message,
        'content': content_b64,
        'branch':  GITHUB_BRANCH,
    }
    # SHA must be included when updating; omitted when creating for the first time
    if current_sha:
        payload['sha'] = current_sha

    # --- Step 4: Push ---
    logger.info('Pushing %s to GitHub (%s/%s)...', GITHUB_FILE_PATH, GITHUB_REPO_OWNER, GITHUB_REPO_NAME)
    put_resp = requests.put(api_url, headers=headers, json=payload)

    if put_resp.status_code in (200, 201):
        commit_sha = put_resp.json()['commit']['sha']
        logger.info('GitHub push succeeded. Commit: %s', commit_sha[:7])
        return True

    # Non-success status — raise so the retry decorator can handle transient errors
    put_resp.raise_for_status()
    return False  # unreachable, but satisfies type checkers


# ---------------------------------------------------------------------------
# Orchestrator: export sheet → push to GitHub
# ---------------------------------------------------------------------------

def export_and_push(
    sheet_id=None,
    sheet_tab=None,
    creds_path=None,
    album_info: Optional[dict] = None,
) -> Tuple[bool, str]:
    """Export the full Google Sheet to JSON, then push it to GitHub.

    This is called after a successful sheet append so the website stays in sync.
    If the push fails (network blip, quota, etc.) the album is already safely
    stored in the sheet — the next successful push will self-heal.

    Args:
        sheet_id, sheet_tab, creds_path: Passed through to export_sheet_to_json.
        album_info: Optional dict with 'Artist'/'Album' keys; used in commit message.

    Returns:
        (success: bool, message: str) — message is suitable for the Telegram reply.
    """
    try:
        # Write to a temp file so we don't clobber any local data.json
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as tmp:
            tmp_path = tmp.name

        export_sheet_to_json(
            sheet_id=sheet_id,
            sheet_tab=sheet_tab,
            creds_path=creds_path,
            output_path=tmp_path,
        )

        with open(tmp_path, 'r', encoding='utf-8') as f:
            json_content = f.read()

        os.unlink(tmp_path)

        # Build a descriptive commit message if we know which album was just added
        if album_info:
            artist = album_info.get('Artist', 'Unknown')
            album  = album_info.get('Album',  'Unknown')
            commit_msg = f'Add {artist} - {album}'
        else:
            commit_msg = 'Update album data'

        push_data_to_github(json_content, commit_msg)
        return True, 'Website will update shortly'

    except Exception as e:
        logger.error('export_and_push failed: %s', e, exc_info=True)
        return False, 'Website update pending (will sync on next run)'
