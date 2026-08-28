import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import mutagen
try:
    import filetype
except ImportError:
    filetype = None

from database.db import query_db
from routes.auth import login_required
from config import Config

songs_bp = Blueprint('songs', __name__)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def is_valid_audio_file(file_obj, filename):
    """Check both extension and MIME/magic bytes for audio files."""
    if not allowed_file(filename, Config.ALLOWED_AUDIO_EXTENSIONS):
        return False
    if filetype:
        header = file_obj.read(512)
        file_obj.seek(0)
        kind = filetype.guess(header)
        if kind is not None:
            mime = kind.mime.lower()
            if not (mime.startswith('audio/') or mime.startswith('video/')):
                return False
    return True

def is_valid_image_file(file_obj, filename):
    """Check both extension and MIME/magic bytes for image files."""
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

def get_audio_duration(file_path):
    """Attempt to extract audio duration in seconds using mutagen."""
    try:
        audio = mutagen.File(file_path)
        if audio and audio.info and hasattr(audio.info, 'length'):
            return int(round(audio.info.length))
    except Exception as e:
        print(f"[Mutagen Notice] Duration extraction info: {e}")
    return 0

@songs_bp.route('/music')
@login_required
def my_music():
    user_id = session['user_id']
    genres = query_db(
        "SELECT DISTINCT genre FROM songs WHERE user_id = %s AND genre IS NOT NULL AND genre != '' ORDER BY genre ASC",
        (user_id,)
    )
    return render_template('music.html', genres=genres)

