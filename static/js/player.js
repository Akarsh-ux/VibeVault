/**
 * VIBE VAULT — ADVANCED HTML5 AUDIO PLAYER ENGINE
 * Persistent audio playback, queue management, shuffle/repeat, seeking, and media session API.
 */

class VibeVaultPlayer {
  constructor() {
    this.audio = new Audio();
    this.queue = [];
    this.originalQueue = [];
    this.currentIndex = -1;
    this.isPlaying = false;
    this.isMuted = false;
    this.volume = 0.8;
    this.isShuffle = false;
    this.repeatMode = 'none'; // 'none', 'all', 'one'
    this.playTimer = null;
    this.hasLoggedPlay = false;

    this.initElements();
    this.attachEventListeners();
    this.restoreState();
  }

  initElements() {
    this.elements = {
      playerBar: document.getElementById('bottom-player'),
      cover: document.getElementById('player-cover'),
      title: document.getElementById('player-title'),
      artist: document.getElementById('player-artist'),
      playBtn: document.getElementById('player-play-btn'),
      playIcon: document.getElementById('player-play-icon'),
      prevBtn: document.getElementById('player-prev-btn'),
      nextBtn: document.getElementById('player-next-btn'),
      shuffleBtn: document.getElementById('player-shuffle-btn'),
      repeatBtn: document.getElementById('player-repeat-btn'),
      currentTime: document.getElementById('player-current-time'),
      totalTime: document.getElementById('player-total-time'),
      scrubberContainer: document.getElementById('player-scrubber'),
      scrubberFill: document.getElementById('player-scrubber-fill'),
      volumeSlider: document.getElementById('player-volume-slider'),
      muteBtn: document.getElementById('player-mute-btn'),
      muteIcon: document.getElementById('player-mute-icon'),
      favoriteBtn: document.getElementById('player-favorite-btn'),
      favoriteIcon: document.getElementById('player-favorite-icon')
    };
  }

