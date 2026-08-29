-- ============================================================
-- Vibe Vault Database Schema (PostgreSQL)
-- Personal Music Library & Playlist Management
-- ============================================================
-- Safe to run multiple times: all statements use IF NOT EXISTS.
-- ============================================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id               SERIAL PRIMARY KEY,
    full_name        VARCHAR(100)  NOT NULL,
    username         VARCHAR(50)   NOT NULL UNIQUE,
    email            VARCHAR(120)  NOT NULL UNIQUE,
    password_hash    VARCHAR(255)  NOT NULL,
    profile_image    VARCHAR(255)  DEFAULT 'default_avatar.png',
    created_at       TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);

-- 2. Songs Table
CREATE TABLE IF NOT EXISTS songs (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title        VARCHAR(200) NOT NULL,
    artist       VARCHAR(150) DEFAULT 'Unknown Artist',
    album        VARCHAR(150) DEFAULT 'Single',
    genre        VARCHAR(50)  DEFAULT 'Various',
    audio_file   VARCHAR(255) NOT NULL,
    cover_image  VARCHAR(255) DEFAULT 'default_cover.png',
    duration     INTEGER      DEFAULT 0,
    upload_date  TIMESTAMPTZ  DEFAULT NOW(),
    play_count   INTEGER      DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_songs_user   ON songs (user_id);
CREATE INDEX IF NOT EXISTS idx_songs_title  ON songs (title);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs (artist);
CREATE INDEX IF NOT EXISTS idx_songs_genre  ON songs (genre);

-- 3. Playlists Table
CREATE TABLE IF NOT EXISTS playlists (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name         VARCHAR(100) NOT NULL,
    description  TEXT,
    cover_image  VARCHAR(255) DEFAULT 'default_playlist.png',
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_playlists_user ON playlists (user_id);

-- 4. Playlist Songs (Many-to-Many with Order Position)
CREATE TABLE IF NOT EXISTS playlist_songs (
    id           SERIAL PRIMARY KEY,
    playlist_id  INTEGER NOT NULL REFERENCES playlists (id) ON DELETE CASCADE,
    song_id      INTEGER NOT NULL REFERENCES songs (id)     ON DELETE CASCADE,
    position     INTEGER DEFAULT 0,
    added_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (playlist_id, song_id)
);

CREATE INDEX IF NOT EXISTS idx_playlist_songs_playlist ON playlist_songs (playlist_id);
CREATE INDEX IF NOT EXISTS idx_playlist_songs_position ON playlist_songs (playlist_id, position);

-- 5. Favorites Table
CREATE TABLE IF NOT EXISTS favorites (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    song_id     INTEGER NOT NULL REFERENCES songs (id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, song_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites (user_id);

-- 6. Recently Played Table
CREATE TABLE IF NOT EXISTS recently_played (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    song_id    INTEGER NOT NULL REFERENCES songs (id) ON DELETE CASCADE,
    played_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recent_user_played ON recently_played (user_id, played_at);
CREATE INDEX IF NOT EXISTS idx_recent_user_song   ON recently_played (user_id, song_id);
