# Project Title

A FastAPI application that interfaces with Spotify and utilizes GPT-4 to generate playlist recommendations based on a provided playlist.

## Prerequisites

Before you begin, ensure you have met the following requirements:
- You have a working Python 3.8+ environment.
- You have a Spotify developer account and have created an application to obtain `client_id` and `client_secret`.
- You have the `fastapi`, `httpx`, `spotipy`, `pandas`, and `pydantic` libraries installed in your Python environment.
- You have set up the necessary environment variables: `OPENAI_API_KEY`, `SPOTIFY_CLIENT_ID`, and `SPOTIFY_CLIENT_SECRET`.
- For GPT-4 interactions, ensure you have access to the GPT-4 model, and the `langchain` library is installed and properly configured.

## Setup and Installation

1. Clone the repository to your local machine:
```bash
git clone <repository_url>
cd <repository_directory>
```

2. Create a virtual environment and install the necessary dependencies:
```
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```
3. Set up your environment variables. You can use a .env file for this:
```
echo "OPENAI_API_KEY=your_openai_api_key" >> .env
echo "SPOTIFY_CLIENT_ID=your_spotify_client_id" >> .env
echo "SPOTIFY_CLIENT_SECRET=your_spotify_client_secret" >> .env
```
4. Run the FastAPI application using makefile
``` 
make api
```

## Usage
1. Access the root path of the application (http://localhost:8000/) in a web browser. This will redirect you to Spotify's authorization page.

2. Authorize the application to access and modify your Spotify playlists.

3. Once redirected back, use the provided access token to make a POST request to /create_playlist/ with a JSON body containing the playlist_name of the playlist you want to use as a seed for recommendations.

**Example request body**
```
{
    "playlist_name": "My Favorite Playlist"
}
```
4. The application will find the specified playlist, extract its tracks, and use GPT-4 to generate a list of similar tracks. A new playlist will be created and populated with these recommended tracks, asynchronously in the background.

## API Endpoints
**GET** /: Initiates the Spotify authorization flow.
**GET** /callback: Handles the callback from Spotify with the authorization code.
**POST** /create_playlist/: Accepts a playlist_name in the request body and initiates the playlist creation and population process.


## Troubleshooting
If you encounter authentication issues, ensure that your environment variables are set correctly and that your Spotify developer application settings (especially the redirect URI) match the configuration in the code.