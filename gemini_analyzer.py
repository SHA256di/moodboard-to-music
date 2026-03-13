import os
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _call_gemini(parts):
    """Shared helper to call the Gemini REST API."""
    url = f"{GEMINI_BASE_URL}?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Gemini API error {response.status_code}: {response.text}")

    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def _extract_json(text):
    """Pull the first valid JSON object or array out of a response string."""
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        return json.loads(text[start:end].strip())

    for open_char, close_char in [("{", "}"), ("[", "]")]:
        if open_char in text and close_char in text:
            start = text.find(open_char)
            end = text.rfind(close_char) + 1
            return json.loads(text[start:end])

    raise ValueError("No JSON found in Gemini response")


def analyze_image_with_gemini(image_path):
    """
    Analyze an image and return specific song recommendations that match its vibe.
    Returns a dict with: success, analysis (vibe data + song list), or error.
    """
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        parts = [
            {
                "text": """You are a music curator. Analyze this image deeply and recommend specific real songs that match its vibe.

Look at:
- Colors, lighting, and visual mood (warm/cold, dark/bright, saturated/muted)
- Energy level (still and contemplative vs. dynamic and intense)
- Texture and atmosphere (gritty, dreamy, clean, chaotic)
- Setting, era, and cultural feel
- Emotional tone (nostalgic, euphoric, melancholic, rebellious, peaceful)

Based on your full analysis, recommend 25 SPECIFIC real songs that someone should listen to while looking at this image.

Pick songs that match the RHYTHM, ENERGY, TEXTURE, and EMOTIONAL FEEL — not just the genre.
Mix well-known and more niche tracks. Be specific and intentional with each pick.

Return ONLY this JSON format:
{
    "vibe_summary": "2-3 sentence description of the image's overall feel",
    "aesthetic_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "mood_descriptors": ["mood1", "mood2", "mood3"],
    "energy_level": "low / medium / high",
    "songs": [
        {"title": "Song Title", "artist": "Artist Name"},
        {"title": "Song Title", "artist": "Artist Name"}
    ]
}

Only include real songs that actually exist. Be specific — not just the most obvious choice for an artist."""
            },
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_data
                }
            }
        ]

        response_text = _call_gemini(parts)
        analysis = _extract_json(response_text)

        return {"success": True, "analysis": analysis}

    except Exception as e:
        print(f"Gemini image analysis failed: {e}")
        return {"success": False, "error": str(e)}


def get_basic_fallback_analysis():
    """Fallback when Gemini is unavailable."""
    return {
        "success": True,
        "analysis": {
            "vibe_summary": "A moody, atmospheric aesthetic with a contemplative and introspective feel.",
            "aesthetic_tags": ["moody", "atmospheric", "indie", "dreamy", "alternative"],
            "mood_descriptors": ["contemplative", "melancholic", "introspective"],
            "energy_level": "low",
            "songs": [
                {"title": "motion picture soundtrack", "artist": "Radiohead"},
                {"title": "Breathe (In the Air)", "artist": "Pink Floyd"},
                {"title": "Video Games", "artist": "Lana Del Rey"},
                {"title": "Fourth of July", "artist": "Sufjan Stevens"},
                {"title": "Holocene", "artist": "Bon Iver"},
                {"title": "Night Moves", "artist": "Bob Seger"},
                {"title": "The Night Will Always Win", "artist": "Manchester Orchestra"},
                {"title": "Blue Ridge Mountains", "artist": "Fleet Foxes"},
                {"title": "Lua", "artist": "Bright Eyes"},
                {"title": "Naked as We Came", "artist": "Iron & Wine"}
            ]
        }
    }
