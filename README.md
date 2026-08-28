# 🎵 Vibe Vault — Personal Music Library Web Application

> **"Your music. Your library. Your vibe."**

Vibe Vault is a modern, responsive full-stack web application designed for personal music library and playlist management. Users can securely upload their audio files, organize tracks into custom playlists, heart their favorite songs, review listening history, and stream high-fidelity audio through an advanced persistent bottom audio player.

---

## 🌟 Key Features

- 🔐 **Authentication & Security**:
  - Secure registration and login with Werkzeug PBKDF2:SHA256 password hashing.
  - Session-based authentication with "Remember Me" support.
  - Strict user data isolation (users can only access, view, and modify their own library).
  - File upload sanitization, format checks, and secure UUID filename generation.
- 🎵 **Music Upload & Management**:
  - Drag-and-drop audio uploading supporting **MP3, WAV, OGG, M4A** (up to 60MB).
  - Automatic duration detection via server-side `mutagen` and client-side HTML5 Audio API.
  - Custom song titles, artist, album, and genre tag metadata.
  - Custom album artwork preview and upload.
  - Search, filter by genre, and sort by recently added, title, artist, or most played.
- ⚡ **Persistent HTML5 Audio Player**:
  - Fixed bottom audio player with frosted glass backdrop.
  - Real-time seek bar scrubber, buffered progress, and current/total duration indicators (`mm:ss`).
  - Shuffle, Repeat (Off, Repeat All, Repeat One), and Volume/Mute controls.
  - Animated soundwave equalizer for active playing tracks.
  - Auto-play logging: automatically increments play count and logs history after 5 seconds of active playback.
  - MediaSession API integration for OS/keyboard media controls.
- 🎧 **Dynamic Playlist Management**:
  - Create, edit, and delete custom playlists with descriptions and cover art.
  - Add songs to playlists with instant duplicate prevention.
  - Reorder playlist songs (move up/down) and full playlist playback (Play All / Shuffle Play).
- ❤️ **Favorites & History**:
  - Single-click heart toggle on any track card or row.
  - Dedicated Favorites library and Recently Played history with relative timestamps.
- 🔍 **Dynamic Global Search**:
  - Real-time autocomplete search across songs, artists, albums, genres, and playlists.
- 🎨 **White & Red Gradient Aesthetic**:
  - Modern, responsive dark studio theme with vibrant white-to-red gradients, glassmorphism cards, and fluid mobile drawer navigation.

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3 (Vanilla CSS with White & Red Gradient Glassmorphism), JavaScript (ES6+ AJAX/Fetch), Bootstrap 5, Font Awesome 6
- **Backend**: Python 3.13, Flask 3.1, Werkzeug, PyMySQL, Mutagen
- **Database**: MySQL (`vibe_vault`) with automatic schema setup & SQLite fallback support
- **Architecture**: RESTful JSON APIs & Jinja2 Template Engine

---

## 📂 Project Structure

```
VibeVault/
│
├── app.py                     # Flask application entrypoint & error handlers
├── config.py                  # Environment config and upload parameters
├── requirements.txt           # Python package dependencies
├── .env                       # Database credentials and secret key
├── .env.example               # Template environment configuration
├── .gitignore                 # Git ignore configuration
├── seed_data.py               # Demo audio generator & seed script
├── generate_assets.py         # SVG & PNG asset generator
│
├── database/
│   ├── schema.sql             # MySQL schema definitions
│   └── db.py                  # Database connection abstraction & query helpers
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                # Auth routes & REST APIs (/login, /register, /logout)
│   ├── main.py                # Landing page & dashboard with dynamic statistics
│   ├── songs.py               # Song upload, list, edit, delete, and REST APIs
│   ├── playlists.py           # Playlist CRUD, track reorder, and REST APIs
│   ├── favorites.py           # Favorite toggle and collection APIs
│   ├── recently_played.py     # Play history and play count tracking APIs
│   ├── search.py              # Global search endpoint across all models
│   └── users.py               # User profile info, avatar update, password reset
│
├── templates/
│   ├── base.html              # Core layout (sidebar, header, bottom player, modals)
│   ├── index.html             # Landing page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── dashboard.html         # User dashboard with stats & quick play
│   ├── music.html             # My Music library with live search & filters
│   ├── upload.html            # Audio upload form with live metadata preview
│   ├── playlists.html         # Playlists grid overview
│   ├── playlist.html          # Single playlist detail & track reordering
│   ├── favorites.html         # Favorites collection
│   ├── recently_played.html   # Listening timeline & play history
│   └── profile.html           # User profile & account security
│
├── static/
│   ├── css/
│   │   └── style.css          # White & Red gradient glassmorphic stylesheet
│   ├── js/
│   │   ├── app.js             # Core UI, toasts, global search, and modals
│   │   ├── player.js          # Persistent HTML5 audio player engine
│   │   ├── songs.js           # Song management, filtering, and duration detection
│   │   └── playlists.js       # Playlist management & reordering
│   └── images/
│       ├── logo.svg           # Vibe Vault glowing brand logo
│       ├── default_cover.png  # Default song cover art
│       ├── default_playlist.png # Default playlist cover art
│       └── default_avatar.png # Default profile picture
│
├── uploads/
│   ├── songs/                 # User audio files (.mp3, .wav, .ogg, .m4a)
│   ├── covers/                # Custom song & playlist covers
│   └── profiles/              # User profile pictures
│
└── tests/
    ├── __init__.py
    └── test_app.py            # Automated test suite (9 test cases)
```

