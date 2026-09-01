import os
from datetime import timedelta
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from .env file (no-op in production where vars
# are injected directly by the platform, e.g. Render, Railway, Heroku)
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    BASE_DIR = BASE_DIR

    # ----------------------------------------------------------------
    # SECURITY: Secret key must always come from the environment.
    # Generate with:  python -c "import secrets; print(secrets.token_hex(32))"
    # ----------------------------------------------------------------
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            "[VibeVault] SECRET_KEY is not set. "
            "Please add SECRET_KEY=<random-string> to your .env file "
            "or set it as an environment variable in your hosting platform."
        )

    # ----------------------------------------------------------------
    # Database — MySQL
    #
    # Production (Railway, Render, PlanetScale, AWS RDS, Heroku, etc.):
    #   Set DATABASE_URL or MYSQL_URL environment variable.
    #   Format: mysql://username:password@hostname:3306/dbname
    #
    # Local development:
    #   Set DATABASE_URL or the individual DB_* variables below.
    # ----------------------------------------------------------------
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('MYSQL_URL') or ''

    # Individual vars used by db.py when DATABASE_URL is absent
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_PORT     = int(os.getenv('DB_PORT', 3306))
    DB_USER     = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME     = os.getenv('DB_NAME', 'vibe_vault')

    # ----------------------------------------------------------------
    # File upload configuration
    # ----------------------------------------------------------------
    UPLOAD_FOLDER   = os.path.join(BASE_DIR, 'uploads')
    SONGS_FOLDER    = os.path.join(UPLOAD_FOLDER, 'songs')
    COVERS_FOLDER   = os.path.join(UPLOAD_FOLDER, 'covers')
    PROFILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')

    # 60 MB max upload size (accommodates high-quality audio)
    MAX_CONTENT_LENGTH = 60 * 1024 * 1024

    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

    # Valid MIME type prefixes (magic-byte validation via filetype lib)
    ALLOWED_AUDIO_MIMES = {'audio/', 'video/'}  # m4a reports as video/mp4
    ALLOWED_IMAGE_MIMES = {'image/'}

    # ----------------------------------------------------------------
    # Storage backend: 'local' (default) or 's3'
    #
    # IMPORTANT for ephemeral clouds (e.g. Render/Heroku without volumes):
    #   Files saved to 'uploads/' on ephemeral platforms are lost on restarts.
    #   For persistent music and image storage, set STORAGE_BACKEND=s3 and
    #   configure the S3_* variables below (Cloudflare R2 or AWS S3).
    # ----------------------------------------------------------------
    STORAGE_BACKEND      = os.getenv('STORAGE_BACKEND', 'local').lower()
    S3_BUCKET_NAME       = os.getenv('S3_BUCKET_NAME', '')
    S3_ENDPOINT_URL      = os.getenv('S3_ENDPOINT_URL', None)
    S3_ACCESS_KEY_ID     = os.getenv('S3_ACCESS_KEY_ID', '')
    S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY', '')
    S3_REGION            = os.getenv('S3_REGION', 'us-east-1')

    # ----------------------------------------------------------------
    # Session / security
    # ----------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Set to true in production (HTTPS only)
    SESSION_COOKIE_SECURE   = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    # 7-day Remember Me lifetime
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
