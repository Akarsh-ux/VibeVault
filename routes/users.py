import os
import uuid
import re
from flask import Blueprint, render_template, request, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
try:
    import filetype
except ImportError:
    filetype = None

from database.db import query_db
from routes.auth import login_required, get_current_user
from config import Config

users_bp = Blueprint('users', __name__)

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

def get_user_stats(user_id):
    total_songs = query_db("SELECT COUNT(*) as c FROM songs WHERE user_id = %s", (user_id,), one=True)['c']
    total_playlists = query_db("SELECT COUNT(*) as c FROM playlists WHERE user_id = %s", (user_id,), one=True)['c']
    total_favorites = query_db("SELECT COUNT(*) as c FROM favorites WHERE user_id = %s", (user_id,), one=True)['c']
    plays_res = query_db("SELECT COALESCE(SUM(play_count), 0) as s FROM songs WHERE user_id = %s", (user_id,), one=True)['s']
    total_plays = int(plays_res) if plays_res is not None else 0
    return {
        'total_songs': total_songs,
        'total_playlists': total_playlists,
        'total_favorites': total_favorites,
        'total_plays': total_plays
    }

@users_bp.route('/profile')
@login_required
def profile_page():
    user_id = session['user_id']
    user = get_current_user()
    stats = get_user_stats(user_id)
    return render_template('profile.html', user=user, stats=stats)

@users_bp.route('/api/profile', methods=['GET'])
@login_required
def get_profile_api():
    """Retrieve full user profile and listening stats."""
    user_id = session['user_id']
    user = query_db(
        "SELECT id, full_name, username, email, profile_image, created_at FROM users WHERE id = %s",
        (user_id,),
        one=True
    )
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
        
    stats = get_user_stats(user_id)
    return jsonify({'success': True, 'user': user, 'stats': stats})

@users_bp.route('/api/profile', methods=['PUT', 'POST'])
@login_required
def update_profile_api():
    """Update user personal details (Full name, username, avatar)."""
    user_id = session['user_id']
    user = query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
        
    data = request.form if request.form else (request.get_json() or {})
    full_name = data.get('full_name', user['full_name']).strip()
    username = data.get('username', user['username']).strip().lower()
    
    if not full_name:
        return jsonify({'success': False, 'message': 'Full Name cannot be empty.'}), 400
    if not username or len(username) < 3 or not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'success': False, 'message': 'Invalid username format (min 3 chars, letters/numbers/underscore).'}), 400
        
    if username != user['username']:
        existing = query_db("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id), one=True)
        if existing:
            return jsonify({'success': False, 'message': 'Username is already in use.'}), 409
            
    profile_image = user['profile_image']
    if 'profile_image' in request.files:
        avatar = request.files['profile_image']
        if avatar and avatar.filename != '' and is_valid_image_file(avatar, avatar.filename):
            unique_avatar_name = f"{uuid.uuid4().hex}_{secure_filename(avatar.filename)}"
            avatar_save_path = os.path.join(Config.PROFILES_FOLDER, unique_avatar_name)
            os.makedirs(Config.PROFILES_FOLDER, exist_ok=True)
            avatar.save(avatar_save_path)
            
            if user['profile_image'] and user['profile_image'] != 'default_avatar.png':
                old_path = os.path.join(Config.PROFILES_FOLDER, user['profile_image'])
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            profile_image = unique_avatar_name
            
    query_db(
        "UPDATE users SET full_name = %s, username = %s, profile_image = %s WHERE id = %s",
        (full_name, username, profile_image, user_id),
        commit=True
    )
    
    session['username'] = username
    session['full_name'] = full_name
    session['profile_image'] = profile_image
    
    updated_user = query_db("SELECT id, full_name, username, email, profile_image, created_at FROM users WHERE id = %s", (user_id,), one=True)
    return jsonify({'success': True, 'message': 'Profile updated successfully!', 'user': updated_user})

@users_bp.route('/api/profile/password', methods=['PUT', 'POST'])
@login_required
def change_password_api():
    """Change password with current password verification."""
    user_id = session['user_id']
    user = query_db("SELECT password_hash FROM users WHERE id = %s", (user_id,), one=True)
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 404
        
    data = request.get_json() if request.is_json else request.form
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_new_password = data.get('confirm_new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'success': False, 'message': 'Please provide current and new password.'}), 400
        
    if not check_password_hash(user['password_hash'], current_password):
        return jsonify({'success': False, 'message': 'Current password does not match.'}), 401
        
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'New password must be at least 8 characters long.'}), 400
        
    if new_password != confirm_new_password:
        return jsonify({'success': False, 'message': 'New password confirmation does not match.'}), 400
        
    new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    query_db("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id), commit=True)
    
    return jsonify({'success': True, 'message': 'Password changed successfully!'})
