/**
 * VIBE VAULT — PLAYLISTS ENGINE
 * Manages playlist creation, editing, song reordering, and playlist playback.
 */

// Load All Playlists (for /playlists page)
window.loadAllPlaylists = function() {
  const container = document.getElementById('playlists-grid-container');
  if (!container) return;

  container.innerHTML = '<div class="text-center py-5 text-muted"><i class="fas fa-spinner fa-spin fa-2x mb-3"></i><p>Loading playlists...</p></div>';

  fetch('/api/playlists')
    .then(res => res.json())
    .then(data => {
      if (!data.success) return;
      renderPlaylistsGrid(data.playlists);
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = '<div class="alert alert-danger">Error loading playlists.</div>';
    });
};

function renderPlaylistsGrid(playlists) {
  const container = document.getElementById('playlists-grid-container');
  if (!container) return;

  if (playlists.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🎧</div>
        <h3 class="empty-state-title">No playlists yet</h3>
        <p class="empty-state-text">Create custom playlists to organize your favorite music for any mood or activity.</p>
        <button class="btn btn-vibe-primary" onclick="openCreatePlaylistModal()"><i class="fas fa-plus me-2"></i> Create Playlist</button>
      </div>
    `;
    return;
  }

  let html = '<div class="music-grid">';
  playlists.forEach(pl => {
    html += `
      <div class="song-card">
        <a href="/playlist/${pl.id}">
          <div class="song-cover-wrapper">
            <img src="/uploads/covers/${pl.cover_image || 'default_playlist.png'}" class="song-cover-img" alt="${pl.name}">
            <div class="song-play-overlay">
              <button class="play-hover-btn" onclick="event.preventDefault(); playEntirePlaylist(${pl.id});" title="Play Playlist">
                <i class="fas fa-play"></i>
              </button>
            </div>
          </div>
        </a>
        <a href="/playlist/${pl.id}" class="song-info-title text-black d-block">${pl.name}</a>
        <div class="song-info-artist">${pl.song_count} songs • ${formatDuration(pl.total_duration)}</div>
      </div>
    `;
  });
  html += '</div>';
  container.innerHTML = html;
}

// Single Playlist Details Page (/playlist/<id>)
let currentPlaylistSongs = [];

window.loadSinglePlaylist = function(playlistId) {
  const songContainer = document.getElementById('playlist-songs-container');
  if (!songContainer) return;

  fetch(`/api/playlists/${playlistId}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success) return;
      currentPlaylistSongs = data.songs;
      renderSinglePlaylistSongs(data.playlist, data.songs);
    })
    .catch(err => {
      console.error(err);
    });
};

