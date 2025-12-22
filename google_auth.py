import json
import os
import requests
from flask import Blueprint, redirect, request, url_for
from flask_login import login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient

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
            users_email = userinfo["email"]
            users_name = userinfo.get("given_name", userinfo.get("name", "User"))
        else:
            return "User email not available or not verified by Google.", 400
        
        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(username=users_name, email=users_email, oauth_provider='google', oauth_id=userinfo['sub'])
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        return redirect(url_for("index"))
    
    @google_auth.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for("index"))
    
    app.register_blueprint(google_auth)
    return google_auth
