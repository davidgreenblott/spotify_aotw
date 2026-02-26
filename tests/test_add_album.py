import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
import add_album

class TestGetUserArgs:

    def test_get_album_info(self):

        test_master_list_fname = 'test_master_list.xlsx'

        # dave matthews band - under the table and dreaming
        good_url = "https://open.spotify.com/album/0SeRWS3scHWplJhMppd6rJ?si=u5s_IA4zST6uM0kTon6MVQ"
        bad_url = "bad"
        # a song title as opposed to a full album
        song_url = "https://open.spotify.com/track/5SBMNVrRM8xZpyGYTYtfR9?si=f4b33e4872194451"

        # test good url
        sp = add_album.get_spotify_api()

        good_album_info = add_album.get_album_info(url = good_url, spot_api = sp)
        assert good_album_info is not None
        print(good_album_info["Album"])
        assert good_album_info["Album"] == "Under the Table and Dreaming (Expanded Edition)"
        assert good_album_info["spotify_album_id"] == "0SeRWS3scHWplJhMppd6rJ"
        assert len(good_album_info["spotify_album_id"]) == 22

        # test bad url
        bad_album_info = add_album.get_album_info(url = bad_url, spot_api = sp)
        assert bad_album_info is None

        # test song url
        song_info = add_album.get_album_info(url = song_url, spot_api = sp)
        assert song_info is None

    def test_get_spotify_api(self):

        sp = add_album.get_spotify_api()

        assert sp is not None