@songs_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_page():
    if request.method == 'POST':
        user_id = session['user_id']
        
        # Audio File validation
        if 'audio_file' not in request.files:
            flash('No audio file provided.', 'danger')
            return redirect(request.url)
            
        audio = request.files['audio_file']
        if not audio or audio.filename == '' or not is_valid_audio_file(audio, audio.filename):
            flash('Please upload a valid audio file (.mp3, .wav, .ogg, .m4a).', 'danger')
            return redirect(request.url)
            
        # Metadata inputs
        title = request.form.get('title', '').strip()
        if not title:
            title = os.path.splitext(audio.filename)[0].replace('_', ' ').replace('-', ' ').title()
            
        artist = request.form.get('artist', '').strip() or 'Unknown Artist'
        album = request.form.get('album', '').strip() or 'Single'
        genre = request.form.get('genre', '').strip() or 'Various'
        duration_input = request.form.get('duration', '').strip()
        
        # Secure filename & save audio
        unique_audio_name = f"{uuid.uuid4().hex}_{secure_filename(audio.filename)}"
        audio_save_path = os.path.join(Config.SONGS_FOLDER, unique_audio_name)
        os.makedirs(Config.SONGS_FOLDER, exist_ok=True)
        audio.save(audio_save_path)
        
        # Determine duration
        duration = 0
        if duration_input and duration_input.isdigit():
            duration = int(duration_input)
        else:
            duration = get_audio_duration(audio_save_path)
            
        # Cover Image processing (optional)
        cover_filename = 'default_cover.png'
        if 'cover_image' in request.files:
            cover = request.files['cover_image']
            if cover and cover.filename != '' and is_valid_image_file(cover, cover.filename):
                unique_cover_name = f"{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
                cover_save_path = os.path.join(Config.COVERS_FOLDER, unique_cover_name)
                os.makedirs(Config.COVERS_FOLDER, exist_ok=True)
                cover.save(cover_save_path)
                cover_filename = unique_cover_name
                
        # Insert into Database
        query_db(
            """INSERT INTO songs (user_id, title, artist, album, genre, audio_file, cover_image, duration)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, title, artist, album, genre, unique_audio_name, cover_filename, duration),
            commit=True
        )
        
        flash(f'Song "{title}" uploaded successfully!', 'success')
        return redirect(url_for('songs.my_music'))

    return render_template('upload.html')

# ==================== REST API ENDPOINTS ====================

@songs_bp.route('/api/songs', methods=['GET'])
@login_required
def get_songs_api():
    """Fetch user's songs with filtering, search, and sorting."""
    user_id = session['user_id']
    query = request.args.get('q', '').strip()
    genre = request.args.get('genre', '').strip()
    sort_by = request.args.get('sort', 'recent')
    order = request.args.get('order', 'desc').lower()
    
    order_dir = 'ASC' if order == 'asc' else 'DESC'
    
    sort_map = {
        'recent': f'upload_date {order_dir}',
        'title': f'title {order_dir}',
        'artist': f'artist {order_dir}',
        'plays': f'play_count {order_dir}',
        'duration': f'duration {order_dir}'
    }
    order_clause = sort_map.get(sort_by, 'upload_date DESC')
    
    sql = """
        SELECT s.*, 
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
        FROM songs s
        LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
        WHERE s.user_id = %s
    """
    params = [user_id, user_id]
    
    if query:
        sql += " AND (s.title LIKE %s OR s.artist LIKE %s OR s.album LIKE %s OR s.genre LIKE %s)"
        search_pattern = f"%{query}%"
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
        
    if genre and genre.lower() != 'all':
        sql += " AND s.genre = %s"
        params.append(genre)
        
    sql += f" ORDER BY {order_clause}"
    
    songs = query_db(sql, tuple(params))
    return jsonify({'success': True, 'songs': songs or [], 'count': len(songs or [])})

@songs_bp.route('/api/songs', methods=['POST'])
@login_required
def upload_song_api():
    """JSON/Form API endpoint to upload a song."""
    user_id = session['user_id']
    
    if 'audio_file' not in request.files:
        return jsonify({'success': False, 'message': 'Audio file is required.'}), 400
        
    audio = request.files['audio_file']
    if not audio or audio.filename == '' or not is_valid_audio_file(audio, audio.filename):
        return jsonify({'success': False, 'message': 'Invalid audio file format. Allowed: MP3, WAV, OGG, M4A.'}), 400
        
    title = request.form.get('title', '').strip()
    if not title:
        title = os.path.splitext(audio.filename)[0].replace('_', ' ').replace('-', ' ').title()
        
    artist = request.form.get('artist', '').strip() or 'Unknown Artist'
    album = request.form.get('album', '').strip() or 'Single'
    genre = request.form.get('genre', '').strip() or 'Various'
    duration_input = request.form.get('duration', '').strip()
    
    unique_audio_name = f"{uuid.uuid4().hex}_{secure_filename(audio.filename)}"
    audio_save_path = os.path.join(Config.SONGS_FOLDER, unique_audio_name)
    os.makedirs(Config.SONGS_FOLDER, exist_ok=True)
    audio.save(audio_save_path)
    
    duration = 0
    if duration_input and duration_input.isdigit():
        duration = int(duration_input)
    else:
        duration = get_audio_duration(audio_save_path)
        
    cover_filename = 'default_cover.png'
    if 'cover_image' in request.files:
        cover = request.files['cover_image']
        if cover and cover.filename != '' and is_valid_image_file(cover, cover.filename):
            unique_cover_name = f"{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
            cover_save_path = os.path.join(Config.COVERS_FOLDER, unique_cover_name)
            os.makedirs(Config.COVERS_FOLDER, exist_ok=True)
            cover.save(cover_save_path)
            cover_filename = unique_cover_name
            
    song_id = query_db(
        """INSERT INTO songs (user_id, title, artist, album, genre, audio_file, cover_image, duration)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (user_id, title, artist, album, genre, unique_audio_name, cover_filename, duration),
        commit=True
    )
    
    song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    return jsonify({'success': True, 'message': 'Song uploaded successfully!', 'song': song}), 201

@songs_bp.route('/api/songs/<int:song_id>', methods=['GET'])
@login_required
def get_song_detail_api(song_id):
    user_id = session['user_id']
    song = query_db(
        """SELECT s.*, CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
           FROM songs s
           LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
           WHERE s.id = %s AND s.user_id = %s""",
        (user_id, song_id, user_id),
        one=True
    )
    if not song:
        return jsonify({'success': False, 'message': 'Song not found or unauthorized.'}), 404
    return jsonify({'success': True, 'song': song})

@songs_bp.route('/api/songs/<int:song_id>', methods=['PUT'])
@login_required
def update_song_api(song_id):
    user_id = session['user_id']
    song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    if not song:
        return jsonify({'success': False, 'message': 'Song not found or unauthorized.'}), 404
        
    data = request.form if request.form else (request.get_json() or {})
    title = data.get('title', song['title']).strip()
    artist = data.get('artist', song['artist']).strip()
    album = data.get('album', song['album']).strip()
    genre = data.get('genre', song['genre']).strip()
    
    if not title:
        return jsonify({'success': False, 'message': 'Song title cannot be empty.'}), 400
        
    cover_filename = song['cover_image']
    if 'cover_image' in request.files:
        cover = request.files['cover_image']
        if cover and cover.filename != '' and is_valid_image_file(cover, cover.filename):
            unique_cover_name = f"{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
            cover_save_path = os.path.join(Config.COVERS_FOLDER, unique_cover_name)
            os.makedirs(Config.COVERS_FOLDER, exist_ok=True)
            cover.save(cover_save_path)
            
            if song['cover_image'] and song['cover_image'] != 'default_cover.png':
                old_path = os.path.join(Config.COVERS_FOLDER, song['cover_image'])
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            cover_filename = unique_cover_name
            
    query_db(
        "UPDATE songs SET title = %s, artist = %s, album = %s, genre = %s, cover_image = %s WHERE id = %s AND user_id = %s",
        (title, artist, album, genre, cover_filename, song_id, user_id),
        commit=True
    )
    
    updated_song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    return jsonify({'success': True, 'message': 'Song updated successfully!', 'song': updated_song})

@songs_bp.route('/api/songs/<int:song_id>', methods=['DELETE'])
@login_required
def delete_song_api(song_id):
    user_id = session['user_id']
    song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    if not song:
        return jsonify({'success': False, 'message': 'Song not found or unauthorized.'}), 404
        
    audio_path = os.path.join(Config.SONGS_FOLDER, song['audio_file'])
    if os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except Exception as e:
            print(f"[File removal notice] {e}")
            
    if song['cover_image'] and song['cover_image'] != 'default_cover.png':
        cover_path = os.path.join(Config.COVERS_FOLDER, song['cover_image'])
        if os.path.exists(cover_path):
            try:
                os.remove(cover_path)
            except Exception:
                pass
                
    query_db("DELETE FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), commit=True)
    return jsonify({'success': True, 'message': f'Song "{song["title"]}" deleted successfully.'})
