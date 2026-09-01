# 🎵 Vibe Vault — Modern Music Streaming & Library Web Application

> **"Your music. Your library. Your vibe."**

Vibe Vault is a full-stack, production-ready music streaming and playlist management application built with Flask, **MySQL (PyMySQL)**, and a clean **White & Blue Gradient Design System**. Users can upload high-resolution audio files, organize tracks into custom playlists, heart favorite songs, review listening timelines, and stream high-fidelity audio through an uninterrupted persistent HTML5 audio player.

---

## 🌟 Key Features

- 🔐 **Authentication & Security**:
  - Secure registration and login with Werkzeug PBKDF2:SHA256 password hashing.
  - Session-based authentication with "Remember Me" support.
  - Strict user data isolation (users can only access, view, and modify their own library).
  - File upload sanitization, format validation, and secure UUID filename generation.
- 🎵 **Music Upload & Management**:
  - Drag-and-drop audio uploading supporting **MP3, WAV, OGG, M4A** (up to 60MB).
  - Automatic duration detection via server-side `mutagen` and client-side HTML5 Audio API.
  - Custom song titles, artist, album, and genre tag metadata.
  - Custom album artwork preview and upload.
  - Search, filter by genre, and sort by recently added, title, artist, or most played.
- ⚡ **Persistent SPA Audio Player**:
  - Uninterrupted playback across all module transitions (`Dashboard`, `My Music`, `Playlists`, `Favorites`, `Recently Played`, `Profile`).
  - Fixed bottom audio player with glassmorphism backdrop.
  - Real-time seek bar scrubber, buffered progress, and duration indicators (`mm:ss`).
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
- 🎨 **White & Blue Gradient Design System**:
  - Polished interface using curated white and royal/deep blue gradients, glassmorphism cards, and fluid mobile drawer navigation.

---

## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3 (Vanilla CSS with White & Blue Gradient Glassmorphism), JavaScript (ES6+ SPA Router & AJAX), Bootstrap 5, Font Awesome 6
- **Backend**: Python 3.13, Flask 3.1, Werkzeug, PyMySQL, Mutagen, Gunicorn
- **Database**: MySQL 8.0 / MariaDB with automatic schema initialization (`database/schema.sql`)
- **Architecture**: RESTful JSON APIs, Jinja2 Template Engine, Decoupled Storage Adapter (Local / S3)

---

## 🚀 Production Deployment

### 1. Production Entrypoint & WSGI Server

Vibe Vault uses the standard WSGI application factory pattern. The application instance is instantiated at module level in `app.py`:

```python
app = create_app()
```

When deploying to production, point your WSGI server (such as Gunicorn) to `app:app`:

```bash
# Procfile command:
web: gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 120 app:app
```

### 2. Environment Variables Checklist

Set the following environment variables in your hosting provider's dashboard (e.g. Railway, Render, Fly.io, AWS, Heroku):

| Variable | Recommended Production Value | Description |
|---|---|---|
| `SECRET_KEY` | *(Generate 32-byte hex key)* | Flask session signing key. Generate via `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `mysql://user:pass@host:3306/vibe_vault` | Single connection URL for MySQL (used by Railway, Render, Heroku) |
| `DB_HOST` | `your-managed-db-host` | MySQL database host (fallback if DATABASE_URL not set) |
| `DB_PORT` | `3306` | MySQL database port |
| `DB_USER` | `your-db-username` | MySQL database username |
| `DB_PASSWORD` | `your-db-password` | MySQL database password |
| `DB_NAME` | `vibe_vault` | MySQL database name |
| `SESSION_COOKIE_SECURE` | `true` | Enforces HTTPS-only cookies in production |
| `PORT` | `5000` | Server binding port (auto-set by most PaaS hosts) |
| `FLASK_DEBUG` | `0` | Disables debug mode in production |
| `STORAGE_BACKEND` | `local` *(or `s3`)* | File storage adapter (`local` disk or `s3` bucket) |

---

## 🗄️ Database Configuration (MySQL)

Vibe Vault is designed to run seamlessly on managed MySQL databases:
- **Recommended Managed MySQL Providers**:
  - [Railway MySQL](https://railway.app)
  - [PlanetScale](https://planetscale.com)
  - [AWS RDS MySQL](https://aws.amazon.com/rds/mysql/)
  - [DigitalOcean Managed MySQL](https://www.digitalocean.com/products/managed-databases-mysql)
  - [Aiven for MySQL](https://aiven.io/mysql)

### Automatic Schema Initialization
When the application starts, `init_db()` automatically runs `database/schema.sql` against the database to create all tables and indexes idempotently without manual database intervention.

---

## 🐳 Deploy with Docker & Docker Compose

To run VibeVault and MySQL 8 together in containers:

```bash
docker compose up -d --build
```

Access the app at `http://localhost:5000`.

---

## 💾 File Storage (Local Disk vs S3)

User uploaded audio tracks (`uploads/songs/`), cover images (`uploads/covers/`), and profile avatars (`uploads/profiles/`) can be stored in two ways:

### Option A: Persistent Volumes (Default: `STORAGE_BACKEND=local`)
If hosting on a platform with persistent volume support, mount a persistent disk volume to the `/app/uploads` folder:
- **Supported Hosts**: Railway Volumes, Fly.io Volumes, Render Persistent Disks, Docker Volumes.
- **Note**: Ephemeral serverless platforms (e.g. Vercel, vanilla Heroku without volume plugins) reset local files on every deploy. Use Option B for ephemeral platforms.

### Option B: S3-Compatible Object Storage (`STORAGE_BACKEND=s3`)
Set `STORAGE_BACKEND=s3` and configure your S3 credentials (compatible with AWS S3, Cloudflare R2, Backblaze B2, MinIO):
```env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=your-bucket-name
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_REGION=us-east-1
```

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
Copy the template and fill in your values:
```bash
cp .env.example .env
```

### 5. Seed Demo Audio & Sample Tracks (Optional)
```bash
python seed_data.py
```

### 6. Run the Application Locally
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 🧪 Automated Testing

Run the automated test suite:
```bash
pytest tests/test_app.py
```

---

## 📜 License
This project is for personal music management and educational use.
