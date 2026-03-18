'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Types ──────────────────────────────────────────────────────────────────────

type AppState = 'upload' | 'analyzing' | 'reveal';

interface Song {
  title: string;
  artist: string;
}

interface Analysis {
  vibe_summary: string;
  aesthetic_tags: string[];
  mood_descriptors: string[];
  energy_level: string;
  songs: Song[];
  fallback?: boolean;
}

interface PlaylistResult {
  playlist_url: string;
  playlist_name: string;
  embed_url: string;
  track_count: number;
  tracks_added: string[];
  tracks_not_found: string[];
}

// ── Dominant color extraction ──────────────────────────────────────────────────
// Draws the image on a small canvas, finds the pixel with the highest color
// saturation (skipping near-black and near-white), returns it as a hex string.

async function extractDominantColor(imageUrl: string): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const SIZE = 80;
      const canvas = document.createElement('canvas');
      canvas.width = SIZE;
      canvas.height = SIZE;
      const ctx = canvas.getContext('2d');
      if (!ctx) { resolve('#1a1a1a'); return; }

      ctx.drawImage(img, 0, 0, SIZE, SIZE);
      const { data } = ctx.getImageData(0, 0, SIZE, SIZE);

      let bestSat = 0;
      let bestR = 26, bestG = 26, bestB = 26;

      for (let i = 0; i < data.length; i += 4) {
        const r = data[i] / 255;
        const g = data[i + 1] / 255;
        const b = data[i + 2] / 255;
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const lightness = (max + min) / 2;
        if (lightness < 0.12 || lightness > 0.88) continue;
        const sat = max === min ? 0 : (max - min) / (1 - Math.abs(2 * lightness - 1));
        if (sat > bestSat) {
          bestSat = sat;
          bestR = Math.round(data[i]);
          bestG = Math.round(data[i + 1]);
          bestB = Math.round(data[i + 2]);
        }
      }

      const hex = (n: number) => n.toString(16).padStart(2, '0');
      resolve(`#${hex(bestR)}${hex(bestG)}${hex(bestB)}`);
    };
    img.onerror = () => resolve('#1a1a1a');
    img.src = imageUrl;
  });
}

// ── Constants ──────────────────────────────────────────────────────────────────

