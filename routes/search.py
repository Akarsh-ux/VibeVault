from flask import Blueprint, request, session, jsonify
from database.db import query_db
from routes.auth import login_required

search_bp = Blueprint('search', __name__)

@search_bp.route('/api/search', methods=['GET'])
@login_required
def search_api():
    """Global dynamic search across songs, artists, albums, genres, and playlists."""
    user_id = session['user_id']
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'success': True, 'results': {'songs': [], 'playlists': []}})
        
    pattern = f"%{query}%"
    
    # Search songs
    songs = query_db(
        """SELECT s.*, 
                  CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
           FROM songs s
           LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
           WHERE s.user_id = %s AND (
               s.title LIKE %s OR 
               s.artist LIKE %s OR 
               s.album LIKE %s OR 
               s.genre LIKE %s
           )
           ORDER BY s.play_count DESC, s.upload_date DESC
           LIMIT 20""",
        (user_id, user_id, pattern, pattern, pattern, pattern)
    )
    
    # Search playlists - ONLY_FULL_GROUP_BY safe
    playlists = query_db(
        """SELECT p.id, p.user_id, p.name, p.description, p.cover_image, p.created_at,
                  COUNT(ps.song_id) as song_count
           FROM playlists p
           LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
           WHERE p.user_id = %s AND (
               p.name LIKE %s OR 
               p.description LIKE %s
           )
           GROUP BY p.id, p.user_id, p.name, p.description, p.cover_image, p.created_at
           ORDER BY p.name ASC
           LIMIT 10""",
        (user_id, pattern, pattern)
    )
    
    return jsonify({
        'success': True,
        'query': query,
        'results': {
            'songs': songs or [],
            'playlists': playlists or []
        }
    })
