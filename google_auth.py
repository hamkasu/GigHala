import json
import os
import requests
from flask import Blueprint, redirect, request, url_for
from flask_login import login_user, logout_user
from oauthlib.oauth2 import WebApplicationClient

def setup_google_oauth(app, db):
    """Setup Google OAuth blueprint. Call this from main app after app is initialized."""
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("⚠️  Google OAuth credentials not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in secrets.")
        return None
    
    DEV_REDIRECT_URL = f'https://{os.environ.get("REPLIT_DEV_DOMAIN")}/google_login/callback'
    print(f"""
✅ Google Authentication Setup Instructions:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new OAuth 2.0 Client ID (Web application)
3. Add this redirect URL to Authorized redirect URIs:
   {DEV_REDIRECT_URL}
4. Copy your Client ID and Client Secret to Replit secrets
5. Restart your app after adding secrets

For detailed instructions:
https://docs.replit.com/additional-resources/google-auth-in-flask#set-up-your-oauth-app--client
""")
    
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
    google_auth = Blueprint("google_auth", __name__)
    
    @google_auth.route("/google_login")
    def login():
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=request.base_url.replace("http://", "https://") + "/callback",
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    
    @google_auth.route("/google_login/callback")
    def callback():
        from app import User
        code = request.args.get("code")
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
        token_endpoint = google_provider_cfg["token_endpoint"]
        
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=request.base_url.replace("http://", "https://"),
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
