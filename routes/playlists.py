import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
try:
    import filetype
except ImportError:
    filetype = None

from database.db import query_db
from routes.auth import login_required
from config import Config

playlists_bp = Blueprint('playlists', __name__)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def is_valid_image_file(file_obj, filename):
    if not allowed_file(filename, Config.ALLOWED_IMAGE_EXTENSIONS):
        return False
    if filetype:
        header = file_obj.read(512)
        file_obj.seek(0)
        kind = filetype.guess(header)
        if kind is not None:
            mime = kind.mime.lower()
            if not mime.startswith('image/'):
                return False
    return True

@playlists_bp.route('/playlists')
@login_required
def playlists_page():
    return render_template('playlists.html')

@playlists_bp.route('/playlist/<int:playlist_id>')
@login_required
def playlist_detail_page(playlist_id):
    user_id = session['user_id']
    playlist = query_db(
        "SELECT * FROM playlists WHERE id = %s AND user_id = %s",
        (playlist_id, user_id),
        one=True
    )
    if not playlist:
        flash('Playlist not found.', 'danger')
        return redirect(url_for('playlists.playlists_page'))
    return render_template('playlist.html', playlist=playlist)

# ==================== REST API ENDPOINTS ====================

@playlists_bp.route('/api/playlists', methods=['GET'])
@login_required
def get_playlists_api():
    """Retrieve all playlists belonging to current user with song count (ONLY_FULL_GROUP_BY safe)."""
    user_id = session['user_id']
    playlists = query_db(
        """SELECT p.id, p.user_id, p.name, p.description, p.cover_image, p.created_at,
                  COUNT(ps.song_id) as song_count,
                  COALESCE(SUM(s.duration), 0) as total_duration
           FROM playlists p
           LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
           LEFT JOIN songs s ON ps.song_id = s.id
           WHERE p.user_id = %s
           GROUP BY p.id, p.user_id, p.name, p.description, p.cover_image, p.created_at
           ORDER BY p.created_at DESC""",
        (user_id,)
    )
    return jsonify({'success': True, 'playlists': playlists or []})

@playlists_bp.route('/api/playlists', methods=['POST'])
@login_required
def create_playlist_api():
    """Create a new playlist."""
    user_id = session['user_id']
    data = request.form if request.form else (request.get_json() or {})
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': 'Playlist name is required.'}), 400
        
    cover_filename = 'default_playlist.png'
    if 'cover_image' in request.files:
        cover = request.files['cover_image']
        if cover and cover.filename != '' and is_valid_image_file(cover, cover.filename):
            unique_cover_name = f"{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
            cover_save_path = os.path.join(Config.COVERS_FOLDER, unique_cover_name)
            os.makedirs(Config.COVERS_FOLDER, exist_ok=True)
            cover.save(cover_save_path)
            cover_filename = unique_cover_name
            
    playlist_id = query_db(
        "INSERT INTO playlists (user_id, name, description, cover_image) VALUES (%s, %s, %s, %s)",
        (user_id, name, description, cover_filename),
        commit=True
    )
    
    new_playlist = query_db(
        "SELECT id, user_id, name, description, cover_image, created_at, 0 as song_count, 0 as total_duration FROM playlists WHERE id = %s AND user_id = %s",
        (playlist_id, user_id),
        one=True
    )
    return jsonify({'success': True, 'message': 'Playlist created successfully!', 'playlist': new_playlist}), 201

@playlists_bp.route('/api/playlists/<int:playlist_id>', methods=['GET'])
@login_required
def get_single_playlist_api(playlist_id):
    """Get detailed info and list of songs for a playlist."""
    user_id = session['user_id']
    playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist not found or unauthorized.'}), 404
        
    songs = query_db(
        """SELECT s.*, ps.position, ps.added_at as in_playlist_since,
                  CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
           FROM playlist_songs ps
           JOIN songs s ON ps.song_id = s.id
           LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
           WHERE ps.playlist_id = %s
           ORDER BY ps.position ASC, ps.added_at ASC""",
        (user_id, playlist_id)
    )
    
    total_duration = sum((song.get('duration') or 0) for song in (songs or []))
    
    return jsonify({
        'success': True,
        'playlist': playlist,
        'songs': songs or [],
        'song_count': len(songs or []),
        'total_duration': total_duration
    })

@playlists_bp.route('/api/playlists/<int:playlist_id>', methods=['PUT'])
@login_required
def update_playlist_api(playlist_id):
    """Update playlist name, description, or cover."""
    user_id = session['user_id']
    playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist not found or unauthorized.'}), 404
        
    data = request.form if request.form else (request.get_json() or {})
    name = data.get('name', playlist['name']).strip()
    description = data.get('description', playlist['description']).strip()
    
    if not name:
        return jsonify({'success': False, 'message': 'Playlist name cannot be empty.'}), 400
        
    cover_filename = playlist['cover_image']
    if 'cover_image' in request.files:
        cover = request.files['cover_image']
        if cover and cover.filename != '' and is_valid_image_file(cover, cover.filename):
            unique_cover_name = f"{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
            cover_save_path = os.path.join(Config.COVERS_FOLDER, unique_cover_name)
            os.makedirs(Config.COVERS_FOLDER, exist_ok=True)
            cover.save(cover_save_path)
            
            if playlist['cover_image'] and playlist['cover_image'] != 'default_playlist.png':
                old_path = os.path.join(Config.COVERS_FOLDER, playlist['cover_image'])
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            cover_filename = unique_cover_name
            
    query_db(
        "UPDATE playlists SET name = %s, description = %s, cover_image = %s WHERE id = %s AND user_id = %s",
        (name, description, cover_filename, playlist_id, user_id),
        commit=True
    )
    
    updated_playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    return jsonify({'success': True, 'message': 'Playlist updated successfully!', 'playlist': updated_playlist})

