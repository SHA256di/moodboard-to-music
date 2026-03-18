import os
import tempfile
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gemini_analyzer import analyze_image_with_gemini, get_basic_fallback_analysis
from spotify_client import create_playlist_from_songs

app = FastAPI(title="Moodboard → Music API", version="1.0.0")

# Allow frontend origins. In production, this should include your custom domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://moodboard-to-music.shawgaze.com",
        "https://shawgaze.com",
        "https://m2m-frontend-1033929125399.us-central1.run.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class Song(BaseModel):
    title: str
    artist: str


class PlaylistRequest(BaseModel):
    songs: List[Song]
    analysis: dict  # the full analysis object returned by /api/analyze
    image_b64: str | None = None  # base64-encoded JPEG for playlist cover art


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Accept an image upload and return the vibe summary, aesthetic tags,
    mood, energy level, and 25 song recommendations.
    Falls back to a default analysis if Gemini is unavailable.
    """
    # Write the uploaded file to a temp path so gemini_analyzer can read it
    suffix = os.path.splitext(file.filename)[-1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = analyze_image_with_gemini(tmp_path)

        if not result["success"]:
            # Gemini failed — return fallback so the frontend still gets a valid shape
            result = get_basic_fallback_analysis()
            result["analysis"]["fallback"] = True

        return result["analysis"]

    finally:
        os.unlink(tmp_path)  # always clean up the temp file


@app.post("/api/playlist")
async def playlist(request: PlaylistRequest):
    """
    Accept the song list and analysis object from /api/analyze,
    create a Spotify playlist, and return the embed URL.
    """
    songs = [song.model_dump() for song in request.songs]
    result = create_playlist_from_songs(songs, request.analysis, request.image_b64)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    playlist_id = result["playlist_url"].split("/")[-1].split("?")[0]

    return {
        "playlist_url": result["playlist_url"],
        "playlist_name": result["playlist_name"],
        "embed_url": f"https://open.spotify.com/embed/playlist/{playlist_id}?utm_source=generator&theme=0",
        "track_count": result["track_count"],
        "tracks_added": result["tracks_added"],
        "tracks_not_found": result.get("tracks_not_found", []),
    }


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "ok", "message": "Moodboard → Music API is running"}
