from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from database.db import query_db
from routes.auth import login_required, get_current_user
from routes.users import get_user_stats

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def landing_page():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = get_current_user()
    stats = get_user_stats(user_id)
    
    # 1. Recently Played Songs (up to 8)
    recently_played = query_db(
        """SELECT s.*, rp.played_at,
                  CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
           FROM recently_played rp
           JOIN songs s ON rp.song_id = s.id
           LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
           WHERE rp.user_id = %s
           ORDER BY rp.played_at DESC
           LIMIT 8""",
        (user_id, user_id)
    )
    
    # 2. My Playlists (up to 6) - ONLY_FULL_GROUP_BY safe
    playlists = query_db(
        """SELECT p.id, p.user_id, p.name, p.description, p.cover_image, p.created_at,
                  COUNT(ps.song_id) as song_count
           FROM playlists p
           LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
           WHERE p.user_id = %s
           GROUP BY p.id, p.user_id, p.name, p.description, p.cover_image, p.created_at
           ORDER BY p.created_at DESC
           LIMIT 6""",
        (user_id,)
    )
    
    # 3. Recently Added Songs (up to 6)
    recently_added = query_db(
        """SELECT s.*, 
                  CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
           FROM songs s
           LEFT JOIN favorites f ON s.id = f.song_id AND f.user_id = %s
           WHERE s.user_id = %s
           ORDER BY s.upload_date DESC
           LIMIT 6""",
        (user_id, user_id)
    )
    
    # 4. Favorites (up to 6)
    favorites = query_db(
        """SELECT s.*, 1 as is_favorite
           FROM favorites f
           JOIN songs s ON f.song_id = s.id
           WHERE f.user_id = %s
           ORDER BY f.created_at DESC
           LIMIT 6""",
        (user_id,)
    )
    
    return render_template(
        'dashboard.html',
        user=user,
        stats=stats,
        recently_played=recently_played or [],
        playlists=playlists or [],
        recently_added=recently_added or [],
        favorites=favorites or []
    )

@main_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats_api():
    user_id = session['user_id']
    stats = get_user_stats(user_id)
    return jsonify({'success': True, 'stats': stats})