  attachEventListeners() {
    // Audio element native events
    this.audio.addEventListener('timeupdate', () => this.onTimeUpdate());
    this.audio.addEventListener('loadedmetadata', () => this.onMetadataLoaded());
    this.audio.addEventListener('ended', () => this.onTrackEnded());
    this.audio.addEventListener('play', () => this.onPlayStateChange(true));
    this.audio.addEventListener('pause', () => this.onPlayStateChange(false));
    this.audio.addEventListener('error', (e) => this.onAudioError(e));

    // UI Click Events
    if (this.elements.playBtn) {
      this.elements.playBtn.addEventListener('click', () => this.togglePlay());
    }
    if (this.elements.prevBtn) {
      this.elements.prevBtn.addEventListener('click', () => this.prev());
    }
    if (this.elements.nextBtn) {
      this.elements.nextBtn.addEventListener('click', () => this.next());
    }
    if (this.elements.shuffleBtn) {
      this.elements.shuffleBtn.addEventListener('click', () => this.toggleShuffle());
    }
    if (this.elements.repeatBtn) {
      this.elements.repeatBtn.addEventListener('click', () => this.toggleRepeat());
    }
    if (this.elements.muteBtn) {
      this.elements.muteBtn.addEventListener('click', () => this.toggleMute());
    }
    if (this.elements.volumeSlider) {
      this.elements.volumeSlider.addEventListener('input', (e) => this.setVolume(parseFloat(e.target.value)));
    }
    if (this.elements.scrubberContainer) {
      this.elements.scrubberContainer.addEventListener('click', (e) => this.onScrub(e));
    }
    if (this.elements.favoriteBtn) {
      this.elements.favoriteBtn.addEventListener('click', () => this.toggleCurrentFavorite());
    }

    // Keyboard Spacebar play/pause shortcut (ignore in input fields)
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        this.togglePlay();
      }
    });
  }

  /** Load a track and start playing */
  playTrack(song, queue = null, index = 0) {
    if (!song) return;

    if (queue && queue.length > 0) {
      this.originalQueue = [...queue];
      this.queue = this.isShuffle ? this.shuffleArray([...queue]) : [...queue];
      this.currentIndex = this.queue.findIndex(s => s.id === song.id);
      if (this.currentIndex === -1) this.currentIndex = index;
    } else if (this.queue.length === 0) {
      this.queue = [song];
      this.originalQueue = [song];
      this.currentIndex = 0;
    }

    const currentSong = this.queue[this.currentIndex] || song;
    this.loadAudioSource(currentSong);
    this.updateUI(currentSong);

    this.audio.play().then(() => {
      this.isPlaying = true;
      this.saveState();
      this.startPlayLoggingTimer(currentSong.id);
      this.updateMediaSession(currentSong);
      this.highlightActiveInDOM();
    }).catch(err => {
      console.warn("Autoplay blocked or playback error:", err);
    });
  }

  loadAudioSource(song) {
    // Use authenticated stream endpoint — audio files are never served publicly
    const audioUrl = `/api/stream/${song.id}`;
    const fullUrl = window.location.origin + audioUrl;
    if (this.audio.src !== fullUrl) {
      this.audio.src = audioUrl;
      this.audio.load();
    }
  }

  togglePlay() {
    if (!this.audio.src || this.queue.length === 0) return;

    if (this.audio.paused) {
      this.audio.play().catch(e => console.error(e));
    } else {
      this.audio.pause();
    }
  }

  next() {
    if (this.queue.length === 0) return;

    if (this.currentIndex < this.queue.length - 1) {
      this.currentIndex++;
      this.playTrack(this.queue[this.currentIndex]);
    } else if (this.repeatMode === 'all') {
      this.currentIndex = 0;
      this.playTrack(this.queue[this.currentIndex]);
    }
  }

  prev() {
    if (this.queue.length === 0) return;

    // If played more than 3 seconds, restart current track
    if (this.audio.currentTime > 3) {
      this.audio.currentTime = 0;
      return;
    }

    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.playTrack(this.queue[this.currentIndex]);
    } else if (this.repeatMode === 'all') {
      this.currentIndex = this.queue.length - 1;
      this.playTrack(this.queue[this.currentIndex]);
    }
  }

  toggleShuffle() {
    this.isShuffle = !this.isShuffle;
    if (this.elements.shuffleBtn) {
      this.elements.shuffleBtn.classList.toggle('active', this.isShuffle);
    }

    const currentSong = this.getCurrentSong();
    if (this.isShuffle) {
      this.queue = this.shuffleArray([...this.originalQueue]);
      if (currentSong) {
        // Move currently playing to first
        this.queue = this.queue.filter(s => s.id !== currentSong.id);
        this.queue.unshift(currentSong);
        this.currentIndex = 0;
      }
    } else {
      this.queue = [...this.originalQueue];
      if (currentSong) {
        this.currentIndex = this.queue.findIndex(s => s.id === currentSong.id);
      }
    }
    this.saveState();
  }

  toggleRepeat() {
    const modes = ['none', 'all', 'one'];
    const nextIdx = (modes.indexOf(this.repeatMode) + 1) % modes.length;
    this.repeatMode = modes[nextIdx];

    if (this.elements.repeatBtn) {
      this.elements.repeatBtn.classList.toggle('active', this.repeatMode !== 'none');
      if (this.repeatMode === 'one') {
        this.elements.repeatBtn.innerHTML = '<i class="fas fa-redo-alt"></i><span style="font-size: 8px; position: absolute; font-weight: 800;">1</span>';
      } else {
        this.elements.repeatBtn.innerHTML = '<i class="fas fa-redo-alt"></i>';
      }
    }
    this.saveState();
  }

  setVolume(vol) {
    this.volume = Math.max(0, Math.min(1, vol));
    this.audio.volume = this.volume;
    this.isMuted = this.volume === 0;
    this.updateVolumeUI();
    this.saveState();
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    this.audio.muted = this.isMuted;
    this.updateVolumeUI();
  }

  onScrub(e) {
    if (!this.audio.duration) return;
    const rect = this.elements.scrubberContainer.getBoundingClientRect();
    const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    this.audio.currentTime = percent * this.audio.duration;
  }

  onTimeUpdate() {
    if (!this.audio.duration) return;
    const current = this.audio.currentTime;
    const duration = this.audio.duration;

    const percent = (current / duration) * 100;
    if (this.elements.scrubberFill) {
      this.elements.scrubberFill.style.width = `${percent}%`;
    }
    if (this.elements.currentTime) {
      this.elements.currentTime.textContent = this.formatTime(current);
    }
  }

  onMetadataLoaded() {
    if (this.elements.totalTime && this.audio.duration) {
      this.elements.totalTime.textContent = this.formatTime(this.audio.duration);
    }
  }

  onTrackEnded() {
    if (this.repeatMode === 'one') {
      this.audio.currentTime = 0;
      this.audio.play();
    } else {
      this.next();
    }
  }

  onPlayStateChange(isPlaying) {
    this.isPlaying = isPlaying;
    if (this.elements.playIcon) {
      this.elements.playIcon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
    }
    this.highlightActiveInDOM();
  }

  onAudioError(e) {
    console.error("Audio playback error:", e);
  }

  getCurrentSong() {
    return this.queue[this.currentIndex] || null;
  }

  formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  updateUI(song) {
    if (!song) return;
    if (this.elements.title) this.elements.title.textContent = song.title;
    if (this.elements.artist) this.elements.artist.textContent = song.artist || 'Unknown Artist';
    
    if (this.elements.cover) {
      const coverUrl = song.cover_url || `/uploads/covers/${song.cover_image || 'default_cover.png'}`;
      this.elements.cover.src = coverUrl;
    }

    if (this.elements.favoriteBtn && this.elements.favoriteIcon) {
      this.elements.favoriteIcon.className = song.is_favorite ? 'fas fa-heart text-danger' : 'far fa-heart';
      this.elements.favoriteBtn.dataset.songId = song.id;
    }

    if (this.elements.totalTime && song.duration) {
      this.elements.totalTime.textContent = this.formatTime(song.duration);
    }
  }

  updateVolumeUI() {
    if (this.elements.volumeSlider) {
      this.elements.volumeSlider.value = this.isMuted ? 0 : this.volume;
    }
    if (this.elements.muteIcon) {
      if (this.isMuted || this.volume === 0) {
        this.elements.muteIcon.className = 'fas fa-volume-mute';
      } else if (this.volume < 0.5) {
        this.elements.muteIcon.className = 'fas fa-volume-down';
      } else {
        this.elements.muteIcon.className = 'fas fa-volume-up';
      }
    }
  }

  toggleCurrentFavorite() {
    const song = this.getCurrentSong();
    if (!song) return;
    
    fetch(`/api/favorites/toggle/${song.id}`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          song.is_favorite = data.is_favorite;
          if (this.elements.favoriteIcon) {
            this.elements.favoriteIcon.className = data.is_favorite ? 'fas fa-heart text-danger' : 'far fa-heart';
          }
          // Update any cards/rows on current page
          document.querySelectorAll(`.btn-fav-song-${song.id}`).forEach(btn => {
            btn.innerHTML = data.is_favorite ? '<i class="fas fa-heart text-danger"></i>' : '<i class="far fa-heart"></i>';
          });
          if (window.showToast) window.showToast(data.message, 'info');
        }
      });
  }

  /** Logs song playback to server after 5 seconds */
  startPlayLoggingTimer(songId) {
    if (this.playTimer) clearTimeout(this.playTimer);
    this.hasLoggedPlay = false;

    this.playTimer = setTimeout(() => {
      if (this.isPlaying && !this.hasLoggedPlay) {
        fetch('/api/recently-played', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ song_id: songId })
        }).then(res => res.json()).then(data => {
          this.hasLoggedPlay = true;
        }).catch(err => console.error("Play log error:", err));
      }
    }, 5000);
  }

  updateMediaSession(song) {
    if ('mediaSession' in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: song.title,
        artist: song.artist,
        album: song.album || 'Vibe Vault',
        artwork: [
          { src: `/uploads/covers/${song.cover_image || 'default_cover.png'}`, sizes: '512x512', type: 'image/png' }
        ]
      });

      navigator.mediaSession.setActionHandler('play', () => this.togglePlay());
      navigator.mediaSession.setActionHandler('pause', () => this.togglePlay());
      navigator.mediaSession.setActionHandler('previoustrack', () => this.prev());
      navigator.mediaSession.setActionHandler('nexttrack', () => this.next());
    }
  }

  highlightActiveInDOM() {
    const currentSong = this.getCurrentSong();
    if (!currentSong) return;

    document.querySelectorAll('[data-song-id]').forEach(el => {
      const id = parseInt(el.dataset.songId);
      const isCurrent = id === currentSong.id;
      
      // Update row active state
      if (el.classList.contains('song-row')) {
        el.classList.toggle('active-track', isCurrent);
        const eq = el.querySelector('.song-index-col');
        if (eq) {
          if (isCurrent && this.isPlaying) {
            eq.innerHTML = '<div class="equalizer"><div class="equalizer-bar"></div><div class="equalizer-bar"></div><div class="equalizer-bar"></div></div>';
          } else {
            eq.textContent = el.dataset.index || '▶';
          }
        }
      }
    });
  }

  shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  saveState() {
    try {
      const state = {
        queue: this.queue,
        originalQueue: this.originalQueue,
        currentIndex: this.currentIndex,
        volume: this.volume,
        isShuffle: this.isShuffle,
        repeatMode: this.repeatMode
      };
      sessionStorage.setItem('vibevault_player_state', JSON.stringify(state));
    } catch (e) {
      console.warn("Storage quota exceeded", e);
    }
  }

  restoreState() {
    try {
      const stateStr = sessionStorage.getItem('vibevault_player_state');
      if (stateStr) {
        const state = JSON.parse(stateStr);
        this.queue = state.queue || [];
        this.originalQueue = state.originalQueue || [];
        this.currentIndex = state.currentIndex || 0;
        this.volume = state.volume !== undefined ? state.volume : 0.8;
        this.isShuffle = !!state.isShuffle;
        this.repeatMode = state.repeatMode || 'none';

        if (this.queue.length > 0 && this.currentIndex >= 0 && this.currentIndex < this.queue.length) {
          const song = this.queue[this.currentIndex];
          this.loadAudioSource(song);
          this.updateUI(song);
        }
        this.setVolume(this.volume);
      }
    } catch (e) {
      console.warn("Could not restore player state:", e);
    }
  }
}

// Global initialization
document.addEventListener('DOMContentLoaded', () => {
  window.VibePlayer = new VibeVaultPlayer();
});
