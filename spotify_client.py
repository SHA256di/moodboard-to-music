import os
import io
import time
import base64
import requests
import spotipy
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

_ACCESS_TOKEN: str | None = None
_ACCESS_TOKEN_EXPIRES_AT: float = 0.0

def get_access_token() -> str:
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRES_AT

    if not CLIENT_ID or not CLIENT_SECRET or not SPOTIFY_REFRESH_TOKEN:
        raise RuntimeError("Spotify credentials missing in environment.")

    now = time.time()
    if _ACCESS_TOKEN and now < _ACCESS_TOKEN_EXPIRES_AT - 60:
        return _ACCESS_TOKEN

    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": SPOTIFY_REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    _ACCESS_TOKEN = data["access_token"]
    _ACCESS_TOKEN_EXPIRES_AT = now + data.get("expires_in", 3600)
    return _ACCESS_TOKEN

def get_spotify_client() -> spotipy.Spotify:
    return spotipy.Spotify(auth=get_access_token())

def find_track(sp, title, artist):
    # Tier 1: Exact
    results = sp.search(q=f'track:"{title}" artist:"{artist}"', type="track", limit=1)
    if results["tracks"]["items"]:
        item = results["tracks"]["items"][0]
        return item["uri"], item["name"], item["artists"][0]["name"], "exact"

    # Tier 2: Loose
    results = sp.search(q=f"{title} {artist}", type="track", limit=1)
    if results["tracks"]["items"]:
        item = results["tracks"]["items"][0]
        return item["uri"], item["name"], item["artists"][0]["name"], "loose"

    # Tier 3: Artist fallback — get artist's albums then grab first track
    # (artist_top_tracks removed in Feb 2026 Spotify API update)
    try:
        results = sp.search(q=f"artist:{artist}", type="artist", limit=1)
        if results["artists"]["items"]:
            artist_id = results["artists"]["items"][0]["id"]
            albums = sp.artist_albums(artist_id, album_type="album,single", limit=1)
            if albums["items"]:
                album_id = albums["items"][0]["id"]
                tracks = sp.album_tracks(album_id, limit=1)
                if tracks["items"]:
                    t = tracks["items"][0]
                    return t["uri"], t["name"], t["artists"][0]["name"], "artist_fallback"
    except Exception:
        pass

    return None, None, None, "not_found"

def upload_playlist_cover(sp, playlist_id, image_b64: str):
    try:
        image_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((640, 640))
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        
        # Spotify has a strict 256KB limit for covers
        if buffer.tell() > 200_000:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=50)

        compressed_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        sp.playlist_upload_cover_image(playlist_id, compressed_b64)
    except Exception as e:
        print(f"Cover upload failed: {e}")

def create_playlist_from_songs(songs, analysis, image_b64: str | None = None):
    try:
        sp = get_spotify_client()
        tags = analysis.get("aesthetic_tags", [])[:3]
        name = f"Mood: {' · '.join(t.title() for t in tags)}" if tags else "Moodboard Mix"
        desc = analysis.get("vibe_summary", "")[:300]

        # POST /me/playlists (POST /users/{id}/playlists removed in Feb 2026)
        token = get_access_token()
        resp = requests.post(
            "https://api.spotify.com/v1/me/playlists",
            json={"name": name, "public": True, "description": desc},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        playlist = resp.json()

        track_uris = []
        tracks_added = []
        
        for song in songs:
            uri, f_title, f_artist, method = find_track(sp, song.get("title"), song.get("artist"))
            if uri and uri not in track_uris:
                track_uris.append(uri)
                tracks_added.append(f"{f_title} by {f_artist}")

        if track_uris:
            # POST /playlists/{id}/items (POST /playlists/{id}/tracks removed Feb 2026)
            token = get_access_token()
            for i in range(0, len(track_uris), 100):
                requests.post(
                    f"https://api.spotify.com/v1/playlists/{playlist['id']}/items",
                    json={"uris": track_uris[i:i + 100]},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    timeout=15,
                ).raise_for_status()

        if image_b64:
            upload_playlist_cover(sp, playlist["id"], image_b64)

        return {
            "success": True,
            "playlist_url": playlist["external_urls"]["spotify"],
            "playlist_name": name,
            "track_count": len(track_uris),
            "tracks_added": tracks_added
        }
    except Exception as e:
        return {"success": False, "error": str(e)}