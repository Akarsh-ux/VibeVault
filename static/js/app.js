/**
 * VIBE VAULT — CORE APPLICATION SCRIPT
 * Manages toast notifications, CSRF protection, global search, and modal workflows.
 */

// CSRF Token helper - reads from meta tag injected by Flask
window.getCsrfToken = function() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
};

// HTML escape utility to prevent XSS in innerHTML assignments
window.escapeHtml = function(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};


// Toast Notification Manager
window.showToast = function(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container-custom';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'vibe-toast';
  
  const icons = {
    success: 'fas fa-check-circle text-success',
    danger: 'fas fa-exclamation-circle text-danger',
    warning: 'fas fa-exclamation-triangle text-warning',
    info: 'fas fa-info-circle text-info'
  };

  toast.innerHTML = `
    <i class="${icons[type] || icons.info}"></i>
    <div style="flex-grow: 1; font-size: 13.5px; font-weight: 500;">${message}</div>
    <button type="button" class="btn-close btn-close-white" style="font-size: 10px;" onclick="this.parentElement.remove()"></button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
};

// Global Favorite Toggle
window.toggleFavorite = function(songId, btn) {
  fetch(`/api/favorites/toggle/${songId}`, {
    method: 'POST',
    headers: { 'X-CSRF-Token': window.getCsrfToken() }
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        // Update all favorite buttons for this song on the page
        document.querySelectorAll(`.btn-fav-song-${songId}`).forEach(b => {
          b.innerHTML = data.is_favorite ? '<i class="fas fa-heart text-danger"></i>' : '<i class="far fa-heart"></i>';
        });
        
        // If the player is currently playing this song, update bottom player icon
        if (window.VibePlayer && window.VibePlayer.getCurrentSong() && window.VibePlayer.getCurrentSong().id == songId) {
          const current = window.VibePlayer.getCurrentSong();
          current.is_favorite = data.is_favorite;
          const playerFavIcon = document.getElementById('player-favorite-icon');
          if (playerFavIcon) {
            playerFavIcon.className = data.is_favorite ? 'fas fa-heart text-danger' : 'far fa-heart';
          }
        }
        
        window.showToast(data.message, data.is_favorite ? 'success' : 'info');
      }
    })
    .catch(err => {
      console.error(err);
      window.showToast('Could not update favorites.', 'danger');
    });
};

// Add to Playlist Modal Workflow
window.openAddToPlaylistModal = function(songId, songTitle) {
  let modalEl = document.getElementById('addToPlaylistModal');
  if (!modalEl) return;
  
  const titleEl = document.getElementById('modalSongTitle');
  if (titleEl) titleEl.textContent = songTitle || 'Song';
  
  const listEl = document.getElementById('modalPlaylistList');
  if (listEl) {
    listEl.innerHTML = '<div class="text-center py-4 text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Loading your playlists...</div>';
  }
  
  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();
  
  // Fetch playlists for this song
  fetch(`/api/user/playlists-for-song/${songId}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success || !listEl) return;
      
      if (data.playlists.length === 0) {
        listEl.innerHTML = `
          <div class="text-center py-3 text-muted">
            <p class="mb-2">No playlists created yet.</p>
            <button class="btn btn-sm btn-vibe-primary" onclick="openCreatePlaylistQuickModal(${songId})">
              <i class="fas fa-plus me-1"></i> Create Playlist
            </button>
          </div>
        `;
        return;
      }
      
      let html = '<div class="list-group list-group-flush bg-transparent">';
      data.playlists.forEach(pl => {
        const isAdded = pl.contains_song === 1;
        html += `
          <div class="list-group-item bg-transparent border-secondary text-black d-flex align-items-center justify-content-between py-2">
            <div class="d-flex align-items-center gap-3">
              <img src="/uploads/covers/${pl.cover_image || 'default_playlist.png'}" style="width: 38px; height: 38px; border-radius: 6px; object-fit: cover;">
              <div>
                <div class="fw-semibold text-black">${pl.name}</div>
              </div>
            </div>
            <div>
              ${isAdded ? `
                <button class="btn btn-sm btn-outline-danger" onclick="removeSongFromPlaylistAction(${pl.id}, ${songId}, '${pl.name.replace(/'/g, "\\'")}')">
                  <i class="fas fa-check me-1"></i> Added
                </button>
              ` : `
                <button class="btn btn-sm btn-vibe-primary" onclick="addSongToPlaylistAction(${pl.id}, ${songId}, '${pl.name.replace(/'/g, "\\'")}')">
                  <i class="fas fa-plus me-1"></i> Add
                </button>
              `}
            </div>
          </div>
        `;
      });
      html += '</div>';
      listEl.innerHTML = html;
    });
};

