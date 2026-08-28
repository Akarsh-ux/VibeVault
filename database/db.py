import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
from config import Config

# ---------------------------------------------------------------------------
# Connection Helpers
# ---------------------------------------------------------------------------

def get_mysql_connection(create_db_if_missing=True):
    """Attempt to establish a MySQL connection using configured credentials."""
    try:
        if create_db_if_missing:
            conn = pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=3
            )
            with conn.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
            conn.select_db(Config.DB_NAME)
            return conn
        else:
            return pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=DictCursor,
                connect_timeout=3
            )
    except Exception:
        return None


def get_sqlite_connection():
    """SQLite connection for explicit dev/test mode (USE_SQLITE=true)."""
    sqlite_path = os.path.join(Config.BASE_DIR, 'database', 'vibe_vault.db')
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _get_connection():
    """
    Get a database connection.
    - If USE_SQLITE is explicitly true, use SQLite.
    - Otherwise use MySQL. Raises RuntimeError if MySQL is unavailable.
    """
    if Config.USE_SQLITE:
        return get_sqlite_connection(), False

    conn = get_mysql_connection(create_db_if_missing=False)
    if conn:
        return conn, True

    raise RuntimeError(
        "[VibeVault DB] Cannot connect to MySQL. "
        "Check your .env credentials or set USE_SQLITE=true for local testing."
    )


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def query_db(query, args=(), one=False, commit=False):
    """
    Execute a database query with automatic parameter handling.
    Works across MySQL (PyMySQL) and SQLite (when USE_SQLITE=true).

    Returns:
      - If commit=True: lastrowid or affected rowcount
      - If one=True: single row dict or None
      - Otherwise: list of row dicts
    """
    conn, is_mysql = _get_connection()

    try:
        if is_mysql:
            with conn.cursor() as cursor:
                cursor.execute(query, args)
                if commit:
                    conn.commit()
                    return cursor.lastrowid or cursor.rowcount
                result = cursor.fetchall()
                if one:
                    return result[0] if result else None
                return result
        else:
            # SQLite uses ? placeholders instead of %s
            sqlite_query = query.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(sqlite_query, args)
            if commit:
                conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                cursor.close()
                conn.close()
                return last_id or row_count

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            dict_rows = [dict(row) for row in rows]
            if one:
                return dict_rows[0] if dict_rows else None
            return dict_rows
    finally:
        if is_mysql and conn:
            conn.close()


# ---------------------------------------------------------------------------
# Schema Initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Initialize the database schema on MySQL or SQLite."""
    print("[VibeVault DB] Initializing database...")

    if Config.USE_SQLITE:
        _init_sqlite()
        return 'sqlite'

    mysql_conn = get_mysql_connection(create_db_if_missing=True)
    if mysql_conn:
        _init_mysql(mysql_conn)
        return 'mysql'

    raise RuntimeError(
        "[VibeVault DB] MySQL not reachable and USE_SQLITE is not set to true. "
        "Set USE_SQLITE=true in .env for local SQLite testing."
    )


def _init_mysql(mysql_conn):
    schema_path = os.path.join(Config.BASE_DIR, 'database', 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_script = f.read()

    statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
    with mysql_conn.cursor() as cursor:
        for stmt in statements:
            if stmt.upper().startswith(('CREATE DATABASE', 'USE')):
                continue
            try:
                cursor.execute(stmt)
            except Exception as err:
                # Ignore "already exists" type errors during idempotent init
                print(f"[MySQL Init Warning]: {err}")
    mysql_conn.commit()
    mysql_conn.close()
    print("[VibeVault DB] Connected and initialized MySQL database: 'vibe_vault' successfully!")


def _init_sqlite():
    print("[VibeVault DB] SQLite mode enabled (USE_SQLITE=true). Initializing local DB...")
    conn = get_sqlite_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        profile_image TEXT DEFAULT 'default_avatar.png',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        artist TEXT DEFAULT 'Unknown Artist',
        album TEXT DEFAULT 'Single',
        genre TEXT DEFAULT 'Various',
        audio_file TEXT NOT NULL,
        cover_image TEXT DEFAULT 'default_cover.png',
        duration INTEGER DEFAULT 0,
        upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        play_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        cover_image TEXT DEFAULT 'default_playlist.png',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS playlist_songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL,
        song_id INTEGER NOT NULL,
        position INTEGER DEFAULT 0,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
        UNIQUE(playlist_id, song_id)
    );

    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        song_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
        UNIQUE(user_id, song_id)
    );

    CREATE TABLE IF NOT EXISTS recently_played (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        song_id INTEGER NOT NULL,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()
    print("[VibeVault DB] SQLite database initialized successfully!")

