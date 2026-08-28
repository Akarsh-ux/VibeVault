from flask import Blueprint, render_template, request, session, jsonify
from database.db import query_db
from routes.auth import login_required
from routes.csrf import csrf_required

favorites_bp = Blueprint('favorites', __name__)

@favorites_bp.route('/favorites')
@login_required
def favorites_page():
    return render_template('favorites.html')

@favorites_bp.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites_api():
    """Retrieve all songs favorited by the logged in user."""
    user_id = session['user_id']
    songs = query_db(
        """SELECT s.*, 1 as is_favorite, f.created_at as favorited_at
           FROM favorites f
           JOIN songs s ON f.song_id = s.id
           WHERE f.user_id = %s
           ORDER BY f.created_at DESC""",
        (user_id,)
    )
    return jsonify({'success': True, 'songs': songs or [], 'count': len(songs or [])})

@favorites_bp.route('/api/favorites/toggle/<int:song_id>', methods=['POST'])
@login_required
@csrf_required
def toggle_favorite_api(song_id):
    """Toggle favorite status for a song."""
    user_id = session['user_id']
    song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    if not song:
        return jsonify({'success': False, 'message': 'Song not found or unauthorized.'}), 404
        
    existing = query_db("SELECT id FROM favorites WHERE user_id = %s AND song_id = %s", (user_id, song_id), one=True)
    if existing:
        query_db("DELETE FROM favorites WHERE id = %s", (existing['id'],), commit=True)
        return jsonify({'success': True, 'is_favorite': False, 'message': f'Removed "{song["title"]}" from favorites.'})
    else:
        query_db("INSERT INTO favorites (user_id, song_id) VALUES (%s, %s)", (user_id, song_id), commit=True)
        return jsonify({'success': True, 'is_favorite': True, 'message': f'Added "{song["title"]}" to favorites!'})

@favorites_bp.route('/api/favorites/<int:song_id>', methods=['DELETE'])
@login_required
@csrf_required
def remove_favorite_api(song_id):
    """Remove a song from user's favorites."""
    user_id = session['user_id']
    query_db("DELETE FROM favorites WHERE user_id = %s AND song_id = %s", (user_id, song_id), commit=True)
    return jsonify({'success': True, 'is_favorite': False, 'message': 'Removed from favorites.'})
