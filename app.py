import os
from flask import Flask, render_template, send_from_directory, jsonify, request, session, abort
from config import Config
from database.db import init_db, query_db
from routes.auth import auth_bp
from routes.songs import songs_bp
from routes.playlists import playlists_bp
from routes.favorites import favorites_bp
from routes.recently_played import recently_played_bp
from routes.users import users_bp
from routes.search import search_bp
from routes.main import main_bp
from routes.csrf import generate_csrf_token


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directories exist
    os.makedirs(Config.SONGS_FOLDER, exist_ok=True)
    os.makedirs(Config.COVERS_FOLDER, exist_ok=True)
    os.makedirs(Config.PROFILES_FOLDER, exist_ok=True)

    # Initialize Database
    try:
        init_db()
    except Exception as e:
        print(f"[VibeVault DB Init Error]: {e}")

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(songs_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(recently_played_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(search_bp)

    # ----------------------------------------------------------------
    # SECURITY: Authenticated audio streaming endpoint.
    # Audio files are NEVER served publicly. Only the owning user
    # (verified via session) can stream their own audio files.
    # ----------------------------------------------------------------
    @app.route('/api/stream/<int:song_id>')
    def stream_song(song_id):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required.'}), 401

        song = query_db(
            "SELECT audio_file FROM songs WHERE id = %s AND user_id = %s",
            (song_id, session['user_id']),
            one=True
        )
        if not song:
            abort(404)

        # Prevent path traversal: only serve the bare filename, not any path component
        filename = os.path.basename(song['audio_file'])
        return send_from_directory(Config.SONGS_FOLDER, filename)

    # Cover images and profile avatars remain publicly accessible
    # (they are images, not private audio content)
    @app.route('/uploads/covers/<path:filename>')
    def serve_cover(filename):
        safe_name = os.path.basename(filename)
        cover_path = os.path.join(Config.COVERS_FOLDER, safe_name)
        if not os.path.exists(cover_path):
            return send_from_directory(
                os.path.join(Config.BASE_DIR, 'static', 'images'), 'default_cover.png'
            )
        return send_from_directory(Config.COVERS_FOLDER, safe_name)

    @app.route('/uploads/profiles/<path:filename>')
    def serve_profile(filename):
        safe_name = os.path.basename(filename)
        profile_path = os.path.join(Config.PROFILES_FOLDER, safe_name)
        if not os.path.exists(profile_path):
            return send_from_directory(
                os.path.join(Config.BASE_DIR, 'static', 'images'), 'default_avatar.png'
            )
        return send_from_directory(Config.PROFILES_FOLDER, safe_name)

    # ----------------------------------------------------------------
    # SECURITY: Add HTTP security headers to every response
    # ----------------------------------------------------------------
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # ----------------------------------------------------------------
    # Template Context Processor (Global template variables)
    # ----------------------------------------------------------------
    @app.context_processor
    def inject_global_data():
        current_user = None
        if 'user_id' in session:
            current_user = query_db(
                "SELECT id, full_name, username, email, profile_image FROM users WHERE id = %s",
                (session['user_id'],),
                one=True
            )
        return {
            'current_user': current_user,
            'is_authenticated': 'user_id' in session,
            'csrf_token': generate_csrf_token
        }

    # Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Bad Request.'}), 400
        return render_template('base.html', error_title='400 - Bad Request',
                               error_msg='Invalid request parameters.'), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Unauthorized access.'}), 401
        return render_template('base.html', error_title='401 - Unauthorized',
                               error_msg='Please log in to access this page.'), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Access forbidden.'}), 403
        return render_template('base.html', error_title='403 - Forbidden',
                               error_msg='You do not have permission to access this resource.'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Resource not found.'}), 404
        return render_template('base.html', error_title='404 - Page Not Found',
                               error_msg='The page or resource you requested could not be found.'), 404

    @app.errorhandler(413)
    def file_too_large(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'File size is too large (max 60MB).'}), 413
        return render_template('base.html', error_title='413 - File Too Large',
                               error_msg='The uploaded file exceeds the 60MB limit.'), 413

    @app.errorhandler(500)
    def internal_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Internal server error. Please try again later.'}), 500
        return render_template('base.html', error_title='500 - Server Error',
                               error_msg='An unexpected error occurred. Please try again.'), 500

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() in ('true', '1')
    print(f"[VibeVault] Starting server on http://0.0.0.0:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=debug)

