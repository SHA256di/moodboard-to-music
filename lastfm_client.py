import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
BASE_URL = "http://ws.audioscrobbler.com/2.0/"

def get_top_tracks_for_tag(tag, limit=5):
    params = {
        "method": "tag.gettoptracks",
        "tag": tag,
        "api_key": API_KEY,
        "format": "json",
        "limit": limit
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        tracks = data.get("tracks", {}).get("track", [])
        return [(t["name"], t["artist"]["name"]) for t in tracks]
    else:
        return []
