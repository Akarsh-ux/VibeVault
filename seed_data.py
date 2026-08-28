import os
import math
import struct
import wave
from werkzeug.security import generate_password_hash
from database.db import init_db, query_db
from config import Config
from generate_assets import create_gradient_cover

def generate_melodic_wave(filepath, duration_sec=12, base_freq=220.0, melody_notes=[0, 4, 7, 11, 7, 4]):
    """Generate a high quality synthetic ambient melodic audio file using standard library wave module."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)
    
    with wave.open(filepath, 'w') as wav_file:
        wav_file.setnchannels(2) # Stereo
        wav_file.setsampwidth(2) # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        note_duration = duration_sec / len(melody_notes)
        
        for i in range(n_samples):
            t = i / sample_rate
            note_idx = int(t / note_duration) % len(melody_notes)
            semitone = melody_notes[note_idx]
            freq = base_freq * (2 ** (semitone / 12.0))
            
            # Envelope (fade in/out per note)
            local_t = t % note_duration
            env = math.sin(math.pi * (local_t / note_duration))
            
            # Harmonic synthesis (Fundamental + 2nd + 3rd harmonics + warm chorus)
            s1 = math.sin(2 * math.pi * freq * t)
            s2 = 0.5 * math.sin(2 * math.pi * freq * 2 * t)
            s3 = 0.25 * math.sin(2 * math.pi * (freq * 1.5) * t)
            
            # LFO modulation
            lfo = 0.7 + 0.3 * math.sin(2 * math.pi * 0.5 * t)
            
            val = int((s1 + s2 + s3) * env * lfo * 14000)
            val = max(-32767, min(32767, val))
            
            # Left & Right channel with slight stereo pan phase
            val_l = int(val * (0.8 + 0.2 * math.sin(t * 2)))
            val_r = int(val * (0.8 - 0.2 * math.sin(t * 2)))
            
            frames.extend(struct.pack('<hh', max(-32767, min(32767, val_l)), max(-32767, min(32767, val_r))))
            
        wav_file.writeframes(frames)
    print(f"Generated demo audio track: {filepath}")

def seed():
    print("[VibeVault Seeder] Initializing database...")
    init_db()
    
    # 1. Create or get Demo User
    demo_user = query_db("SELECT id FROM users WHERE username = %s", ('demo_user',), one=True)
    if not demo_user:
        pwd_hash = generate_password_hash('password123', method='pbkdf2:sha256')
        user_id = query_db(
            "INSERT INTO users (full_name, username, email, password_hash, profile_image) VALUES (%s, %s, %s, %s, %s)",
            ('Demo Vibe Master', 'demo_user', 'demo@vibevault.io', pwd_hash, 'default_avatar.png'),
            commit=True
        )
        print(f"[VibeVault Seeder] Created demo user (id={user_id}, username='demo_user', password='password123')")
    else:
        user_id = demo_user['id']
        print(f"[VibeVault Seeder] Found existing demo user (id={user_id})")

    # 2. Sample Songs Metadata
    sample_tracks = [
        {
            'title': 'Midnight Neon Drive',
            'artist': 'Cyber Syndicate',
            'album': 'Retrowave Horizon',
            'genre': 'Synthwave',
            'duration': 14,
            'base_freq': 220.0,
            'melody': [0, 3, 7, 10, 7, 3, 0],
            'color1': (138, 43, 226),
            'color2': (0, 242, 254),
            'file_prefix': 'midnight_neon'
        },
        {
            'title': 'Cosmic Chill Lounge',
            'artist': 'Aura Soundscapes',
            'album': 'Deep Space Coffee',
            'genre': 'Lo-Fi Chill',
            'duration': 12,
            'base_freq': 174.61,
            'melody': [0, 4, 7, 9, 11, 7],
            'color1': (18, 53, 91),
            'color2': (72, 202, 228),
            'file_prefix': 'cosmic_chill'
        },
        {
            'title': 'Electric Pulse Symphony',
            'artist': 'Hyperion Beats',
            'album': 'Quantum Resonance',
            'genre': 'Electronic',
            'duration': 15,
            'base_freq': 261.63,
            'melody': [0, 2, 4, 7, 9, 12, 9, 7],
            'color1': (255, 0, 127),
            'color2': (138, 43, 226),
            'file_prefix': 'electric_pulse'
        },
        {
            'title': 'Golden Hour Groove',
            'artist': 'Solaris Trio',
            'album': 'Sunset Sessions',
            'genre': 'Nu-Disco',
            'duration': 10,
            'base_freq': 196.00,
            'melody': [0, 4, 7, 11, 14, 11, 7],
            'color1': (247, 127, 0),
            'color2': (214, 40, 40),
            'file_prefix': 'golden_hour'
        }
    ]

    os.makedirs(Config.SONGS_FOLDER, exist_ok=True)
    os.makedirs(Config.COVERS_FOLDER, exist_ok=True)

    song_ids = []
    for track in sample_tracks:
        audio_filename = f"demo_{track['file_prefix']}.wav"
        audio_path = os.path.join(Config.SONGS_FOLDER, audio_filename)
        
        # Generate wave if not exists
        if not os.path.exists(audio_path):
            generate_melodic_wave(
                audio_path,
                duration_sec=track['duration'],
                base_freq=track['base_freq'],
                melody_notes=track['melody']
            )

        # Generate custom cover
        cover_filename = f"cover_{track['file_prefix']}.png"
        cover_path = os.path.join(Config.COVERS_FOLDER, cover_filename)
        if not os.path.exists(cover_path):
            create_gradient_cover(cover_path, track['title'], track['artist'], track['color1'], track['color2'])

        # Check DB
        existing_song = query_db(
            "SELECT id FROM songs WHERE user_id = %s AND title = %s",
            (user_id, track['title']),
            one=True
        )
        if not existing_song:
            s_id = query_db(
                """INSERT INTO songs (user_id, title, artist, album, genre, audio_file, cover_image, duration, play_count)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, track['title'], track['artist'], track['album'], track['genre'], audio_filename, cover_filename, track['duration'], 5),
                commit=True
            )
            song_ids.append(s_id)
        else:
            song_ids.append(existing_song['id'])

    # 3. Create Sample Playlists
    pl1 = query_db("SELECT id FROM playlists WHERE user_id = %s AND name = %s", (user_id, 'Late Night Vibes'), one=True)
    if not pl1:
        pl1_id = query_db(
            "INSERT INTO playlists (user_id, name, description, cover_image) VALUES (%s, %s, %s, %s)",
            (user_id, 'Late Night Vibes', 'Smooth synth and ambient frequencies for nighttime focus.', 'default_playlist.png'),
            commit=True
        )
        for idx, sid in enumerate(song_ids):
            query_db("INSERT INTO playlist_songs (playlist_id, song_id, position) VALUES (%s, %s, %s)", (pl1_id, sid, idx+1), commit=True)
        print(f"[VibeVault Seeder] Created playlist 'Late Night Vibes' with {len(song_ids)} songs")

    # 4. Add Favorites & Recent Plays
    if song_ids:
        # Favorite first two songs
        for sid in song_ids[:2]:
            fav = query_db("SELECT id FROM favorites WHERE user_id = %s AND song_id = %s", (user_id, sid), one=True)
            if not fav:
                query_db("INSERT INTO favorites (user_id, song_id) VALUES (%s, %s)", (user_id, sid), commit=True)

        # Record recent plays
        for sid in song_ids:
            rp = query_db("SELECT id FROM recently_played WHERE user_id = %s AND song_id = %s", (user_id, sid), one=True)
            if not rp:
                query_db("INSERT INTO recently_played (user_id, song_id) VALUES (%s, %s)", (user_id, sid), commit=True)

    print("[VibeVault Seeder] Sample data seeding completed successfully!")

if __name__ == '__main__':
    seed()
