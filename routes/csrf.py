"""
Lightweight CSRF protection using HMAC + session secret.
No Flask-WTF dependency required.
"""
import hmac
import hashlib
import secrets
import os
from functools import wraps
from flask import session, request, jsonify, abort, current_app


def generate_csrf_token():
    """Generate and store a CSRF token in the session."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']


def validate_csrf_token():
    """
    Validate CSRF token from request header or form field.
    Returns True if valid, False otherwise.
    """
    token_in_session = session.get('csrf_token')
    if not token_in_session:
        return False

    # Check header first (for AJAX), then fall back to form field
    token_from_request = (
        request.headers.get('X-CSRF-Token')
        or request.form.get('csrf_token')
        or (request.get_json(silent=True) or {}).get('csrf_token')
    )

    if not token_from_request:
        return False

    # Use hmac.compare_digest to prevent timing attacks
    return hmac.compare_digest(token_in_session, token_from_request)


def csrf_required(f):
    """Decorator to enforce CSRF validation on state-changing endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_app.config.get('TESTING'):
            return f(*args, **kwargs)
        # Only check for state-changing methods
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            if not validate_csrf_token():
                if request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'message': 'CSRF token missing or invalid. Please refresh the page.'
                    }), 403
                abort(403)
        return f(*args, **kwargs)
    return decorated

