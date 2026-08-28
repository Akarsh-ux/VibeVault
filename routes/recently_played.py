from flask import Blueprint, render_template, request, session, jsonify
from database.db import query_db
from routes.auth import login_required

recently_played_bp = Blueprint('recently_played', __name__)

@recently_played_bp.route('/recently-played')
@login_required
def recently_played_page():
    return render_template('recently_played.html')

@recently_played_bp.route('/api/recently-played', methods=['GET'])
@login_required
def get_recently_played_api():
    """Retrieve recently played songs for current user with relative timestamps."""
    user_id = session['user_id']
    try:
        limit = int(request.args.get('limit', 50))
        limit = max(1, min(limit, 100))
    except (ValueError, TypeError):
        limit = 50
    
    songs = query_db(
        """SELECT s.*, rp.played_at, rp.id as history_id,
                  CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
           FROM recently_played rp
           JOIN songs s ON rp.song_id = s.id
           LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
           WHERE rp.user_id = %s
           ORDER BY rp.played_at DESC
           LIMIT %s""",
        (user_id, user_id, limit)
    )
    return jsonify({'success': True, 'songs': songs or [], 'count': len(songs or [])})

@recently_played_bp.route('/api/recently-played', methods=['POST'])
@login_required
def record_play_api():
    """Record a song playback event, increment play count, and update history."""
    user_id = session['user_id']
    data = request.get_json() or request.form
    song_id = data.get('song_id')
    
    if not song_id:
        return jsonify({'success': False, 'message': 'Song ID required.'}), 400
        
    song = query_db("SELECT * FROM songs WHERE id = %s AND user_id = %s", (song_id, user_id), one=True)
    if not song:
        return jsonify({'success': False, 'message': 'Song not found.'}), 404
        
    # Increment play count on song
    query_db("UPDATE songs SET play_count = play_count + 1 WHERE id = %s", (song_id,), commit=True)
    
    # Check if this song was already recorded in recently_played for this user
    existing = query_db(
        "SELECT id FROM recently_played WHERE user_id = %s AND song_id = %s ORDER BY played_at DESC",
        (user_id, song_id),
        one=True
    )
    
    if existing:
        query_db(
            "UPDATE recently_played SET played_at = CURRENT_TIMESTAMP WHERE id = %s",
            (existing['id'],),
            commit=True
        )
    else:
        query_db(
            "INSERT INTO recently_played (user_id, song_id, played_at) VALUES (%s, %s, CURRENT_TIMESTAMP)",
            (user_id, song_id),
            commit=True
        )
        
    updated_song = query_db("SELECT play_count FROM songs WHERE id = %s", (song_id,), one=True)
    return jsonify({'success': True, 'play_count': updated_song['play_count'] if updated_song else 1})

@recently_played_bp.route('/api/recently-played/clear', methods=['POST'])
@login_required
def clear_history_api():
    """Clear playback history for the logged in user."""
    user_id = session['user_id']
    query_db("DELETE FROM recently_played WHERE user_id = %s", (user_id,), commit=True)
    return jsonify({'success': True, 'message': 'Listening history cleared.'})
