import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8888/callback/"

# Spotify scopes needed for playlist creation
SCOPE = "playlist-modify-public playlist-modify-private"

def get_spotify_client():
    """Initialize and return Spotify client with OAuth"""
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=".spotify_cache"
    )
    return spotipy.Spotify(auth_manager=auth_manager)

def search_track(sp, track_name, artist_name):
    """Search for a track on Spotify and return track URI"""
    query = f"track:{track_name} artist:{artist_name}"
    results = sp.search(q=query, type='track', limit=1)
    
    if results['tracks']['items']:
        return results['tracks']['items'][0]['uri']
    return None

def create_playlist_from_genres(genre_tracks, image_tags):
    """Create a Spotify playlist from genre tracks"""
    try:
        sp = get_spotify_client()
        user_id = sp.current_user()['id']
        
        # Create playlist name based on top aesthetic tags
        top_tags = [tag for tag, _ in image_tags[:3]]  # Top 3 tags
        playlist_name = f"Moodboard Mix: {' + '.join(top_tags).title()}"
        playlist_description = f"Generated from image aesthetics: {', '.join([tag for tag, _ in image_tags[:5]])}"
        
        # Create the playlist
        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=True,
            description=playlist_description
        )
        
        track_uris = []
        added_tracks = []
        
        # Search for tracks on Spotify and collect URIs
        for genre, tracks in genre_tracks.items():
            for track_name, artist_name in tracks[:5]:  # Top 5 from each genre
                track_uri = search_track(sp, track_name, artist_name)
                if track_uri and track_uri not in track_uris:  # Avoid duplicates
                    track_uris.append(track_uri)
                    added_tracks.append(f"{track_name} by {artist_name}")
        
        # Add tracks to playlist
        if track_uris:
            # Spotify allows max 100 tracks per request
            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                sp.playlist_add_items(playlist['id'], batch)
        
        return {
            'success': True,
            'playlist_url': playlist['external_urls']['spotify'],
            'playlist_name': playlist_name,
            'track_count': len(track_uris),
            'tracks_added': added_tracks
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_genre_tracks_for_playlist(tags):
    """Get tracks for each genre from the top aesthetic tags"""
    from tag_to_music import map_clip_tag_to_lastfm
    from lastfm_client import get_top_tracks_for_tag
    
    genre_tracks = {}
    
    # Get tracks for top 3-4 aesthetic tags to keep playlist manageable
    for tag, score in tags[:4]:
        genres = map_clip_tag_to_lastfm(tag)
        if genres:
            for genre in genres[:2]:  # Limit to 2 genres per tag
                tracks = get_top_tracks_for_tag(genre, limit=5)
                if tracks:
                    genre_tracks[genre] = tracks
    
    return genre_tracks
