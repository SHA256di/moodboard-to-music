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

# Simple in-memory token cache so we don't refresh on every request
_ACCESS_TOKEN: str | None = None
_ACCESS_TOKEN_EXPIRES_AT: float = 0.0


def get_access_token() -> str:
    """
    Get a valid Spotify access token using the long-lived refresh token.
    Caches the token in memory until it's close to expiring.
    """
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRES_AT

    if not CLIENT_ID or not CLIENT_SECRET or not SPOTIFY_REFRESH_TOKEN:
        raise RuntimeError("Spotify credentials or refresh token are not set in the environment.")

    now = time.time()
    # Reuse token if it is still valid for at least another 60 seconds
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
    # Spotify tokens are typically valid for 3600s; be conservative
    expires_in = data.get("expires_in", 3600)
    _ACCESS_TOKEN_EXPIRES_AT = now + expires_in

    return _ACCESS_TOKEN


def get_spotify_client() -> spotipy.Spotify:
    """
    Return a Spotipy client authenticated with the current access token.
    This does not perform any interactive OAuth flow, so it works on Railway.
    """
    token = get_access_token()
    return spotipy.Spotify(auth=token)


def find_track(sp, title, artist):
    """
    Try to find a track on Spotify using 3 strategies, each progressively looser.

    Tier 1: Exact field search — track:"title" artist:"artist"
    Tier 2: Loose plain search — title artist (handles minor title variations)
    Tier 3: Artist fallback — search the artist and return their most popular track
    """

    # Tier 1: exact match
    results = sp.search(q=f'track:"{title}" artist:"{artist}"', type="track", limit=1)
    items = results["tracks"]["items"]
    if items:
        return items[0]["uri"], items[0]["name"], items[0]["artists"][0]["name"], "exact"

    # Tier 2: loose match
    results = sp.search(q=f"{title} {artist}", type="track", limit=1)
    items = results["tracks"]["items"]
    if items:
        return items[0]["uri"], items[0]["name"], items[0]["artists"][0]["name"], "loose"

    # Tier 3: artist fallback — grab their most popular track
    results = sp.search(q=f"artist:{artist}", type="artist", limit=1)
    artist_items = results["artists"]["items"]
    if artist_items:
        artist_id = artist_items[0]["id"]
        top_tracks = sp.artist_top_tracks(artist_id, country="US")["tracks"]
        if top_tracks:
            track = top_tracks[0]
            return track["uri"], track["name"], track["artists"][0]["name"], "artist_fallback"

    return None, None, None, "not_found"


def upload_playlist_cover(sp, playlist_id, image_b64: str):
    """
    Set a custom cover image on a Spotify playlist.
    Resizes and recompresses the image to stay under Spotify's 256KB limit.
    """
    try:
        image_bytes = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((640, 640))

        quality = 85
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)

        # Reduce quality until the file is under Spotify's 256KB limit
        while buffer.tell() > 200_000 and quality > 20:
            quality -= 10
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)

        compressed_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        sp.playlist_upload_cover_image(playlist_id, compressed_b64)
    except Exception as e:
        print(f"Playlist cover upload failed (non-fatal): {e}")


def create_playlist_from_songs(songs, analysis, image_b64: str | None = None):
    """
    Build a Spotify playlist from a list of {title, artist} dicts.
    Uses 3-tier search to maximize how many songs get found.

    Returns a result dict with success status, playlist URL, and track details.
    """
    try:
        sp = get_spotify_client()
        user_id = sp.current_user()["id"]

        # Build playlist name from aesthetic tags
        tags = analysis.get("aesthetic_tags", [])[:3]
        playlist_name = f"Moodboard: {' · '.join(t.title() for t in tags)}" if tags else "Moodboard Mix"
        vibe = analysis.get("vibe_summary", "AI-generated playlist from image analysis")
        playlist_description = vibe[:300]  # Spotify caps description at 300 chars

        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=True,
            description=playlist_description
        )

        track_uris = []
        tracks_added = []
        tracks_not_found = []

        for song in songs:
            title = song.get("title", "")
            artist = song.get("artist", "")

            uri, found_title, found_artist, method = find_track(sp, title, artist)

            if uri and uri not in track_uris:
                track_uris.append(uri)
                label = f"{found_title} by {found_artist}"
                if method == "artist_fallback":
                    label += " (artist fallback)"
                elif method == "loose":
                    label += " (close match)"
                tracks_added.append(label)
            else:
                tracks_not_found.append(f"{title} by {artist}")

        # Add tracks in batches of 100 (Spotify API limit)
        for i in range(0, len(track_uris), 100):
            sp.playlist_add_items(playlist["id"], track_uris[i:i + 100])

        # Set the uploaded image as the playlist cover
        if image_b64:
            upload_playlist_cover(sp, playlist["id"], image_b64)

        return {
            "success": True,
            "playlist_url": playlist["external_urls"]["spotify"],
            "playlist_name": playlist_name,
            "track_count": len(track_uris),
            "tracks_added": tracks_added,
            "tracks_not_found": tracks_not_found
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
