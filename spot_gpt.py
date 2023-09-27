import requests
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel
from spotipy import Spotify
import os
import pandas as pd
from io import StringIO
from uuid import uuid4
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from langchain.chat_models import openai, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Setting up environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
user_id = os.getenv("USER_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
# playlist_name = 'Anime Workout'
redirect_uri = "http://localhost:9000"
app = FastAPI()

# Setting up OAuth2
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.spotify.com/authorize",
    tokenUrl="https://accounts.spotify.com/api/token",
    scopes={
        "playlist-modify-private": "Modify user's private playlists",
        "playlist-modify-public": "Modify user's public playlists"
    }
)


async def get_spotify_client(token: str = Depends(oauth2_scheme)):
    # Here you might exchange the 'token' (actually an authorization code) for an access token
    # using HTTP requests, for which you would use your client ID and secret.

    token_data = {
        'grant_type': 'authorization_code',
        'code': token,
        'redirect_uri': os.getenv("SPOTIPY_REDIRECT_URI"),
        'client_id': os.getenv("SPOTIFY_CLIENT_ID"),
        'client_secret': os.getenv("SPOTIFY_CLIENT_SECRET"),
        'scope': 'playlist-modify-private playlist-modify-public'
    }

    token_response = requests.post('https://accounts.spotify.com/api/token', data=token_data)
    if token_response.status_code != 200:
        raise HTTPException(status_code=token_response.status_code, detail="Could not authenticate token")

    token_info = token_response.json()
    access_token = token_info['access_token']
    sp = Spotify(auth=access_token)
    return sp


def show_tracks(tracks):
    returned_tracks = []
    for i, item in enumerate(tracks['items']):
        track = item['track']
        returned_tracks.append(f"{track['artists'][0]['name']},{track['name']}")
    return returned_tracks


def prompt_gpt_for_playlist(playlist_tracks):
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
    df = pd.read_csv(playlist_data)
    return df


def get_song_uris(sp, df):
    uris = []
    for index, row in df.iterrows():
        query = f'artist:{row["artist"]} track:{row["track"]}'
        search_result = sp.search(query, type='track', limit=1)
        tracks = search_result['tracks']['items']
        if tracks:
            uris.append(tracks[0]['uri'])
    return uris


def create_and_populate_playlist(sp, user_id, uris, playlist_name):
    new_user_playlist = sp.user_playlist_create(user_id, playlist_name)
    new_playlist_id = new_user_playlist['id']
    sp.playlist_add_items(new_playlist_id, uris)


class PlaylistName(BaseModel):
    playlist_name: str

@app.get("/")
def read_root():
    auth_url = "https://accounts.spotify.com/authorize?" + \
               f"client_id={client_id}&" + \
               "response_type=code&" + \
               f"redirect_uri={redirect_uri}&" + \
               "scope=playlist-modify-private%20playlist-modify-public"
    return RedirectResponse(auth_url)


@app.get("/callback")
async def callback(code: str):
    # Prepare data to fetch the access token from Spotify
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,  # Using the redirect_uri you've set above
        'client_id': client_id,  # Using the client_id you've set above
        'client_secret': client_secret,  # Using the client_secret you've set above
    }

    # Make a POST request to get the access token
    token_response = requests.post('https://accounts.spotify.com/api/token', data=token_data)

    # Check if the request was successful
    if token_response.status_code != 200:
        raise HTTPException(status_code=token_response.status_code, detail="Could not authenticate token")

    # Parse the JSON response to get the access token
    token_info = token_response.json()
    access_token = token_info['access_token']

    # Optional: Store the access token for future use (database, session, etc.)

    return {"access_token": access_token}

@app.post("/create_playlist/")
async def create_playlist(playlist_data: PlaylistName, sp: Spotify = Depends(get_spotify_client)):
    playlist_name = playlist_data.playlist_name  # Extracting the playlist name from request body

    # Step 1: Generate your DataFrame using your GPT-based prompt
    playlists = sp.user_playlists(sp.current_user())
    playlist_tracks = None
    for playlist in playlists['items']:
        if playlist['name'] == playlist_name:
            results = sp.playlist(playlist['id'], fields="tracks,next")
            tracks = results['tracks']
            playlist_tracks = show_tracks(tracks)
            break  # No need to continue if we found the playlist

    if playlist_tracks is None:
        return {"success": False, "detail": "Playlist not found"}

    df = prompt_gpt_for_playlist(playlist_tracks)

    # Step 2: Get the URIs based on the DataFrame
    uris = get_song_uris(sp, df)

    # Step 3: Create new playlist and populate it
    if uris:
        create_and_populate_playlist(sp, user_id, uris, f'Test Playlist {uuid4()}')
        return {"success": True}
    else:
        return {"success": False, "detail": "No URIs found"}