window.addSongToPlaylistAction = function(playlistId, songId, playlistName) {
  fetch(`/api/playlists/${playlistId}/songs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': window.getCsrfToken() },
    body: JSON.stringify({ song_id: songId })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.showToast(data.message, 'success');
      window.openAddToPlaylistModal(songId, document.getElementById('modalSongTitle')?.textContent);
    } else {
      window.showToast(data.message, 'warning');
    }
  });
};

window.removeSongFromPlaylistAction = function(playlistId, songId, playlistName) {
  fetch(`/api/playlists/${playlistId}/songs/${songId}`, {
    method: 'DELETE',
    headers: { 'X-CSRF-Token': window.getCsrfToken() }
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      window.showToast(data.message, 'info');
      window.openAddToPlaylistModal(songId, document.getElementById('modalSongTitle')?.textContent);
    }
  });
};

// Global Live Search Logic
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('global-search-input');
  const searchDropdown = document.getElementById('search-dropdown');
  let searchTimeout = null;

  if (searchInput && searchDropdown) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      clearTimeout(searchTimeout);

      if (query.length === 0) {
        searchDropdown.style.display = 'none';
        searchDropdown.innerHTML = '';
        return;
      }

      searchTimeout = setTimeout(() => {
        fetch(`/api/search?q=${encodeURIComponent(query)}`)
          .then(res => res.json())
          .then(data => {
            if (!data.success) return;
            const { songs, playlists } = data.results;

            if (songs.length === 0 && playlists.length === 0) {
              searchDropdown.innerHTML = `
                <div class="text-center py-3 text-muted" style="font-size: 13px;">
                  <i class="fas fa-search me-1"></i> No results found for "${query}"
                </div>
              `;
              searchDropdown.style.display = 'block';
              return;
            }

            let html = '';

            // Songs Section
            if (songs.length > 0) {
              html += `<div class="search-section-title">Songs (${songs.length})</div>`;
              songs.slice(0, 5).forEach(s => {
                const songJson = JSON.stringify(s).replace(/"/g, '&quot;');
                html += `
                  <div class="search-result-item" onclick='window.VibePlayer.playTrack(${songJson})'>
                    <img src="/uploads/covers/${s.cover_image || 'default_cover.png'}" class="search-result-img">
                    <div style="flex-grow: 1; overflow: hidden;">
                      <div class="text-truncate fw-semibold" style="font-size: 13.5px;">${s.title}</div>
                      <div class="text-truncate text-muted" style="font-size: 11.5px;">${s.artist} • ${s.genre}</div>
                    </div>
                    <i class="fas fa-play text-cyan" style="font-size: 12px;"></i>
                  </div>
                `;
              });
            }

            // Playlists Section
            if (playlists.length > 0) {
              html += `<div class="search-section-title">Playlists (${playlists.length})</div>`;
              playlists.slice(0, 4).forEach(p => {
                html += `
                  <a href="/playlist/${p.id}" class="search-result-item">
                    <img src="/uploads/covers/${p.cover_image || 'default_playlist.png'}" class="search-result-img">
                    <div style="flex-grow: 1; overflow: hidden;">
                      <div class="text-truncate fw-semibold" style="font-size: 13.5px;">${p.name}</div>
                      <div class="text-truncate text-muted" style="font-size: 11.5px;">${p.song_count} songs</div>
                    </div>
                    <i class="fas fa-chevron-right text-muted" style="font-size: 11px;"></i>
                  </a>
                `;
              });
            }

            searchDropdown.innerHTML = html;
            searchDropdown.style.display = 'block';
          });
      }, 250);
    });

    // Close search dropdown on click outside
    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
        searchDropdown.style.display = 'none';
      }
    });
  }

  // Mobile sidebar toggle
  const sidebarToggleBtn = document.getElementById('mobile-sidebar-toggle');
  const sidebar = document.getElementById('app-sidebar');
  if (sidebarToggleBtn && sidebar) {
    sidebarToggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('show');
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (window.innerWidth < 992 && !sidebar.contains(e.target) && !sidebarToggleBtn.contains(e.target)) {
        sidebar.classList.remove('show');
      }
    });
  }
});
