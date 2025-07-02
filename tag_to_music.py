
tag_to_lastfm = {
    "dreamy": ["dream pop", "shoegaze"],
    "moody": ["indie rock", "alternative"],
    "sunset": ["chillwave", "ambient"],
    "vintage": ["classic rock", "retro"],
    "cozy": ["acoustic", "folk"],
    "bright": ["pop", "dance"],
    "grunge": ["grunge", "alternative rock"],
    "dark": ["darkwave", "industrial"],
    "romantic": ["r&b", "love songs"],
    "quiet": ["lo-fi", "instrumental"],
    "gloomy": ["slowcore", "doom metal"],
    "pastel": ["bedroom pop", "indie pop"],
    "aesthetic": ["vaporwave", "synthpop"],
    "soft": ["soft rock", "easy listening"],
    "punk": ["punk rock", "garage"],
    "boho": ["folk rock", "psychedelic"],
    "glam": ["glam rock", "electropop"],
    "urban": ["hip hop", "trap"],
    "futuristic": ["electronic", "synthwave"],
    "noir": ["jazz", "trip hop"],
    "cottagecore": ["folk", "chamber pop"],
    "retro": ["disco", "funk"],
    "summer": ["surf rock", "reggae"],
    "autumn": ["singer-songwriter", "indie folk"],
    "melancholy": ["sadcore", "piano"],
    "chaotic": ["experimental", "noise rock"],
    "ethereal": ["ethereal wave", "new age"],
    "colorful": ["pop rock", "electropop"],
    "monochrome": ["post-punk", "minimal"],
    "sparkly": ["bubblegum pop", "dance pop"],
    "industrial": ["industrial", "ebm"]
}

def map_clip_tag_to_lastfm(clip_tag):
    return tag_to_lastfm.get(clip_tag.lower(), [])
