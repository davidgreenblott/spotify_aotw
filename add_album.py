import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import json
import argparse
from datetime import datetime


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
    
    raw_info = spot_api.album(url)

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

def main():

    # get user args
    args = get_user_args()
    url = args.url

    # Setup spotify credentials
    with open('spotify_credentials.json', 'r') as cred_file:
        creds = json.load(cred_file)

    CLIENT_ID = creds.get('CLIENT_ID')
    CLIENT_SECRET = creds.get('CLIENT_SECRET')

    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # import masater list
    master_list_fname = 'aotw_master_list.xlsx'
    df = pd.read_excel(master_list_fname)

    #get new album info and append
    next_album_info = get_album_info(url = url, spot_api = sp)
    df = pd.concat([df, pd.DataFrame([next_album_info])], ignore_index = True)
    df.to_excel('aotw_master_list.xlsx')
    

if __name__ == "__main__":
    main()