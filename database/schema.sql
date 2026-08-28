-- Vibe Vault Database Schema (MySQL)
-- Personal Music Library & Playlist Management

CREATE DATABASE IF NOT EXISTS `vibe_vault` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `vibe_vault`;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `full_name` VARCHAR(100) NOT NULL,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(120) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `profile_image` VARCHAR(255) DEFAULT 'default_avatar.png',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_users_username` (`username`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Songs Table
CREATE TABLE IF NOT EXISTS `songs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `artist` VARCHAR(150) DEFAULT 'Unknown Artist',
    `album` VARCHAR(150) DEFAULT 'Single',
    `genre` VARCHAR(50) DEFAULT 'Various',
    `audio_file` VARCHAR(255) NOT NULL,
    `cover_image` VARCHAR(255) DEFAULT 'default_cover.png',
    `duration` INT DEFAULT 0 COMMENT 'Duration in seconds',
    `upload_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `play_count` INT DEFAULT 0,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_songs_user` (`user_id`),
    INDEX `idx_songs_title` (`title`),
    INDEX `idx_songs_artist` (`artist`),
    INDEX `idx_songs_genre` (`genre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Playlists Table
CREATE TABLE IF NOT EXISTS `playlists` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT,
    `cover_image` VARCHAR(255) DEFAULT 'default_playlist.png',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_playlists_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Playlist Songs (Many-to-Many with Order Position)
CREATE TABLE IF NOT EXISTS `playlist_songs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `playlist_id` INT NOT NULL,
    `song_id` INT NOT NULL,
    `position` INT DEFAULT 0,
    `added_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`playlist_id`) REFERENCES `playlists`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`song_id`) REFERENCES `songs`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `unique_playlist_song` (`playlist_id`, `song_id`),
    INDEX `idx_playlist_songs_playlist` (`playlist_id`),
    INDEX `idx_playlist_songs_position` (`playlist_id`, `position`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Favorites Table
CREATE TABLE IF NOT EXISTS `favorites` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `song_id` INT NOT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`song_id`) REFERENCES `songs`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `unique_user_favorite` (`user_id`, `song_id`),
    INDEX `idx_favorites_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Recently Played Table
CREATE TABLE IF NOT EXISTS `recently_played` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `song_id` INT NOT NULL,
    `played_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`song_id`) REFERENCES `songs`(`id`) ON DELETE CASCADE,
    INDEX `idx_recent_user_played` (`user_id`, `played_at`),
    INDEX `idx_recent_user_song` (`user_id`, `song_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
