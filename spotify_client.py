import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8888/callback/"
SCOPE = "playlist-modify-public playlist-modify-private"


def get_spotify_client():
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=".spotify_cache"
    )
    return spotipy.Spotify(auth_manager=auth_manager)


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


def create_playlist_from_songs(songs, analysis):
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
