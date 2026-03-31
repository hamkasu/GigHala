"""
GigHala Mobile API
Flask Blueprint providing mobile-specific endpoints consumed by the
Capacitor Android app (X-Mobile-App: true header).

Register in app.py:
    from mobile_api import mobile_bp
    app.register_blueprint(mobile_bp)
"""

from flask import Blueprint, request, jsonify, session
from flask_login import current_user, login_required
from functools import wraps
import os
import uuid
import base64
from datetime import datetime

mobile_bp = Blueprint('mobile', __name__, url_prefix='/api/mobile')

# ── Helpers ───────────────────────────────────────────────────────────────────

def mobile_required(f):
    """Decorator: only accept requests from the mobile app."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.headers.get('X-Mobile-App'):
            return jsonify({'error': 'Mobile app only'}), 403
        return f(*args, **kwargs)
    return decorated


def allowed_image(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def get_upload_folder():
    folder = os.path.join('static', 'uploads', 'mobile')
    os.makedirs(folder, exist_ok=True)
    return folder


# ── Push Notification Token ───────────────────────────────────────────────────

@mobile_bp.route('/register-push-token', methods=['POST'])
@login_required
@mobile_required
def register_push_token():
    """Store the FCM push token for the current user."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()
    platform = data.get('platform', 'android')

    if not token:
        return jsonify({'success': False, 'error': 'token required'}), 400

    try:
        # Import here to avoid circular imports
        from app import db, User
        user = User.query.get(current_user.id)
        if user:
            user.fcm_token = token
            user.fcm_platform = platform
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Biometric Login ───────────────────────────────────────────────────────────

@mobile_bp.route('/biometric-login', methods=['POST'])
@mobile_required
def biometric_login():
    """
    Complete login after the device has verified biometrics locally.
    Requires a previously established session (the biometric token stored
    in the session after a successful password login).
    """
    data = request.get_json(silent=True) or {}

    if not data.get('verified'):
        return jsonify({'success': False, 'error': 'Biometric not verified'}), 401

    # Retrieve the stored user ID from the mobile biometric session
    user_id = session.get('biometric_user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'No biometric session. Please log in with password first.',
            'require_password': True,
        }), 401

    try:
        from app import db, User
        from flask_login import login_user
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        login_user(user, remember=True)
        return jsonify({
            'success': True,
            'redirect': '/dashboard',
            'user': {
                'id': user.id,
                'name': user.full_name or user.username,
                'email': user.email,
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@mobile_bp.route('/enable-biometric', methods=['POST'])
@login_required
@mobile_required
def enable_biometric():
    """Store user ID in session so biometric login can work next time."""
    session['biometric_user_id'] = current_user.id
    session.permanent = True
    return jsonify({'success': True})


# ── Photo Upload ──────────────────────────────────────────────────────────────

@mobile_bp.route('/upload-photo', methods=['POST'])
@login_required
@mobile_required
def upload_photo():
    """
    Accept a photo uploaded from the native camera/gallery.
    Supports both multipart/form-data (File object) and base64 JSON.
    """
    upload_folder = get_upload_folder()

    # ── Multipart file upload
    if 'photo' in request.files:
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        if not allowed_image(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        url = f"/static/uploads/mobile/{filename}"
        return jsonify({'success': True, 'url': url, 'filename': filename})

    # ── Base64 JSON upload
    data = request.get_json(silent=True) or {}
    b64 = data.get('base64', '')
    fmt = data.get('format', 'jpeg').lstrip('.')

    if not b64:
        return jsonify({'success': False, 'error': 'No image data'}), 400
    if fmt not in ('png', 'jpg', 'jpeg', 'webp'):
        return jsonify({'success': False, 'error': 'Invalid format'}), 400

    try:
        image_data = base64.b64decode(b64)
        filename = f"{uuid.uuid4().hex}.{fmt}"
        filepath = os.path.join(upload_folder, filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)
        url = f"/static/uploads/mobile/{filename}"
        return jsonify({'success': True, 'url': url, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Mobile-Optimised API responses ───────────────────────────────────────────

@mobile_bp.route('/gigs', methods=['GET'])
@mobile_required
def get_gigs_mobile():
    """
    Lightweight gig listing for mobile.
    Returns only the fields needed by the mobile app to reduce payload size.
    """
    try:
        from app import Gig, db
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category', '')
        search = request.args.get('q', '')

        query = Gig.query.filter_by(status='open')
        if category:
            query = query.filter(Gig.category == category)
        if search:
            query = query.filter(
                db.or_(
                    Gig.title.ilike(f'%{search}%'),
                    Gig.description.ilike(f'%{search}%'),
                )
            )

        pagination = query.order_by(Gig.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        gigs = [{
            'id': g.id,
            'title': g.title,
            'category': g.category,
            'budget': g.budget,
            'location': g.location,
            'created_at': g.created_at.isoformat() if g.created_at else None,
        } for g in pagination.items]

        return jsonify({
            'gigs': gigs,
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mobile_bp.route('/profile', methods=['GET'])
@login_required
@mobile_required
def get_profile_mobile():
    """Return the current user's profile for the mobile app."""
    try:
        u = current_user
        return jsonify({
            'id': u.id,
            'username': u.username,
            'full_name': getattr(u, 'full_name', ''),
            'email': u.email,
            'profile_photo_url': getattr(u, 'profile_photo_url', None),
            'is_worker': getattr(u, 'is_worker', False),
            'rating': getattr(u, 'rating', None),
            'wallet_balance': getattr(u, 'wallet_balance', 0),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mobile_bp.route('/notifications', methods=['GET'])
@login_required
@mobile_required
def get_notifications_mobile():
    """Return unread notifications for the mobile app."""
    try:
        from app import Notification
        notifs = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False,
        ).order_by(Notification.created_at.desc()).limit(50).all()

        return jsonify({
            'notifications': [{
                'id': n.id,
                'title': getattr(n, 'title', 'GigHala'),
                'message': n.message,
                'url': getattr(n, 'url', None),
                'created_at': n.created_at.isoformat() if n.created_at else None,
            } for n in notifs],
            'unread_count': len(notifs),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mobile_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
@mobile_required
def mark_notification_read(notif_id):
    try:
        from app import Notification, db
        n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
        n.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── App Config endpoint ───────────────────────────────────────────────────────

@mobile_bp.route('/config', methods=['GET'])
@mobile_required
def app_config():
    """
    Return runtime config needed by the mobile app on startup.
    Intentionally minimal — no secrets.
    """
    return jsonify({
        'app_version': '1.0.0',
        'min_version': '1.0.0',
        'maintenance': False,
        'features': {
            'biometric_login': True,
            'native_camera': True,
            'push_notifications': True,
        },
        'urls': {
            'privacy': '/privacy',
            'terms': '/terms',
            'support': '/support',
        },
    })