function renderSinglePlaylistSongs(playlist, songs) {
  const container = document.getElementById('playlist-songs-container');
  const countBadge = document.getElementById('playlist-song-count-badge');
  const durationBadge = document.getElementById('playlist-duration-badge');

  if (countBadge) countBadge.textContent = `${songs.length} songs`;
  if (durationBadge) {
    const totalSecs = songs.reduce((sum, s) => sum + (s.duration || 0), 0);
    durationBadge.textContent = formatDuration(totalSecs);
  }

  if (!container) return;

  if (songs.length === 0) {
    container.innerHTML = `
      <div class="empty-state py-5">
        <div class="empty-state-icon">🎶</div>
        <h4 class="empty-state-title">This playlist is empty</h4>
        <p class="empty-state-text">Browse your music library and click "Add to Playlist" on any song to start filling it up.</p>
        <a href="/music" class="btn btn-vibe-secondary"><i class="fas fa-search me-2"></i> Find Songs</a>
      </div>
    `;
    return;
  }

  let html = `
    <div class="song-table-container">
      <table class="song-table">
        <thead>
          <tr>
            <th style="width: 60px;">#</th>
            <th>Title & Artist</th>
            <th>Album</th>
            <th style="width: 80px;"><i class="far fa-clock"></i></th>
            <th style="width: 140px; text-align: right;">Order & Actions</th>
          </tr>
        </thead>
        <tbody>
  `;

  songs.forEach((song, idx) => {
    const isCurrent = window.VibePlayer && window.VibePlayer.getCurrentSong()?.id === song.id;
    const songJson = JSON.stringify(song).replace(/"/g, '&quot;');
    const queueJson = JSON.stringify(songs).replace(/"/g, '&quot;');

    html += `
      <tr class="song-row ${isCurrent ? 'active-track' : ''}" data-song-id="${song.id}" data-index="${idx + 1}">
        <td class="song-index-col" onclick='window.VibePlayer.playTrack(${songJson}, ${queueJson}, ${idx})' style="cursor: pointer;">
          ${isCurrent && window.VibePlayer.isPlaying ? `
            <div class="equalizer"><div class="equalizer-bar"></div><div class="equalizer-bar"></div><div class="equalizer-bar"></div></div>
          ` : (idx + 1)}
        </td>
        <td>
          <div class="d-flex align-items-center">
            <img src="/uploads/covers/${song.cover_image || 'default_cover.png'}" class="song-thumb" style="cursor: pointer;" onclick='window.VibePlayer.playTrack(${songJson}, ${queueJson}, ${idx})'>
            <div style="min-width: 0;">
              <div class="song-title-cell fw-semibold text-truncate text-black" style="cursor: pointer;" onclick='window.VibePlayer.playTrack(${songJson}, ${queueJson}, ${idx})'>
                ${song.title}
              </div>
              <div class="text-muted text-truncate" style="font-size: 12.5px;">${song.artist || 'Unknown Artist'}</div>
            </div>
          </div>
        </td>
        <td class="text-muted text-truncate" style="max-width: 140px;">${song.album || 'Single'}</td>
        <td class="text-muted" style="font-family: 'JetBrains Mono', monospace; font-size: 12.5px;">${formatDuration(song.duration)}</td>
        <td style="text-align: right;">
          <!-- Move Up / Down buttons -->
          <button class="btn btn-sm btn-icon" onclick="moveSongInPlaylist(${playlist.id}, ${idx}, -1)" ${idx === 0 ? 'disabled style="opacity: 0.3;"' : ''} title="Move Up">
            <i class="fas fa-chevron-up"></i>
          </button>
          <button class="btn btn-sm btn-icon" onclick="moveSongInPlaylist(${playlist.id}, ${idx}, 1)" ${idx === songs.length - 1 ? 'disabled style="opacity: 0.3;"' : ''} title="Move Down">
            <i class="fas fa-chevron-down"></i>
          </button>
          <button class="btn-favorite btn-fav-song-${song.id} ${song.is_favorite ? 'active' : ''}" onclick="window.toggleFavorite(${song.id}, this)" title="Favorite">
            <i class="${song.is_favorite ? 'fas fa-heart text-danger' : 'far fa-heart'}"></i>
          </button>
          <button class="btn btn-sm btn-icon text-danger" onclick="removeSongFromCurrentPlaylist(${playlist.id}, ${song.id})" title="Remove from Playlist">
            <i class="fas fa-times"></i>
          </button>
        </td>
      </tr>
    `;
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}

window.playEntirePlaylist = function(playlistId) {
  fetch(`/api/playlists/${playlistId}`)
    .then(res => res.json())
    .then(data => {
      if (data.success && data.songs.length > 0 && window.VibePlayer) {
        window.VibePlayer.playTrack(data.songs[0], data.songs, 0);
        window.showToast(`Playing playlist "${data.playlist.name}"`, 'success');
      } else {
        window.showToast('This playlist is empty.', 'warning');
      }
    });
};

window.shuffleEntirePlaylist = function(playlistId) {
  fetch(`/api/playlists/${playlistId}`)
    .then(res => res.json())
    .then(data => {
      if (data.success && data.songs.length > 0 && window.VibePlayer) {
        if (!window.VibePlayer.isShuffle) {
          window.VibePlayer.toggleShuffle();
        }
        window.VibePlayer.playTrack(data.songs[0], data.songs, 0);
        window.showToast(`Shuffle playing "${data.playlist.name}"`, 'success');
      }
    });
};

window.moveSongInPlaylist = function(playlistId, index, direction) {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= currentPlaylistSongs.length) return;

  const temp = currentPlaylistSongs[index];
  currentPlaylistSongs[index] = currentPlaylistSongs[targetIndex];
  currentPlaylistSongs[targetIndex] = temp;

  const newOrderIds = currentPlaylistSongs.map(s => s.id);

  fetch(`/api/playlists/${playlistId}/reorder`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ song_ids: newOrderIds })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.loadSinglePlaylist(playlistId);
    }
  });
};

window.removeSongFromCurrentPlaylist = function(playlistId, songId) {
  fetch(`/api/playlists/${playlistId}/songs/${songId}`, { method: 'DELETE' })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.showToast('Song removed from playlist.', 'info');
        window.loadSinglePlaylist(playlistId);
      }
    });
};

// Create Playlist Modal
window.openCreatePlaylistModal = function() {
  const modalEl = document.getElementById('createPlaylistModal');
  if (modalEl) new bootstrap.Modal(modalEl).show();
};

window.handleCreatePlaylistSubmit = function(e) {
  e.preventDefault();
  const form = document.getElementById('createPlaylistForm');
  const formData = new FormData(form);

  fetch('/api/playlists', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.showToast(data.message, 'success');
      form.reset();
      bootstrap.Modal.getInstance(document.getElementById('createPlaylistModal'))?.hide();
      if (window.location.pathname === '/playlists') {
        window.loadAllPlaylists();
      } else {
        window.location.href = `/playlist/${data.playlist.id}`;
      }
    } else {
      window.showToast(data.message, 'danger');
    }
  });
};

// Edit Playlist Modal
window.openEditPlaylistModal = function(playlist) {
  const modalEl = document.getElementById('editPlaylistModal');
  if (!modalEl) return;

  document.getElementById('editPlaylistId').value = playlist.id;
  document.getElementById('editPlaylistName').value = playlist.name;
  document.getElementById('editPlaylistDesc').value = playlist.description || '';

  new bootstrap.Modal(modalEl).show();
};

window.handleEditPlaylistSubmit = function(e) {
  e.preventDefault();
  const playlistId = document.getElementById('editPlaylistId').value;
  const form = document.getElementById('editPlaylistForm');
  const formData = new FormData(form);

  fetch(`/api/playlists/${playlistId}`, {
    method: 'PUT',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.showToast(data.message, 'success');
      window.location.reload();
    } else {
      window.showToast(data.message, 'danger');
    }
  });
};

window.confirmDeletePlaylist = function(playlistId, playlistName) {
  if (confirm(`Are you sure you want to delete the playlist "${playlistName}"? Songs will remain in your library.`)) {
    fetch(`/api/playlists/${playlistId}`, { method: 'DELETE' })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          window.showToast(data.message, 'success');
          window.location.href = '/playlists';
        }
      });
  }
};