---

## 🗄️ Database Schema & Setup

### Database Tables:
1. **`users`**: `id`, `full_name`, `username`, `email`, `password_hash`, `profile_image`, `created_at`
2. **`songs`**: `id`, `user_id`, `title`, `artist`, `album`, `genre`, `audio_file`, `cover_image`, `duration`, `upload_date`, `play_count`
3. **`playlists`**: `id`, `user_id`, `name`, `description`, `cover_image`, `created_at`
4. **`playlist_songs`**: `id`, `playlist_id`, `song_id`, `position`, `added_at` (Unique: `[playlist_id, song_id]`)
5. **`favorites`**: `id`, `user_id`, `song_id`, `created_at` (Unique: `[user_id, song_id]`)
6. **`recently_played`**: `id`, `user_id`, `song_id`, `played_at`

---

## ⚙️ Installation & Running Locally

### 1. Clone the repository and navigate into directory
```bash
cd VibeVault
```

### 2. Create and activate a Python virtual environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Create or edit `.env` in the root directory:
```env
SECRET_KEY=9535170711
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=AkarshSanjay2007
DB_NAME=vibe_vault
FLASK_ENV=development
FLASK_DEBUG=1
```

### 5. Seed Demo Audio & Sample Tracks (Optional)
```bash
python seed_data.py
```
*Creates sample synthesized melodic tracks, cover artwork, and sets up `demo_user` with password `password123`.*

### 6. Run the Application
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 🧪 Automated Testing

Run the automated test suite covering authentication, file uploads, playlist reordering, duplicate prevention, and user isolation:

```bash
python tests/test_app.py
```

---

## 🌐 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/register` | Register new user account |
| `POST` | `/api/login` | Authenticate user & start session |
| `POST` | `/api/logout` | End session |
| `GET` | `/api/songs` | List user songs (supports `?q=`, `?genre=`, `?sort=`) |
| `POST` | `/api/songs` | Upload new audio track with metadata |
| `GET` | `/api/songs/<id>` | Get single song details |
| `PUT` | `/api/songs/<id>` | Update song title, artist, album, genre, cover |
| `DELETE` | `/api/songs/<id>` | Delete song and audio file from storage |
| `GET` | `/api/playlists` | List user playlists with song counts |
| `POST` | `/api/playlists` | Create new playlist |
| `GET` | `/api/playlists/<id>` | Get playlist details and ordered track list |
| `PUT` | `/api/playlists/<id>` | Update playlist name and description |
| `DELETE` | `/api/playlists/<id>` | Delete playlist |
| `POST` | `/api/playlists/<id>/songs` | Add song to playlist (duplicate protected) |
| `DELETE` | `/api/playlists/<id>/songs/<song_id>` | Remove song from playlist |
| `PUT` | `/api/playlists/<id>/reorder` | Update song order positions |
| `GET` | `/api/favorites` | List all favorited songs |
| `POST` | `/api/favorites/toggle/<song_id>` | Toggle song favorite status |
| `GET` | `/api/recently-played` | Get listening history |
| `POST` | `/api/recently-played` | Log song playback & increment play count |
| `GET` | `/api/search?q=<query>` | Global search across all models |
| `GET` | `/api/profile` | Get profile information and listening stats |
| `POST` | `/api/profile` | Update full name, username, or avatar |
| `POST` | `/api/profile/password` | Change password with current password verification |

---

## 📜 License
This project is for personal music management and educational use.
