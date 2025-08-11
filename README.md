# Moodboard-to-Music 

Moodboard-to-Music is an image-to-audio pipeline that generates Spotify playlists from uploaded images. It uses CLIP to extract aesthetic tags, maps them to Last.fm genres, and creates playlists that reflect the mood or vibe of the image.
 
## Goal

To explore the connection between an image and sound. This project bridges platforms that evoke emotion in different media (visual vs. auditory), and is part of my broader interest in creativity, AI, and cross-sensory product design.

## Features

- Accepts image uploads from local files  
- Uses CLIP to extract aesthetic tags from visuals  
- Maps tags to genres and moods using GPT-4 + Last.fm’s genre taxonomy  
- Queries Spotify to generate and preview a matching playlist  

## Stack

- CLIP (OpenAI) or Google Vision — image-to-tag extraction  
- GPT-4 / Claude — tag-to-genre translation  
- Last.fm API — genre-based music lookup  
- Spotify API — playlist creation and playback  
- Streamlit — lightweight interactive UI  
- Python — end-to-end logic and API orchestration  

## Status

Currently in development. The MVP accepts image uploads, extracts aesthetic tags, and generates Spotify playlists based on emotional tone. Refining tag mappings, playlist quality, and UI polish.

## About Me

Hi, I'm Shawdi — a creative technologist with a background in computer science, linguistics, and digital media. I enjoy building emotionally resonant tools and products that live between media, accessibility, and technology. This project is part of my exploration into AI, product management, and cross-platform creativity.

## Privacy Policy

This app does not store or share any uploaded images, Spotify account data, or personal information. All processing is local or API-based, and user data is discarded after session use.

If the app is deployed publicly, OAuth tokens are used only to authorize playlist creation via Spotify and are not logged or stored.

For questions, feel free to reach out.
