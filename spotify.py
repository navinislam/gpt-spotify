import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Retrieve Spotify API credentials from environment variables
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

# Set up Spotify API client
# Using client credentials flow for authorization
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)

# Initialize Spotipy with authorized client
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Your Spotify USER ID (from your Spotify account, not your developer account)
user_id = 'navinraven'

# Fetch playlists associated with the user_id
playlists = sp.user_playlists(user_id)


# Function to display tracks in a given playlist
def show_tracks(tracks):
    for i, item in enumerate(tracks['items']):
        # Retrieve individual track details
        track = item['track']
        # Print artist name and track name
        print(f"   {i} {track['artists'][0]['name']:32.32} {track['name']}")


# Loop through each playlist
for playlist in playlists['items']:
    # Print playlist name
    print(playlist['name'])

    # Fetch playlist details by its ID
    results = sp.playlist(playlist['id'])

    # Fetch track information from the playlist details
    tracks = results['tracks']

    # Display the tracks
    show_tracks(tracks)

