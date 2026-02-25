import re
from typing import Optional


def is_valid_spotify_album_url(url: str) -> bool:
    """Check if URL matches Spotify album pattern.

    Valid formats:
    - https://open.spotify.com/album/{album_id}
    - https://open.spotify.com/album/{album_id}?si=...
    """
    pattern = r'^https://open\.spotify\.com/album/[a-zA-Z0-9]{22}(\?.*)?$'
    return bool(re.match(pattern, url))


def extract_spotify_album_id(url: str) -> Optional[str]:
    """Extract album ID from Spotify URL.

    Returns 22-character album ID or None if not found.
    """
    match = re.search(r'/album/([a-zA-Z0-9]{22})', url)
    return match.group(1) if match else None


def validate_album_metadata(album_info: dict) -> tuple:
    """Validate that all required fields are present in Spotify response.

    Returns (is_valid, error_message).
    """
    required_fields = ['Artist', 'Album', 'Year', 'spotify_album_url', 'artwork_url']
    missing = [f for f in required_fields if not album_info.get(f)]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, ""
