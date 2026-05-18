import json
import os
import secrets
import time
import requests
from flask import Blueprint, jsonify, redirect, request, session, url_for
from flask_login import login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient
from email_validator import validate_email, EmailNotValidError

# Short-lived bridge tokens for Android OAuth: {token: (user_id, expires_at)}
_mobile_tokens: dict = {}

def setup_google_oauth(app, db):
    """Setup Google OAuth blueprint. Call this from main app after app is initialized."""
    # Support both GOOGLE_OAUTH_* and GOOGLE_CLIENT_* environment variable names
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("⚠️  Google OAuth credentials not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in secrets.")
        return None
    
    # Determine redirect URL based on environment
    if os.environ.get("REPLIT_DEV_DOMAIN"):
        # Replit environment
        REDIRECT_URL = f'https://{os.environ.get("REPLIT_DEV_DOMAIN")}/google_login/callback'
    else:
        # Railway or other production environment - will be determined from request
        REDIRECT_URL = None
    
    if REDIRECT_URL:
        print(f"""
✅ Google Authentication Setup Instructions:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID (Web application)
3. Add this redirect URL to Authorized redirect URIs:
   {REDIRECT_URL}
4. Copy your Client ID and Client Secret to environment secrets
5. Restart your app after adding secrets
""")
    
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
    google_auth = Blueprint("google_auth", __name__)
    
    @google_auth.route("/google_login")
    def login():
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Build callback URL - works for both Replit and Railway
        callback_url = request.url_root.rstrip('/') + '/google_login/callback'
        if request.url_root.startswith('http://'):
            callback_url = callback_url.replace('http://', 'https://', 1)

        # Remember if this was initiated from the Android app
        if request.args.get('source') == 'android':
            session['oauth_source'] = 'android'
        else:
            session.pop('oauth_source', None)

        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=callback_url,
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    
    @google_auth.route("/google_login/callback")
    def callback():
        from app import User
        code = request.args.get("code")
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        token_endpoint = google_provider_cfg["token_endpoint"]
        
        # Build callback URL - works for both Replit and Railway
        callback_url = request.url_root.rstrip('/') + '/google_login/callback'
        if request.url_root.startswith('http://'):
            callback_url = callback_url.replace('http://', 'https://', 1)
        
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=callback_url,
            code=code,
        )
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )
        
        client.parse_request_body_response(json.dumps(token_response.json()))
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)
        
        userinfo = userinfo_response.json()
        if userinfo.get("email_verified"):
            # Normalize email to ensure consistency with regular login/registration
            try:
                email_info = validate_email(userinfo["email"], check_deliverability=False)
                users_email = email_info.normalized
            except EmailNotValidError:
                return "Invalid email address from Google OAuth.", 400

            users_name = userinfo.get("given_name", userinfo.get("name", "User"))
        else:
            return "User email not available or not verified by Google.", 400

        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(username=users_name, email=users_email, oauth_provider='google', oauth_id=userinfo['sub'])
            db.session.add(user)
            db.session.commit()
        
        login_user(user)

        # Android: redirect via deep link with a short-lived bridge token
        if session.pop('oauth_source', None) == 'android':
            bridge_token = secrets.token_urlsafe(32)
            _mobile_tokens[bridge_token] = (user.id, time.time() + 300)
            return redirect(f'gighala://oauth/callback?token={bridge_token}')

        return redirect(url_for("index"))

    @google_auth.route("/api/auth/mobile/exchange", methods=["POST"])
    def mobile_exchange():
        from app import User
        # Purge expired tokens opportunistically
        now = time.time()
        expired = [t for t, (_, exp) in _mobile_tokens.items() if now > exp]
        for t in expired:
            _mobile_tokens.pop(t, None)

        data = request.get_json(silent=True) or {}
        bridge_token = data.get('token', '')
        entry = _mobile_tokens.pop(bridge_token, None)
        if not entry:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_id, expires_at = entry
        if time.time() > expires_at:
            return jsonify({"error": "Token expired"}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        login_user(user)
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "profile_photo": user.profile_photo,
                "is_verified": getattr(user, 'is_verified', False),
                "is_admin": getattr(user, 'is_admin', False),
                "halal_verified": getattr(user, 'halal_verified', False),
                "totp_enabled": getattr(user, 'totp_enabled', False),
            }
        })

    @google_auth.route("/api/auth/google/verify-token", methods=["POST"])
    def verify_google_id_token():
        """Verify a Google ID token from the Android native Sign-In SDK."""
        from app import User
        data = request.get_json(silent=True) or {}
        id_token = data.get('id_token', '')
        if not id_token:
            return jsonify({"error": "Missing id_token"}), 400

        # Verify the token with Google's tokeninfo endpoint
        token_resp = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': id_token},
            timeout=10
        )
        if not token_resp.ok:
            return jsonify({"error": "Invalid Google ID token"}), 401

        info = token_resp.json()

        # Confirm the token was issued for our app
        if info.get('aud') != GOOGLE_CLIENT_ID:
            return jsonify({"error": "Token audience mismatch"}), 401

        if info.get('email_verified') != 'true' and info.get('email_verified') is not True:
            return jsonify({"error": "Email not verified by Google"}), 401

        try:
            email_info = validate_email(info['email'], check_deliverability=False)
            users_email = email_info.normalized
        except (EmailNotValidError, KeyError):
            return jsonify({"error": "Invalid email from Google"}), 400

        users_name = info.get('given_name', info.get('name', users_email.split('@')[0]))
        google_sub = info.get('sub', '')

        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(username=users_name, email=users_email, oauth_provider='google', oauth_id=google_sub)
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return jsonify({
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "user_type": user.user_type,
                "profile_photo": user.profile_photo,
                "is_verified": getattr(user, 'is_verified', False),
                "is_admin": getattr(user, 'is_admin', False),
                "halal_verified": getattr(user, 'halal_verified', False),
                "totp_enabled": getattr(user, 'totp_enabled', False),
            }
        })

    @google_auth.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("index"))
    
    app.register_blueprint(google_auth)
    return google_auth
