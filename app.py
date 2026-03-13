import streamlit as st
from gemini_analyzer import analyze_image_with_gemini, get_basic_fallback_analysis
from spotify_client import create_playlist_from_songs

# Page config
st.set_page_config(
    page_title="Moodboard → Music",
    page_icon="🎵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 800px;
    }

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

    .energy-chip {
        display: inline-block;
        background: #F0FDF4;
        color: #16A34A;
        padding: 0.4rem 0.9rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid #BBF7D0;
    }

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

    .success-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        text-align: center;
    }

    .vibe-box {
        background: #FAFAFA;
        border-left: 3px solid #4F46E5;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
        font-style: italic;
        color: #444;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 2.5rem; font-weight: 600; color: #1a1a1a; margin-bottom: 0.5rem;">
        Moodboard → Music
    </h1>
    <p style="font-size: 1.1rem; color: #666; margin-bottom: 2rem;">
        Upload an image and get a Spotify playlist that matches its vibe
    </p>
</div>
""", unsafe_allow_html=True)

# File upload
uploaded_file = st.file_uploader(
    "Choose an image",
    type=["jpg", "jpeg", "png"],
    help="Upload a JPEG or PNG image"
)

if uploaded_file:
    with open("temp.jpg", "wb") as f:
        f.write(uploaded_file.read())

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("temp.jpg", caption="Your moodboard", width=300)

    # Analyze image
    with st.spinner("Analyzing your image's vibe..."):
        result = analyze_image_with_gemini("temp.jpg")

    if result["success"]:
        analysis = result["analysis"]
    else:
        st.warning("⚠️ Gemini API unavailable — using fallback analysis.")
        analysis = get_basic_fallback_analysis()["analysis"]

    # Vibe summary
    if analysis.get("vibe_summary"):
        st.markdown(f'<div class="vibe-box">{analysis["vibe_summary"]}</div>', unsafe_allow_html=True)

    # Aesthetic tags
    st.markdown("### Detected Vibes")
    tags_html = "".join(
        f'<span class="tag-chip">{tag.title()}</span>'
        for tag in analysis.get("aesthetic_tags", [])
    )
    st.markdown(tags_html, unsafe_allow_html=True)

    # Mood + energy
    col_mood, col_energy = st.columns([3, 1])
    with col_mood:
        st.markdown("### Mood")
        mood_html = "".join(
            f'<span class="tag-chip">{m.title()}</span>'
            for m in analysis.get("mood_descriptors", [])
        )
        st.markdown(mood_html, unsafe_allow_html=True)
    with col_energy:
        st.markdown("### Energy")
        energy = analysis.get("energy_level", "medium").title()
        st.markdown(f'<span class="energy-chip">⚡ {energy}</span>', unsafe_allow_html=True)

    # Song preview
    songs = analysis.get("songs", [])
    if songs:
        with st.expander(f"🎵 {len(songs)} songs Gemini selected for this vibe"):
            for i, song in enumerate(songs, 1):
                st.write(f"{i}. **{song['title']}** — {song['artist']}")

    # Playlist generation
    st.markdown("### Create Your Playlist")

    if st.button("Generate Spotify Playlist") and songs:
        with st.spinner("Finding tracks on Spotify and building your playlist..."):
            result = create_playlist_from_songs(songs, analysis)

        if result["success"]:
            playlist_id = result["playlist_url"].split("/")[-1].split("?")[0]

            st.success("🎉 Playlist created!")

            st.markdown(f"""
            <div class="success-card">
                <h4>{result['playlist_name']}</h4>
                <p>{result['track_count']} tracks added</p>
                <a href="{result['playlist_url']}" target="_blank"
                   style="color: #4F46E5; text-decoration: none; font-weight: 600;">
                    Open in Spotify →
                </a>
            </div>
            """, unsafe_allow_html=True)

            # Spotify embed
            st.markdown("### Listen Now")
            st.markdown(f"""
            <iframe style="border-radius:8px"
                src="https://open.spotify.com/embed/playlist/{playlist_id}?utm_source=generator&theme=0"
                width="100%" height="352" frameBorder="0" allowfullscreen=""
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                loading="lazy">
            </iframe>
            """, unsafe_allow_html=True)

            # Track list
            with st.expander("View all tracks added"):
                for track in result["tracks_added"]:
                    st.write(f"✓ {track}")

            if result.get("tracks_not_found"):
                with st.expander(f"⚠️ {len(result['tracks_not_found'])} tracks not found on Spotify"):
                    for track in result["tracks_not_found"]:
                        st.write(f"✗ {track}")

        else:
            st.error(f"❌ Couldn't create playlist: {result['error']}")
            if "authorization" in result["error"].lower():
                st.info("💡 Authorize the app in the browser tab that opens, then try again.")
