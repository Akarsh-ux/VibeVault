import re
from functools import wraps
from urllib.parse import urlparse
# pyrefly: ignore [missing-import]
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import query_db

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator to require login on protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False,
                                'message': 'Authentication required. Please log in.'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def _safe_next_url(next_url):
    """
    Validate that the next URL is a relative path (same-origin) only.
    Prevents open-redirect attacks.
    """
    if not next_url:
        return None
    parsed = urlparse(next_url)
    # Allow only relative URLs (no scheme, no netloc)
    if parsed.scheme or parsed.netloc:
        return None
    return next_url


def get_current_user():
    """Retrieve full current user record from database."""
    if 'user_id' not in session:
        return None
    return query_db(
        "SELECT id, full_name, username, email, profile_image, created_at "
        "FROM users WHERE id = %s",
        (session['user_id'],),
        one=True
    )


@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/api/register', methods=['POST'])
def register():
    if request.method == 'GET' and 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Support both form data and JSON
        data = request.get_json() if request.is_json else request.form
        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip().lower()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        # Validation
        errors = []
        if not full_name:
            errors.append('Full Name is required.')
        if not username or len(username) < 3 or not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('Username must be at least 3 characters (letters, numbers, underscores).')
        if not email or not re.match(
                r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append('A valid email address is required.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': errors[0], 'errors': errors}), 400
            for err in errors:
                flash(err, 'danger')
            return render_template('register.html', full_name=full_name,
                                   username=username, email=email)

        # Check for existing username / email
        existing_user = query_db(
            "SELECT id, username, email FROM users WHERE username = %s OR email = %s",
            (username, email), one=True
        )
        if existing_user:
            msg = ('Username already taken.'
                   if existing_user.get('username') == username
                   else 'Email address is already registered.')
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': msg}), 409
            flash(msg, 'danger')
            return render_template('register.html', full_name=full_name,
                                   username=username, email=email)

        # Hash password using PBKDF2-SHA256
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        try:
            user_id = query_db(
                "INSERT INTO users (full_name, username, email, password_hash, profile_image) "
                "VALUES (%s, %s, %s, %s, %s)",
                (full_name, username, email, password_hash, 'default_avatar.png'),
                commit=True
            )
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': True,
                    'message': 'Account created successfully! Please log in.',
                    'user_id': user_id,
                    'redirect': url_for('auth.login')
                }), 201
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            msg = 'An error occurred while creating your account. Please try again.'
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': msg}), 500
            flash(msg, 'danger')
            return render_template('register.html', full_name=full_name,
                                   username=username, email=email)

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/api/login', methods=['POST'])
def login():
    if request.method == 'GET' and 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        login_input = data.get('login_input', '').strip().lower()
        password = data.get('password', '')
        remember = bool(data.get('remember'))

        if not login_input or not password:
            msg = 'Please enter both username/email and password.'
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': msg}), 400
            flash(msg, 'danger')
            return render_template('login.html', login_input=login_input)

        user = query_db(
            "SELECT id, full_name, username, email, password_hash, profile_image "
            "FROM users WHERE username = %s OR email = %s",
            (login_input, login_input),
            one=True
        )

        if user and check_password_hash(user['password_hash'], password):
            # SECURITY: Clear old session before setting new identity (session fixation protection)
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['profile_image'] = user.get('profile_image') or 'default_avatar.png'

            if remember:
                session.permanent = True

            # SECURITY: Validate next URL to prevent open redirect
            raw_next = request.args.get('next') or data.get('next')
            next_url = _safe_next_url(raw_next) or url_for('main.dashboard')

            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': True,
                    'message': 'Logged in successfully!',
                    'redirect': next_url,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user['full_name']
                    }
                })
            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(next_url)
        else:
            msg = 'Invalid username/email or password.'
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': msg}), 401
            flash(msg, 'danger')
            return render_template('login.html', login_input=login_input)

    return render_template('login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': True, 'message': 'Logged out successfully.',
                        'redirect': url_for('auth.login')})
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
        user = get_current_user()
        return jsonify({
            'authenticated': True,
            'user': {
                'id': user['id'],
                'full_name': user['full_name'],
                'username': user['username'],
                'email': user['email'],
                'profile_image': user['profile_image']
            }
        })
    return jsonify({'authenticated': False})