@playlists_bp.route('/api/playlists/<int:playlist_id>', methods=['DELETE'])
@login_required
def delete_playlist_api(playlist_id):
    """Delete playlist and associated songs relations."""
    user_id = session['user_id']
    playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist not found or unauthorized.'}), 404
        
    if playlist['cover_image'] and playlist['cover_image'] != 'default_playlist.png':
        cover_path = os.path.join(Config.COVERS_FOLDER, playlist['cover_image'])
        if os.path.exists(cover_path):
            try:
                os.remove(cover_path)
            except Exception:
                pass
                
    query_db("DELETE FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), commit=True)
    return jsonify({'success': True, 'message': f'Playlist "{playlist["name"]}" deleted successfully.'})

@playlists_bp.route('/api/playlists/<int:playlist_id>/songs', methods=['POST'])
@login_required
def add_song_to_playlist_api(playlist_id):
    """Add a song to a playlist with duplicate prevention."""
    user_id = session['user_id']
    playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist not found or unauthorized.'}), 404
        
    data = request.get_json() or request.form
    song_id = data.get('song_id')
    if not song_id:
        return jsonify({'success': False, 'message': 'Song ID is required.'}), 400
        
    song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    if not song:
        return jsonify({'success': False, 'message': 'Song not found or unauthorized.'}), 404
        
    existing = query_db(
        "SELECT id FROM playlist_songs WHERE playlist_id = %s AND song_id = %s",
        (playlist_id, song_id),
        one=True
    )
    if existing:
        return jsonify({'success': False, 'message': f'"{song["title"]}" is already in this playlist.'}), 409
        
    pos_res = query_db("SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM playlist_songs WHERE playlist_id = %s", (playlist_id,), one=True)
    next_pos = pos_res['next_pos'] if pos_res else 1
    
    query_db(
        "INSERT INTO playlist_songs (playlist_id, song_id, position) VALUES (%s, %s, %s)",
        (playlist_id, song_id, next_pos),
        commit=True
    )
    
    return jsonify({'success': True, 'message': f'Added "{song["title"]}" to "{playlist["name"]}".'})

@playlists_bp.route('/api/playlists/<int:playlist_id>/songs/<int:song_id>', methods=['DELETE'])
@login_required
def remove_song_from_playlist_api(playlist_id, song_id):
    """Remove a song from a playlist."""
    user_id = session['user_id']
    playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist not found or unauthorized.'}), 404
        
    query_db(
        "DELETE FROM playlist_songs WHERE playlist_id = %s AND song_id = %s",
        (playlist_id, song_id),
        commit=True
    )
    return jsonify({'success': True, 'message': 'Song removed from playlist.'})

@playlists_bp.route('/api/playlists/<int:playlist_id>/reorder', methods=['PUT'])
@login_required
def reorder_playlist_songs_api(playlist_id):
    """Reorder songs in a playlist after validating song IDs."""
    user_id = session['user_id']
    playlist = query_db("SELECT * FROM playlists WHERE id = %s AND user_id = %s", (playlist_id, user_id), one=True)
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist not found or unauthorized.'}), 404
        
    data = request.get_json() or {}
    song_ids = data.get('song_ids', [])
    
    # Validation: Ensure all given song_ids actually belong to this playlist
    existing_entries = query_db("SELECT song_id FROM playlist_songs WHERE playlist_id = %s", (playlist_id,))
    valid_song_ids = {row['song_id'] for row in (existing_entries or [])}
    
    for position, song_id in enumerate(song_ids, start=1):
        if song_id in valid_song_ids:
            query_db(
                "UPDATE playlist_songs SET position = %s WHERE playlist_id = %s AND song_id = %s",
                (position, playlist_id, song_id),
                commit=True
            )
        
    return jsonify({'success': True, 'message': 'Playlist order saved successfully.'})

@playlists_bp.route('/api/user/playlists-for-song/<int:song_id>', methods=['GET'])
@login_required
def get_user_playlists_for_song(song_id):
    """Returns list of user's playlists with a boolean indicating if the given song is in that playlist."""
    user_id = session['user_id']
    playlists = query_db(
        """SELECT p.id, p.name, p.cover_image,
                  CASE WHEN ps.id IS NOT NULL THEN 1 ELSE 0 END as contains_song
           FROM playlists p
           LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id AND ps.song_id = %s
           WHERE p.user_id = %s
           ORDER BY p.name ASC""",
        (song_id, user_id)
    )
    return jsonify({'success': True, 'playlists': playlists or []})
