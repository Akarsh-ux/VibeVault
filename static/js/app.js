/**
 * VIBE VAULT — CORE APPLICATION & PERSISTENT SPA ROUTER
 * Seamless SPA navigation, persistent audio lifecycle, global search, toasts, and modal workflows.
 */

// CSRF Token helper - reads from meta tag injected by Flask
window.getCsrfToken = function() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
};

// HTML escape utility
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
    success: 'fas fa-check-circle',
    danger: 'fas fa-exclamation-circle',
    warning: 'fas fa-exclamation-triangle',
    info: 'fas fa-info-circle'
  };

  toast.innerHTML = `
    <i class="${icons[type] || icons.info}"></i>
    <div style="flex-grow: 1; font-size: 13.5px; font-weight: 600; color: var(--text-main);">${message}</div>
    <button type="button" class="btn-close" style="font-size: 10px;" onclick="this.parentElement.remove()"></button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 350);
  }, 3500);
};

// ---------------------------------------------------------------------------
// SEAMLESS PERSISTENT SPA ROUTER
// Intercepts in-app navigation so that audio playback NEVER stops or resets
// ---------------------------------------------------------------------------

window.navigateTo = function(url, pushState = true) {
  // Disallow external or auth links
  if (!url || url.startsWith('http://') || url.startsWith('https://') || url.includes('/logout')) {
    window.location.href = url;
    return;
  }

  const contentContainer = document.querySelector('.content-body');
  if (!contentContainer) {
    window.location.href = url;
    return;
  }

  contentContainer.classList.add('page-transitioning');

  fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.text();
    })
    .then(htmlText => {
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, 'text/html');

      // Update Document Title
      const newTitle = doc.querySelector('title');
      if (newTitle) {
        document.title = newTitle.textContent;
      }

      // Extract new content body
      const newContent = doc.querySelector('.content-body');
      if (newContent) {
        contentContainer.innerHTML = newContent.innerHTML;
      } else {
        // Fallback for public or unexpected pages
        window.location.href = url;
        return;
      }

      if (pushState) {
        window.history.pushState({ path: url }, '', url);
      }

      // Update active state in sidebar navigation
      updateSidebarActive(window.location.pathname);

      // Close mobile sidebar if open
      const sidebar = document.getElementById('app-sidebar');
      if (sidebar) sidebar.classList.remove('show');

      // Re-initialize page specific scripts and DOM elements
      initPageLifecycle(window.location.pathname);

      // Restore active track highlight from persistent player
      if (window.VibePlayer) {
        window.VibePlayer.highlightActiveInDOM();
      }

      // Smooth scroll to top of content
      window.scrollTo({ top: 0, behavior: 'smooth' });
    })
    .catch(err => {
      console.warn("SPA navigation error, falling back to standard navigation:", err);
      window.location.href = url;
    })
    .finally(() => {
      setTimeout(() => {
        contentContainer.classList.remove('page-transitioning');
      }, 50);
    });
};

function updateSidebarActive(pathname) {
  document.querySelectorAll('.app-sidebar .nav-link-item').forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;
    const linkPath = new URL(href, window.location.origin).pathname;
    
    const isActive = (linkPath === pathname) ||
      (pathname.startsWith('/playlist') && linkPath.startsWith('/playlist')) ||
      (pathname === '/music' && linkPath === '/music');

    link.classList.toggle('active', isActive);
  });
}

function initPageLifecycle(pathname) {
  if (pathname === '/music') {
    if (typeof window.loadSongs === 'function') window.loadSongs();
  } else if (pathname === '/playlists') {
    if (typeof window.loadAllPlaylists === 'function') window.loadAllPlaylists();
  } else if (pathname.startsWith('/playlist/')) {
    const parts = pathname.split('/');
    const playlistId = parts[parts.length - 1];
    if (playlistId && typeof window.loadSinglePlaylist === 'function') {
      window.loadSinglePlaylist(playlistId);
    }
  } else if (pathname === '/favorites') {
    if (typeof window.loadFavorites === 'function') window.loadFavorites();
  } else if (pathname === '/recently-played') {
    if (typeof window.loadRecentlyPlayed === 'function') window.loadRecentlyPlayed();
  }
}

// Intercept PopState for Browser Back/Forward navigation
window.addEventListener('popstate', (e) => {
  window.navigateTo(window.location.pathname + window.location.search, false);
});

// Global Link Click Interceptor for SPA Navigation
document.addEventListener('click', (e) => {
  const link = e.target.closest('a');
  if (!link) return;

  const href = link.getAttribute('href');
  if (!href) return;

  // Ignore anchors, external links, javascript:, or special target attributes
  if (href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) return;
  if (link.target === '_blank' || link.hasAttribute('download')) return;
  if (href.includes('/logout')) return;

  // Verify link is an in-app relative route
  try {
    const url = new URL(link.href, window.location.origin);
    if (url.origin === window.location.origin) {
      // Check if we are inside the authenticated layout
      if (document.querySelector('.app-wrapper')) {
        e.preventDefault();
        window.navigateTo(url.pathname + url.search);
      }
    }
  } catch (err) {
    // Standard link fallback
  }
});

// ---------------------------------------------------------------------------
// Global Favorites & Playlist Workflows
// ---------------------------------------------------------------------------

window.toggleFavorite = function(songId, btn) {
  fetch(`/api/favorites/toggle/${songId}`, {
    method: 'POST',
    headers: { 'X-CSRF-Token': window.getCsrfToken() }
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        document.querySelectorAll(`.btn-fav-song-${songId}`).forEach(b => {
          b.innerHTML = data.is_favorite ? '<i class="fas fa-heart"></i>' : '<i class="far fa-heart"></i>';
          b.classList.toggle('active', data.is_favorite);
        });
        
        if (window.VibePlayer && window.VibePlayer.getCurrentSong() && window.VibePlayer.getCurrentSong().id == songId) {
          const current = window.VibePlayer.getCurrentSong();
          current.is_favorite = data.is_favorite;
          const playerFavIcon = document.getElementById('player-favorite-icon');
          if (playerFavIcon) {
            playerFavIcon.className = data.is_favorite ? 'fas fa-heart' : 'far fa-heart';
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

window.openAddToPlaylistModal = function(songId, songTitle) {
  let modalEl = document.getElementById('addToPlaylistModal');
  if (!modalEl) return;
  
  const titleEl = document.getElementById('modalSongTitle');
  if (titleEl) titleEl.textContent = songTitle || 'Song';
  
  const listEl = document.getElementById('modalPlaylistList');
  if (listEl) {
    listEl.innerHTML = '<div class="text-center py-4 text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Loading playlists...</div>';
  }
  
  const bsModal = new bootstrap.Modal(modalEl);
  bsModal.show();
  
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
          <div class="list-group-item bg-transparent border-light d-flex align-items-center justify-content-between py-2">
            <div class="d-flex align-items-center gap-3">
              <img src="/uploads/covers/${pl.cover_image || 'default_playlist.png'}" style="width: 40px; height: 40px; border-radius: 8px; object-fit: cover; border: 1px solid var(--border-light);">
              <div>
                <div class="fw-semibold text-heading">${pl.name}</div>
              </div>
            </div>
            <div>
              ${isAdded ? `
                <button class="btn btn-sm btn-vibe-secondary text-primary" onclick="removeSongFromPlaylistAction(${pl.id}, ${songId}, '${pl.name.replace(/'/g, "\\'")}')">
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

