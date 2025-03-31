import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
import pandas as pd
import json
import argparse
from datetime import datetime
import os


def get_user_args():
    """Accepts user input from command line
    """
    parser = argparse.ArgumentParser(
                description='Add url')
    parser.add_argument('--url',
                        type=str,
                        help='Spotify album url',
                        required=True)
    return parser.parse_args()

# use spotify api to extract album info from given url
def get_album_info(url = '', spot_api = None):
    
    try:

        raw_info = spot_api.album(url)

    except SpotifyException as e:

        if e.http_status == 400:
            print('exception')
            return None


    artist = raw_info['artists'][0]['name']
    album = raw_info['name']
    release_date = raw_info['release_date']
    release_date_precision = raw_info['release_date_precision']

    if release_date_precision == 'day':

        year = datetime.strptime(release_date, '%Y-%m-%d').year
    else:

        year = release_date
    artwork_url = raw_info['images'][1]['url']

    to_return = {"Artist": artist,
                 "Album": album,
                 "Year": year,
                 "spotify_album_url": url,
                 "artwork_url": artwork_url}

    return to_return

def get_spotify_api():

    credentials_file = "spotify_credentials.json"
    base_dir = os.path.dirname(os.path.abspath(credentials_file))
    cred_path = os.path.join(base_dir, '..', 'spotify_credentials.json')

    with open(cred_path, 'r') as cred_file:
        creds = json.load(cred_file)

    CLIENT_ID = creds.get('CLIENT_ID')
    CLIENT_SECRET = creds.get('CLIENT_SECRET')

    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    return sp

def add_album(url = '', master_list_fname = 'aotw_master_list.xlsx'):

    sp = get_spotify_api()

    base_dir = os.path.dirname(os.path.abspath(master_list_fname))
    master_list_path = os.path.join(base_dir, '..', master_list_fname)
    df = pd.read_excel(master_list_path, index_col = 0)

    #get new album info and append
    next_album_info = get_album_info(url = url, spot_api = sp)

    if next_album_info is None:
        
        return False
    df = pd.concat([df, pd.DataFrame([next_album_info])], ignore_index = True)
    df.to_excel(master_list_path)

    return True

def main():

    args = get_user_args()
    url = args.url
    add_album(url = url)

if __name__ == "__main__":
    main()