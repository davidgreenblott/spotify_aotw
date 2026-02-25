import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from validation import is_valid_spotify_album_url, extract_spotify_album_id, validate_album_metadata


VALID_ALBUM_ID = "0SeRWS3scHWplJhMppd6rJ"
VALID_URL = f"https://open.spotify.com/album/{VALID_ALBUM_ID}"
VALID_URL_WITH_SI = f"https://open.spotify.com/album/{VALID_ALBUM_ID}?si=abc123"


class TestIsValidSpotifyAlbumUrl:

    def test_valid_url(self):
        assert is_valid_spotify_album_url(VALID_URL) is True

    def test_valid_url_with_query_param(self):
        assert is_valid_spotify_album_url(VALID_URL_WITH_SI) is True

    def test_track_url_rejected(self):
        assert is_valid_spotify_album_url("https://open.spotify.com/track/5SBMNVrRM8xZpyGYTYtfR9") is False

    def test_playlist_url_rejected(self):
        assert is_valid_spotify_album_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M") is False

    def test_artist_url_rejected(self):
        assert is_valid_spotify_album_url("https://open.spotify.com/artist/2WX2uTcsvV5OnS0inACecP") is False

    def test_empty_string_rejected(self):
        assert is_valid_spotify_album_url("") is False

    def test_plain_text_rejected(self):
        assert is_valid_spotify_album_url("not a url") is False

    def test_wrong_domain_rejected(self):
        assert is_valid_spotify_album_url("https://spotify.com/album/0SeRWS3scHWplJhMppd6rJ") is False

    def test_short_album_id_rejected(self):
        assert is_valid_spotify_album_url("https://open.spotify.com/album/tooshort") is False

    def test_long_album_id_rejected(self):
        assert is_valid_spotify_album_url("https://open.spotify.com/album/toolongidthatexceeds22chars") is False


class TestExtractSpotifyAlbumId:

    def test_extracts_id_from_plain_url(self):
        assert extract_spotify_album_id(VALID_URL) == VALID_ALBUM_ID

    def test_extracts_id_from_url_with_query_param(self):
        assert extract_spotify_album_id(VALID_URL_WITH_SI) == VALID_ALBUM_ID

    def test_returns_none_for_non_album_url(self):
        assert extract_spotify_album_id("https://open.spotify.com/track/5SBMNVrRM8xZpyGYTYtfR9") is None

    def test_returns_none_for_empty_string(self):
        assert extract_spotify_album_id("") is None

    def test_returns_none_for_plain_text(self):
        assert extract_spotify_album_id("not a url") is None


class TestValidateAlbumMetadata:

    def test_valid_complete_metadata(self):
        album_info = {
            "Artist": "Dave Matthews Band",
            "Album": "Under the Table and Dreaming",
            "Year": 1994,
            "spotify_album_url": VALID_URL,
            "artwork_url": "https://i.scdn.co/image/abc123",
        }
        is_valid, error = validate_album_metadata(album_info)
        assert is_valid is True
        assert error == ""

    def test_missing_artist(self):
        album_info = {
            "Album": "Some Album",
            "Year": 2020,
            "spotify_album_url": VALID_URL,
            "artwork_url": "https://i.scdn.co/image/abc123",
        }
        is_valid, error = validate_album_metadata(album_info)
        assert is_valid is False
        assert "Artist" in error

    def test_missing_multiple_fields(self):
        album_info = {"Artist": "Someone"}
        is_valid, error = validate_album_metadata(album_info)
        assert is_valid is False
        assert "Album" in error
        assert "Year" in error

    def test_empty_dict(self):
        is_valid, error = validate_album_metadata({})
        assert is_valid is False
        assert error != ""

    def test_empty_string_field_treated_as_missing(self):
        album_info = {
            "Artist": "",
            "Album": "Some Album",
            "Year": 2020,
            "spotify_album_url": VALID_URL,
            "artwork_url": "https://i.scdn.co/image/abc123",
        }
        is_valid, error = validate_album_metadata(album_info)
        assert is_valid is False
        assert "Artist" in error
