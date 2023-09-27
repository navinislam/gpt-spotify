import os
from uuid import uuid4

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from langchain.chat_models import openai, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
from io import StringIO

# Setup for Spotify API
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
user_id = os.getenv("USER_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
playlist_name = 'Workout'


sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri="http://localhost:9000",
    scope="playlist-modify-private,playlist-modify-public",
    cache_path=None)

token_info = sp_oauth.get_access_token(as_dict=True)
print(token_info)
sp = spotipy.Spotify(auth=token_info['access_token'])
# Retrieve existing playlists
playlists = sp.user_playlists(user_id)


def show_tracks(tracks):
    returned_tracks = []
    for i, item in enumerate(tracks['items']):
        # Retrieve individual track details
        track = item['track']
        # Print artist name and track name
        returned_tracks.append(f"  {track['artists'][0]['name']:32.32} {track['name']}")
        # print(f"  {track['artists'][0]['name']:32.32} {track['name']}")
    return returned_tracks


def prompt_gpt_for_playlist():
    playlist_tracks = None

    for playlist in playlists['items']:

        if playlist['name'] == playlist_name:
            results = sp.playlist(playlist['id'])
            tracks = results['tracks']
            playlist_tracks = show_tracks(tracks)

    playlist_template = """Based on my provided playlist 
    could you recommend a list of similar songs that are available on Spotify.
    Make sure no songs are repeated from my playlist provided.
    Make sure the songs are real songs and songs that would be available on spotify.
    Return in csv format with column "artist" and "track".
    Playlist: {playlist}
    """

    llm = ChatOpenAI(model_name='gpt-4', temperature=0.9)
    prompt = PromptTemplate(template=playlist_template, input_variables=['playlist'])
    llm_chain = LLMChain(prompt=prompt, llm=llm)

    new_playlist = llm_chain.predict(playlist=playlist_tracks)
    playlist_data = StringIO(new_playlist.lower())

    # Read the data into a DataFrame
    df = pd.read_csv(playlist_data)

    # Show the DataFrame
    print(df)
    return df


# Function to get URIs for the songs in the DataFrame
def get_song_uris(sp, df):
    uris = []
    for index, row in df.iterrows():
        query = f'artist:{row["artist"]} track:{row["track"]}'
        search_result = sp.search(query, type='track', limit=1)
        tracks = search_result['tracks']['items']
        if tracks:
            uris.append(tracks[0]['uri'])
    return uris


# Function to create a playlist and populate it with tracks
def create_and_populate_playlist(sp, user_id, uris, playlist_name):
    # Create a new playlist
    new_user_playlist = sp.user_playlist_create(user_id, playlist_name)
    new_playlist_id = new_user_playlist['id']

    # Add tracks to the playlist
    sp.playlist_add_items(new_playlist_id, uris)


# Step 1: Get the URIs of the songs in the DataFrame

def create_playlists_using_uris(sp, df):
    uris = get_song_uris(sp, df)

    print(uris)
    # Step 2 and 3: Create new playlist and populate it
    if uris:  # Only proceed if we found any URIs
        print('FOUND URIS')
        create_and_populate_playlist(sp, user_id, uris, f'Test Playlist {uuid4()}')
        print('created playlist')