const ANALYZING_PHRASES = [
  'reading the vibe...',
  'feeling the energy...',
  'finding your songs...',
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

// ── Page ───────────────────────────────────────────────────────────────────────

export default function Home() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [playlist, setPlaylist] = useState<PlaylistResult | null>(null);
  const [dominantColor, setDominantColor] = useState('#1a1a1a');
  const [isDragging, setIsDragging] = useState(false);
  const [playlistLoading, setPlaylistLoading] = useState(false);
  const [playlistError, setPlaylistError] = useState<string | null>(null);
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [embedKey, setEmbedKey] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cycle analyzing phrases every 2 seconds
  useEffect(() => {
    if (appState !== 'analyzing') return;
    const id = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % ANALYZING_PHRASES.length);
    }, 2000);
    return () => clearInterval(id);
  }, [appState]);

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) return;

    const url = URL.createObjectURL(file);
    setImageUrl(url);
    setImageFile(file);
    setAppState('analyzing');
    setPhraseIndex(0);

    // Extract dominant color in parallel with the API call
    extractDominantColor(url).then(setDominantColor);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`API error ${res.status}`);

      const data: Analysis = await res.json();
      setAnalysis(data);
      setAppState('reveal');
    } catch (err) {
      console.error(err);
      setAppState('upload');
      alert(`Could not analyze the image. Attempted to connect to: ${API_BASE || 'Undefined API URL'}`);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleGeneratePlaylist = async () => {
    if (!analysis) return;
    setPlaylistLoading(true);
    setPlaylistError(null);

    try {
      // Convert image to base64 so the backend can set it as the playlist cover
      let image_b64: string | null = null;
      if (imageFile) {
        const buffer = await imageFile.arrayBuffer();
        const bytes = new Uint8Array(buffer);
        let binary = '';
        bytes.forEach((b) => (binary += String.fromCharCode(b)));
        image_b64 = btoa(binary);
      }

      const res = await fetch(`${API_BASE}/api/playlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ songs: analysis.songs, analysis, image_b64 }),
      });

      if (!res.ok) throw new Error(`API error ${res.status}`);

      const data: PlaylistResult = await res.json();
      setPlaylist(data);
      setEmbedKey((k) => k + 1);
    } catch {
      setPlaylistError('Could not create playlist. Make sure Spotify is authorized.');
    } finally {
      setPlaylistLoading(false);
    }
  };

  const handleReset = () => {
    setAppState('upload');
    setImageUrl(null);
    setImageFile(null);
    setAnalysis(null);
    setPlaylist(null);
    setPlaylistError(null);
    setDominantColor('#1a1a1a');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <main className="min-h-screen bg-black text-white overflow-x-hidden">
      <AnimatePresence mode="wait">

        {/* ── UPLOAD ─────────────────────────────────────────────────────────── */}
        {appState === 'upload' && (
          <motion.div
            key="upload"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4 }}
            className="min-h-screen flex items-center justify-center px-6"
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.6, ease: 'easeOut' }}
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onClick={() => fileInputRef.current?.click()}
              className={`
                w-full max-w-sm aspect-square rounded-2xl border-2 border-dashed
                flex flex-col items-center justify-center gap-3 cursor-pointer
                transition-all duration-300 select-none
                ${isDragging
                  ? 'border-white/50 bg-white/10 scale-[1.02]'
                  : 'border-white/10 bg-white/[0.02] hover:border-white/25 hover:bg-white/[0.05]'
                }
              `}
            >
              <p className="text-white/35 text-sm text-center leading-loose tracking-wide">
                drop an image.<br />get a playlist.
              </p>
              <p className="text-white/15 text-xs tracking-widest">jpg · png</p>
            </motion.div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleFile(f);
              }}
            />
          </motion.div>
        )}

        {/* ── ANALYZING ──────────────────────────────────────────────────────── */}
        {appState === 'analyzing' && imageUrl && (
          <motion.div
            key="analyzing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="min-h-screen relative flex items-center justify-center"
          >
            {/* Full-screen blurred image */}
            <div
              className="absolute inset-0 scale-110"
              style={{
                backgroundImage: `url(${imageUrl})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                filter: 'blur(50px) brightness(0.3) saturate(1.5)',
              }}
            />
            <div className="absolute inset-0 bg-black/55" />

            {/* Cycling phrase — each fades in and out */}
            <div className="relative z-10 text-center">
              <AnimatePresence mode="wait">
                <motion.p
                  key={phraseIndex}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.45 }}
                  className="text-base font-light tracking-[0.3em] text-white/65"
                >
                  {ANALYZING_PHRASES[phraseIndex]}
                </motion.p>
              </AnimatePresence>
            </div>
          </motion.div>
        )}

        {/* ── REVEAL ─────────────────────────────────────────────────────────── */}
        {appState === 'reveal' && analysis && (
          <motion.div
            key="reveal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.7 }}
            className="min-h-screen relative"
            style={{
              background: `radial-gradient(ellipse at 50% 0%, ${dominantColor}45 0%, #000 55%)`,
            }}
          >
            <div className="relative z-10 max-w-xl mx-auto px-6 py-14">

              {/* Back */}
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                onClick={handleReset}
                className="text-white/20 text-xs tracking-widest uppercase hover:text-white/45 transition-colors mb-10"
              >
                ← new image
              </motion.button>

              {/* Thumbnail */}
              {imageUrl && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.25, duration: 0.5, ease: 'easeOut' }}
                  className="mb-8"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imageUrl}
                    alt="uploaded moodboard"
                    className="w-20 h-20 object-cover rounded-xl"
                    style={{ boxShadow: `0 8px 32px ${dominantColor}55` }}
                  />
                </motion.div>
              )}

              {/* Vibe summary */}
              <motion.p
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35, duration: 0.6 }}
                className="text-white/65 text-base font-light leading-relaxed italic mb-8"
              >
                {analysis.vibe_summary}
              </motion.p>

              {/* Aesthetic tags */}
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45, duration: 0.5 }}
                className="flex flex-wrap gap-2 mb-8"
              >
                {analysis.aesthetic_tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-3 py-1 rounded-full text-xs tracking-widest uppercase text-white/55 border"
                    style={{
                      borderColor: `${dominantColor}65`,
                      background: `${dominantColor}15`,
                    }}
                  >
                    {tag}
                  </span>
                ))}
              </motion.div>

              {/* Energy bar */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.55 }}
                className="mb-10"
              >
                <p className="text-white/25 text-xs tracking-widest uppercase mb-2">
                  energy · {analysis.energy_level}
                </p>
                <div className="h-px w-full bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width:
                        analysis.energy_level === 'high'
                          ? '100%'
                          : analysis.energy_level === 'medium'
                          ? '60%'
                          : '28%',
                    }}
                    transition={{ delay: 0.7, duration: 0.9, ease: 'easeOut' }}
                    className="h-full rounded-full"
                    style={{ background: dominantColor }}
                  />
                </div>
              </motion.div>

              {/* Song cards — stagger in with 0.08s between each */}
              <motion.div
                variants={{
                  hidden: {},
                  visible: {
                    transition: { staggerChildren: 0.08, delayChildren: 0.65 },
                  },
                }}
                initial="hidden"
                animate="visible"
                className="space-y-1.5 mb-10"
              >
                {analysis.songs.map((song, i) => (
                  <motion.div
                    key={`${song.title}-${i}`}
                    variants={{
                      hidden: { opacity: 0, x: -14 },
                      visible: {
                        opacity: 1,
                        x: 0,
                        transition: { duration: 0.35, ease: 'easeOut' },
                      },
                    }}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:bg-white/[0.07] transition-colors"
                  >
                    <span className="text-white/20 text-xs w-5 text-right shrink-0 tabular-nums">
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="text-white/80 text-sm font-medium truncate">{song.title}</p>
                      <p className="text-white/30 text-xs truncate">{song.artist}</p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              {/* Generate playlist button */}
              {!playlist && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 2.8, duration: 0.5 }}
                >
                  <button
                    onClick={handleGeneratePlaylist}
                    disabled={playlistLoading}
                    className="w-full py-4 rounded-2xl text-sm font-medium tracking-widest uppercase transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{
                      background: `linear-gradient(135deg, ${dominantColor}dd, ${dominantColor}88)`,
                      color: 'white',
                    }}
                  >
                    {playlistLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          className="inline-block"
                        >
                          ↻
                        </motion.span>
                        building your playlist
                      </span>
                    ) : (
                      'generate spotify playlist'
                    )}
                  </button>

                  {playlistError && (
                    <p className="text-red-400/60 text-xs text-center mt-3">{playlistError}</p>
                  )}
                </motion.div>
              )}

              {/* Playlist result */}
              {playlist && (
                <motion.div
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6 }}
                >
                  {/* Links row */}
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-white/25 text-xs tracking-widest uppercase">
                      {playlist.track_count} tracks
                    </p>
                    <div className="flex items-center gap-4">
                      <button
                        onClick={() => setEmbedKey((k) => k + 1)}
                        className="text-white/25 text-xs tracking-widest uppercase hover:text-white/50 transition-colors"
                      >
                        ↺ reload
                      </button>
                      <a
                        href={`spotify:playlist:${playlist.playlist_url.split('/').pop()}`}
                        className="text-xs tracking-widest uppercase hover:opacity-70 transition-opacity"
                        style={{ color: dominantColor }}
                      >
                        open in spotify →
                      </a>
                    </div>
                  </div>

                  {/* Spotify embed */}
                  <iframe
                    key={embedKey}
                    src={playlist.embed_url}
                    width="100%"
                    height="352"
                    frameBorder="0"
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                    loading="lazy"
                    className="rounded-2xl"
                  />

                  <p className="text-white/15 text-xs text-center mt-2">
                    if the embed shows &quot;not found&quot;, wait 30s and hit reload ↑
                  </p>

                  {playlist.tracks_not_found.length > 0 && (
                    <p className="text-white/20 text-xs text-center mt-2">
                      {playlist.tracks_not_found.length} songs couldn&apos;t be found on Spotify
                    </p>
                  )}
                </motion.div>
              )}

            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </main>
  );
}
