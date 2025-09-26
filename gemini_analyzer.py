import os
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERVICE_ACCOUNT_PATH = "/Users/shawdi/Desktop/m2m files/moodboard-to-music-0be1a4b8bb98.json"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
elif os.path.exists(SERVICE_ACCOUNT_PATH):
    # Try using service account
    import google.auth
    from google.auth.transport.requests import Request
    credentials, project = google.auth.load_credentials_from_file(SERVICE_ACCOUNT_PATH)
    genai.configure(credentials=credentials)

def analyze_image_with_gemini(image_path):
    """
    Use Gemini 1.5 Vision to analyze image and extract detailed aesthetic information
    Returns both tags and genre recommendations
    """
    try:
        import base64
        import requests
        import json
        
        # Load and prepare image
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Use REST API directly with your API key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": """Analyze this image and provide a detailed aesthetic analysis for music recommendation.
        
        Please provide:
        1. AESTHETIC TAGS (5-8 descriptive words): Describe the visual mood, style, colors, atmosphere
        2. MUSIC GENRES (3-5 specific genres): What music genres would match this aesthetic?
        3. MOOD DESCRIPTORS (3-4 words): Emotional tone and energy level
        4. TIME PERIOD/ERA: What decade or era does this evoke?
        5. CULTURAL CONTEXT: Any specific subcultures, movements, or scenes this relates to
        
        Format your response as JSON:
        {
            "aesthetic_tags": ["tag1", "tag2", "tag3", ...],
            "music_genres": ["genre1", "genre2", "genre3", ...],
            "mood_descriptors": ["mood1", "mood2", "mood3"],
            "time_period": "era description",
            "cultural_context": "cultural description",
            "confidence": 0.85
        }
        
        Be specific with genres (e.g., "shoegaze" instead of just "alternative", "future funk" instead of just "electronic").
        Consider the lighting, colors, textures, subjects, and overall composition."""
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_data
                        }
                    }
                ]
            }]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            response_text = data['candidates'][0]['content']['parts'][0]['text']
            
            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text and "}" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
            
            # Parse JSON
            analysis = json.loads(json_text)
            
            return {
                'success': True,
                'analysis': analysis,
                'raw_response': response_text
            }
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
    except Exception as e:
        print(f"Gemini analysis failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'fallback_tags': ['aesthetic', 'moody', 'vintage', 'dreamy']  # Fallback to basic tags
        }

def get_enhanced_genre_mapping(aesthetic_tags, mood_descriptors, music_genres, time_period, cultural_context):
    """
    Use Gemini to create dynamic genre mapping based on the full analysis
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Based on this aesthetic analysis:
        - Aesthetic tags: {aesthetic_tags}
        - Mood: {mood_descriptors} 
        - Suggested genres: {music_genres}
        - Time period: {time_period}
        - Cultural context: {cultural_context}
        
        Provide a refined list of 4-6 specific music genres that would create the perfect playlist.
        
        Focus on:
        - Specific subgenres rather than broad categories
        - Current and relevant artists/styles
        - Cohesive flow between genres
        - Avoiding obscure genres that won't have good tracks
        
        Return as a simple JSON array: ["genre1", "genre2", "genre3", ...]
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON array
        if "[" in response_text and "]" in response_text:
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            json_text = response_text[json_start:json_end]
            
            import json
            genres = json.loads(json_text)
            return genres
        
        # Fallback to basic mapping if JSON parsing fails
        return music_genres[:5] if music_genres else ['indie rock', 'alternative', 'electronic']
        
    except Exception as e:
        print(f"Genre mapping failed: {e}")
        return music_genres[:5] if music_genres else ['indie rock', 'alternative', 'electronic']

# Simple fallback without external dependencies
def get_basic_fallback_analysis():
    """Provide basic aesthetic analysis when Gemini fails"""
    return {
        'success': True,
        'analysis': {
            'aesthetic_tags': ['aesthetic', 'moody', 'atmospheric', 'indie', 'alternative', 'contemporary'],
            'music_genres': ['indie rock', 'alternative', 'electronic', 'ambient', 'indie pop', 'chill'],
            'mood_descriptors': ['atmospheric', 'contemplative', 'moody'],
            'time_period': 'contemporary',
            'cultural_context': 'modern indie aesthetic',
            'confidence': 0.5
        }
    }
