import httpx as httpx
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel
from spotipy import Spotify
import os
import pandas as pd
from io import StringIO
from uuid import uuid4
from spotipy.oauth2 import SpotifyClientCredentials
from langchain.chat_models import openai, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import logging

logger = logging.getLogger(__name__)

# Setting up environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)
openai.api_key = os.getenv("OPENAI_API_KEY")
redirect_uri = "http://localhost:9000/callback"  # Ensure this matches the URI registered on Spotify
app = FastAPI()

# Setting up OAuth2
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.spotify.com/authorize",
    tokenUrl="https://accounts.spotify.com/api/token",
    scopes={
        "playlist-modify-private": "Modify user's private playlists",
        "playlist-modify-public": "Modify user's public playlists",
    },
)


def show_tracks(tracks):
    returned_tracks = []
    for i, item in enumerate(tracks["items"]):
        track = item["track"]
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
    llm = ChatOpenAI(model_name="gpt-4", temperature=0.9)
    prompt = PromptTemplate(template=playlist_template, input_variables=["playlist"])
    llm_chain = LLMChain(prompt=prompt, llm=llm)
    new_playlist = llm_chain.predict(playlist=playlist_tracks)
    playlist_data = StringIO(new_playlist.lower())
    df = pd.read_csv(playlist_data)
    return df


def get_song_uris(sp, df):
    uris = []
    for index, row in df.iterrows():
        query = f'artist:{row["artist"]} track:{row["track"]}'
        search_result = sp.search(query, type="track", limit=1)
        tracks = search_result["tracks"]["items"]
        if tracks:
            uris.append(tracks[0]["uri"])
    return uris


def create_and_populate_playlist(sp, user_id, uris, playlist_name):
    new_user_playlist = sp.user_playlist_create(user_id, playlist_name)
    new_playlist_id = new_user_playlist["id"]
    sp.playlist_add_items(new_playlist_id, uris)


class PlaylistName(BaseModel):
    playlist_name: str


async def get_spotify_client(authorization: str = Depends(oauth2_scheme)):
    token = authorization
    sp = Spotify(auth=token)
    return sp


@app.get("/")
def read_root():
    auth_url = (
            "https://accounts.spotify.com/authorize?"
            + f"client_id={client_id}&"
            + "response_type=code&"
            + f"redirect_uri={redirect_uri}&"
            + "scope=playlist-modify-private%20playlist-modify-public"
    )
    return RedirectResponse(auth_url)


async def get_http_client():
    async with httpx.AsyncClient() as client:
        yield client


@app.get("/callback")
async def callback(
        code: str, http_client: httpx.AsyncClient = Depends(get_http_client)
):
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    token_response = await http_client.post(
        "https://accounts.spotify.com/api/token", data=token_data
    )
    if token_response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=token_response.status_code,
            detail="Could not authenticate token",
        )
    token_info = token_response.json()
    print(token_info)
    access_token = token_info["access_token"]
    return {"access_token": access_token}

def background_task(sp, sp_user_id, playlist_tracks):
    df = prompt_gpt_for_playlist(playlist_tracks)
    uris = get_song_uris(sp, df)
    if uris:
        create_and_populate_playlist(sp, sp_user_id, uris, f'{sp_user_id} Playlist {uuid4()}')


@app.post("/create_playlist/")
async def create_playlist(
        playlist_data: PlaylistName,
        sp: Spotify = Depends(get_spotify_client),
        background_tasks: BackgroundTasks = BackgroundTasks()  # Corrected line
):
    playlist_name = playlist_data.playlist_name

    user_info = sp.current_user()
    sp_user_id = user_info['id']
    playlists = sp.user_playlists(sp_user_id)
    playlist_tracks = None
    for playlist in playlists['items']:
        if playlist['name'].lower() == playlist_name.lower():
            results = sp.playlist(playlist['id'], fields="tracks,next")
            tracks = results['tracks']
            playlist_tracks = show_tracks(tracks)
            break

    if playlist_tracks is None:
        return {"success": False, "detail": "Playlist not found"}

    background_tasks.add_task(background_task, sp, sp_user_id, playlist_tracks)
    return {"success": True, "detail": "Matching playlist found, processing in the background"}
