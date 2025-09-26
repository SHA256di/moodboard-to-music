import streamlit as st
from gemini_analyzer import analyze_image_with_gemini, get_enhanced_genre_mapping
from lastfm_client import get_top_tracks_for_tag
from spotify_client import create_playlist_from_genres
import re

# Page config
st.set_page_config(
    page_title="Moodboard → Music",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean, minimal design
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 800px;
    }
    
    /* Clean typography */
    .main-title {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    /* Simple tag styling */
    .tag-chip {
        display: inline-block;
        background: #EEF2FF;
        color: #4F46E5;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-size: 0.9rem;
        font-weight: 500;
        border: 1px solid #E0E7FF;
    }
    
    /* Clean button styling */
    .stButton > button {
        background: #4F46E5;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: #4338CA;
        transform: translateY(-1px);
    }
    
    /* Success card */
    .success-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    /* Simple spacing */
    .section-spacing {
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 class="main-title">Moodboard → Music</h1>
    <p class="subtitle">Upload an image and get a personalized Spotify playlist that matches its vibe</p>
</div>
""", unsafe_allow_html=True)

# File upload
uploaded_file = st.file_uploader(
    "Choose an image",
    type=["jpg", "jpeg", "png"],
    help="Upload a JPEG or PNG image to analyze its aesthetic"
)

# Remove the annoying instruction text

if uploaded_file:
    # Save uploaded file
    with open("temp.jpg", "wb") as f:
        f.write(uploaded_file.read())

    # Show uploaded image
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("temp.jpg", caption="Your moodboard", width=300)

    # Analyze image with Gemini
    with st.spinner("🔮 Analyzing your image's aesthetic with AI..."):
        analysis_result = analyze_image_with_gemini("temp.jpg")
    
    if analysis_result['success']:
        analysis = analysis_result['analysis']
        
        # Display aesthetic tags
        st.markdown("### Detected Vibes")
        tags_html = ""
        for tag in analysis['aesthetic_tags'][:5]:
            tags_html += f'<span class="tag-chip">{tag.title()}</span>'
        st.markdown(tags_html, unsafe_allow_html=True)
        
        # Display mood descriptors
        st.markdown("### Mood")
        mood_html = ""
        for mood in analysis['mood_descriptors']:
            mood_html += f'<span class="tag-chip">{mood.title()}</span>'
        st.markdown(mood_html, unsafe_allow_html=True)
        
        # Show additional context in expandable section
        with st.expander("📋 Detailed Analysis"):
            st.write(f"**Time Period:** {analysis.get('time_period', 'Contemporary')}")
            st.write(f"**Cultural Context:** {analysis.get('cultural_context', 'Modern aesthetic')}")
            st.write(f"**Confidence:** {analysis.get('confidence', 0.8):.1%}")
            
            st.write("**Suggested Genres:**")
            for genre in analysis.get('music_genres', []):
                st.write(f"• {genre}")
        
        # Store analysis for playlist generation
        gemini_analysis = analysis
    else:
        # Fallback to basic analysis
        st.warning("⚠️ Gemini API not available. Using fallback analysis...")
        from gemini_analyzer import get_basic_fallback_analysis
        fallback_result = get_basic_fallback_analysis()
        analysis = fallback_result['analysis']
        
        # Display aesthetic tags
        st.markdown("### Detected Vibes")
        tags_html = ""
        for tag in analysis['aesthetic_tags'][:5]:
            tags_html += f'<span class="tag-chip">{tag.title()}</span>'
        st.markdown(tags_html, unsafe_allow_html=True)
        
        # Display mood descriptors
        st.markdown("### Mood")
        mood_html = ""
        for mood in analysis['mood_descriptors']:
            mood_html += f'<span class="tag-chip">{mood.title()}</span>'
        st.markdown(mood_html, unsafe_allow_html=True)
        
        # Show additional context
        with st.expander("📋 Analysis Details"):
            st.write(f"**Time Period:** {analysis.get('time_period', 'Contemporary')}")
            st.write(f"**Cultural Context:** {analysis.get('cultural_context', 'Modern aesthetic')}")
            st.write("**Note:** Using fallback analysis. Enable Gemini API for better results.")
            
            st.write("**Suggested Genres:**")
            for genre in analysis.get('music_genres', []):
                st.write(f"• {genre}")
        
        # Store analysis for playlist generation
        gemini_analysis = analysis

    # Generate playlist button
    st.markdown("### Create Your Playlist")
    
    if st.button("Generate Spotify Playlist") and gemini_analysis:
        with st.spinner("🎵 Crafting your perfect playlist..."):
            try:
                # Get enhanced genre mapping from Gemini
                enhanced_genres = get_enhanced_genre_mapping(
                    gemini_analysis['aesthetic_tags'],
                    gemini_analysis['mood_descriptors'], 
                    gemini_analysis['music_genres'],
                    gemini_analysis.get('time_period', 'Contemporary'),
                    gemini_analysis.get('cultural_context', 'Modern')
                )
                
                # Get tracks for each enhanced genre
                genre_tracks = {}
                for genre in enhanced_genres[:4]:  # Limit to 4 genres
                    tracks = get_top_tracks_for_tag(genre, limit=8)
                    if tracks:
                        genre_tracks[genre] = tracks
                
                if genre_tracks:
                    # Create the playlist
                    result = create_playlist_from_genres(genre_tracks, gemini_analysis)
                    
                    if result['success']:
                        # Extract playlist ID for embed
                        playlist_id = result['playlist_url'].split('/')[-1].split('?')[0]
                        
                        # Success message
                        st.success("🎉 Playlist created successfully!")
                        
                        st.markdown(f"""
                        <div class="success-card">
                            <h4>{result['playlist_name']}</h4>
                            <p>{result['track_count']} tracks added</p>
                            <a href="{result['playlist_url']}" target="_blank" style="color: #4F46E5; text-decoration: none; font-weight: 600;">
                                Open in Spotify →
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Spotify embed
                        st.markdown("### Listen Now")
                        spotify_embed = f"""
                        <iframe style="border-radius:8px" src="https://open.spotify.com/embed/playlist/{playlist_id}?utm_source=generator&theme=0" 
                        width="100%" height="352" frameBorder="0" allowfullscreen="" 
                        allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>
                        """
                        st.markdown(spotify_embed, unsafe_allow_html=True)
                        
                        # Track list in expandable section
                        with st.expander("View all tracks"):
                            for track in result['tracks_added']:
                                st.write(f"• {track}")
                                
                    else:
                        st.error(f"❌ Couldn't create playlist: {result['error']}")
                        if "authorization" in result['error'].lower():
                            st.info("💡 Please authorize the app in the browser tab that opens, then try again.")
                else:
                    st.warning("⚠️ No tracks found for your image's vibe. Try a different photo!")
                    
            except Exception as e:
                st.error(f"❌ Something went wrong: {str(e)}")
                st.info("💡 Please check your connection and try again.")

# Remove annoying footer


