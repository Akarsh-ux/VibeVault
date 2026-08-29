import os
from datetime import timedelta
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR

    # SECURITY: Secret key must be set in .env — no hardcoded fallback in production
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            "[VibeVault] SECRET_KEY is not set. "
            "Please add SECRET_KEY=<random-string> to your .env file."
        )

    # Database configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'vibe_vault')

    # Allow SQLite only when explicitly enabled (for testing/dev without MySQL)
    USE_SQLITE = os.getenv('USE_SQLITE', 'false').lower() == 'true'

    # File upload configurations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    SONGS_FOLDER = os.path.join(UPLOAD_FOLDER, 'songs')
    COVERS_FOLDER = os.path.join(UPLOAD_FOLDER, 'covers')
    PROFILES_FOLDER = os.path.join(UPLOAD_FOLDER, 'profiles')

    # 60 MB Max upload size (accommodates high-res audio files)
    MAX_CONTENT_LENGTH = 60 * 1024 * 1024

    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

    # Valid MIME type prefixes for audio and image files (magic-byte validation)
    ALLOWED_AUDIO_MIMES = {'audio/', 'video/'}  # m4a reports as video/mp4 in some libs
    ALLOWED_IMAGE_MIMES = {'image/'}

    # Storage Backend Configuration: 'local' (default) or 's3'
    STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'local').lower()
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', '')
    S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL', None)
    S3_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID', '')
    S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY', '')
    S3_REGION = os.getenv('S3_REGION', 'us-east-1')


    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Set to True only when serving over HTTPS (production)
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    # 7-day Remember Me lifetime (Flask requires timedelta, not integer seconds)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