// ---------------------------------------------------------------------------
// Global Live Search & Mobile Sidebar
// ---------------------------------------------------------------------------
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
                  <div class="search-result-item" onclick='window.VibePlayer.playTrack(${songJson}); document.getElementById("search-dropdown").style.display="none";'>
                    <img src="/uploads/covers/${s.cover_image || 'default_cover.png'}" class="search-result-img">
                    <div style="flex-grow: 1; overflow: hidden;">
                      <div class="text-truncate fw-semibold" style="font-size: 13.5px;">${s.title}</div>
                      <div class="text-truncate text-muted" style="font-size: 11.5px;">${s.artist} • ${s.genre}</div>
                    </div>
                    <i class="fas fa-play text-primary" style="font-size: 12px;"></i>
                  </div>
                `;
              });
            }

            // Playlists Section
            if (playlists.length > 0) {
              html += `<div class="search-section-title">Playlists (${playlists.length})</div>`;
              playlists.slice(0, 4).forEach(p => {
                html += `
                  <a href="/playlist/${p.id}" class="search-result-item" onclick='document.getElementById("search-dropdown").style.display="none";'>
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

    document.addEventListener('click', (e) => {
      if (window.innerWidth < 992 && !sidebar.contains(e.target) && !sidebarToggleBtn.contains(e.target)) {
        sidebar.classList.remove('show');
      }
    });
  }
});
