/**
 * VIBE VAULT — SONGS & LIBRARY MANAGEMENT
 * Handles dynamic search/filter, sorting, edit, delete, and audio file duration preview.
 */

let currentSongList = [];

// Load and render user's song library
window.loadSongs = function() {
  const query = document.getElementById('song-search-filter')?.value || '';
  const genre = document.getElementById('genre-filter')?.value || 'all';
  const sort = document.getElementById('sort-filter')?.value || 'recent';
  const songContainer = document.getElementById('songs-container');

  if (!songContainer) return;
  songContainer.innerHTML = '<div class="text-center py-5 text-muted"><i class="fas fa-spinner fa-spin fa-2x mb-3"></i><p>Loading your music...</p></div>';

  fetch(`/api/songs?q=${encodeURIComponent(query)}&genre=${encodeURIComponent(genre)}&sort=${encodeURIComponent(sort)}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success) return;
      currentSongList = data.songs;
      renderSongList(currentSongList);
    })
    .catch(err => {
      console.error(err);
      songContainer.innerHTML = '<div class="alert alert-danger">Error loading music library.</div>';
    });
};

function renderSongList(songs) {
  const container = document.getElementById('songs-container');
  if (!container) return;

  if (songs.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🎵</div>
        <h3 class="empty-state-title">Your music library is empty</h3>
        <p class="empty-state-text">Upload your first song and start building your personal Vibe Vault collection.</p>
        <a href="/upload" class="btn btn-vibe-primary"><i class="fas fa-cloud-upload-alt me-2"></i> Upload Music</a>
      </div>
    `;
    return;
  }

  let html = `
    <div class="song-table-container">
      <table class="song-table">
        <thead>
          <tr>
            <th style="width: 50px;">#</th>
            <th>Title & Artist</th>
            <th>Album</th>
            <th>Genre</th>
            <th>Plays</th>
            <th style="width: 80px;"><i class="far fa-clock"></i></th>
            <th style="width: 140px; text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
  `;

  songs.forEach((song, idx) => {
    const isCurrentPlaying = window.VibePlayer && window.VibePlayer.getCurrentSong()?.id === song.id;
    const songJson = JSON.stringify(song).replace(/"/g, '&quot;');
    const queueJson = JSON.stringify(songs).replace(/"/g, '&quot;');

    html += `
      <tr class="song-row ${isCurrentPlaying ? 'active-track' : ''}" data-song-id="${song.id}" data-index="${idx + 1}">
        <td class="song-index-col" onclick='window.VibePlayer.playTrack(${songJson}, ${queueJson}, ${idx})' style="cursor: pointer;">
          ${isCurrentPlaying && window.VibePlayer.isPlaying ? `
            <div class="equalizer"><div class="equalizer-bar"></div><div class="equalizer-bar"></div><div class="equalizer-bar"></div></div>
          ` : (idx + 1)}
        </td>
        <td>
          <div class="d-flex align-items-center">
            <div class="position-relative" style="cursor: pointer;" onclick='window.VibePlayer.playTrack(${songJson}, ${queueJson}, ${idx})'>
              <img src="/uploads/covers/${song.cover_image || 'default_cover.png'}" class="song-thumb">
            </div>
            <div style="min-width: 0;">
              <div class="song-title-cell fw-semibold text-truncate text-black" style="cursor: pointer;" onclick='window.VibePlayer.playTrack(${songJson}, ${queueJson}, ${idx})'>
                ${song.title}
              </div>
              <div class="text-muted text-truncate" style="font-size: 12.5px;">${song.artist || 'Unknown Artist'}</div>
            </div>
          </div>
        </td>
        <td class="text-muted text-truncate" style="max-width: 140px;">${song.album || 'Single'}</td>
        <td><span class="badge-genre">${song.genre || 'Various'}</span></td>
        <td class="text-muted" style="font-family: 'JetBrains Mono', monospace; font-size: 12.5px;">${song.play_count || 0}</td>
        <td class="text-muted" style="font-family: 'JetBrains Mono', monospace; font-size: 12.5px;">${formatDuration(song.duration)}</td>
        <td style="text-align: right;">
          <button class="btn-favorite btn-fav-song-${song.id} ${song.is_favorite ? 'active' : ''}" onclick="window.toggleFavorite(${song.id}, this)" title="Favorite">
            <i class="${song.is_favorite ? 'fas fa-heart text-danger' : 'far fa-heart'}"></i>
          </button>
          <button class="btn btn-sm btn-icon" onclick="window.openAddToPlaylistModal(${song.id}, '${song.title.replace(/'/g, "\\'")}')" title="Add to Playlist">
            <i class="fas fa-list-ul"></i>
          </button>
          <button class="btn btn-sm btn-icon" onclick='openEditSongModal(${songJson})' title="Edit Song">
            <i class="fas fa-pen"></i>
          </button>
          <button class="btn btn-sm btn-icon text-danger" onclick='confirmDeleteSong(${song.id}, "${song.title.replace(/"/g, '&quot;')}")' title="Delete Song">
            <i class="fas fa-trash-alt"></i>
          </button>
        </td>
      </tr>
    `;
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}

window.playAllFilteredSongs = function() {
  if (currentSongList.length > 0 && window.VibePlayer) {
    window.VibePlayer.playTrack(currentSongList[0], currentSongList, 0);
  }
};

function formatDuration(sec) {
  if (!sec || isNaN(sec)) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// Edit Song Modal Functionality
window.openEditSongModal = function(song) {
  const modalEl = document.getElementById('editSongModal');
  if (!modalEl) return;

  document.getElementById('editSongId').value = song.id;
  document.getElementById('editSongTitle').value = song.title;
  document.getElementById('editSongArtist').value = song.artist || '';
  document.getElementById('editSongAlbum').value = song.album || '';
  document.getElementById('editSongGenre').value = song.genre || '';
  document.getElementById('editSongCoverPreview').src = `/uploads/covers/${song.cover_image || 'default_cover.png'}`;

  new bootstrap.Modal(modalEl).show();
};

window.saveSongEdit = function(e) {
  e.preventDefault();
  const songId = document.getElementById('editSongId').value;
  const form = document.getElementById('editSongForm');
  const formData = new FormData(form);

  fetch(`/api/songs/${songId}`, {
    method: 'PUT',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.showToast(data.message, 'success');
      bootstrap.Modal.getInstance(document.getElementById('editSongModal')).hide();
      window.loadSongs();
    } else {
      window.showToast(data.message, 'danger');
    }
  });
};

// Delete Song Confirmation
window.confirmDeleteSong = function(songId, songTitle) {
  if (confirm(`Are you sure you want to delete "${songTitle}"? This will also remove it from your playlists and history.`)) {
    fetch(`/api/songs/${songId}`, { method: 'DELETE' })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          window.showToast(data.message, 'success');
          window.loadSongs();
        } else {
          window.showToast(data.message, 'danger');
        }
      });
  }
};

// Audio File Client-side Duration Detection & Drag and Drop
document.addEventListener('DOMContentLoaded', () => {
  const audioInput = document.getElementById('audio_file_input');
  const durationInput = document.getElementById('detected_duration');
  const fileNameDisplay = document.getElementById('selected_audio_name');

  if (audioInput) {
    audioInput.addEventListener('change', function(e) {
      const file = this.files[0];
      if (file) {
        if (fileNameDisplay) fileNameDisplay.textContent = `Selected: ${file.name} (${(file.size / (1024*1024)).toFixed(2)} MB)`;
        
        // Auto-fill title if empty
        const titleField = document.getElementById('song_title_input');
        if (titleField && !titleField.value) {
          const rawName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
          titleField.value = rawName.replace(/[_]/g, ' ').replace(/-/g, ' ').trim();
        }

        // Calculate duration via Audio element
        const reader = new FileReader();
        reader.onload = function(evt) {
          const tempAudio = new Audio();
          tempAudio.src = evt.target.result;
          tempAudio.addEventListener('loadedmetadata', function() {
            if (durationInput) {
              durationInput.value = Math.round(tempAudio.duration);
            }
          });
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Cover image preview
  const coverInput = document.getElementById('cover_image_input');
  const coverPreview = document.getElementById('cover_preview_img');
  if (coverInput && coverPreview) {
    coverInput.addEventListener('change', function() {
      const file = this.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
          coverPreview.src = e.target.result;
          coverPreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  }
});
