from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, flash, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from email_validator import validate_email, EmailNotValidError
import os
import secrets
import json
import re
import stripe
import uuid
import math
import requests
from hijri_converter import Hijri, Gregorian
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from twilio.rest import Client
from email_service import email_service
from scheduled_jobs import init_scheduler
import pyotp
from halal_compliance import (
    validate_gig_halal_compliance,
    get_categories_for_dropdown,
    get_halal_guidelines_text,
    HALAL_APPROVED_CATEGORY_SLUGS
)
import qrcode
import io
import base64
import random
import calendar

# Stripe configuration - will be set dynamically based on mode
def get_stripe_keys():
    """Get Stripe keys based on the current mode setting"""
    from models import get_site_setting

    # Get the mode from site settings (default to 'test' for safety)
    stripe_mode = get_site_setting('stripe_mode', 'test')

    if stripe_mode == 'live':
        # Use live keys
        secret_key = os.environ.get('STRIPE_LIVE_SECRET_KEY')
        publishable_key = os.environ.get('STRIPE_LIVE_PUBLISHABLE_KEY')
        webhook_secret = os.environ.get('STRIPE_LIVE_WEBHOOK_SECRET')
    else:
        # Use test keys (default)
        secret_key = os.environ.get('STRIPE_TEST_SECRET_KEY')
        publishable_key = os.environ.get('STRIPE_TEST_PUBLISHABLE_KEY')
        webhook_secret = os.environ.get('STRIPE_TEST_WEBHOOK_SECRET')

    # Fallback to legacy keys if specific mode keys not set
    if not secret_key:
        secret_key = os.environ.get('STRIPE_SECRET_KEY')
    if not publishable_key:
        publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    if not webhook_secret:
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    return {
        'secret_key': secret_key,
        'publishable_key': publishable_key,
        'webhook_secret': webhook_secret,
        'mode': stripe_mode
    }

def init_stripe():
    """Initialize Stripe with the appropriate keys"""
    try:
        keys = get_stripe_keys()
        stripe.api_key = keys['secret_key']
        return keys
    except:
        # Fallback for initial setup before DB is ready
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_TEST_SECRET_KEY')
        return None

# Initialize Stripe (will use legacy key initially, then switch to mode-based after DB is ready)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY') or os.environ.get('STRIPE_TEST_SECRET_KEY')

PROCESSING_FEE_PERCENT = 0.029
PROCESSING_FEE_FIXED = 1.00

# Main categories to show in category pickers (excludes detailed subcategories)
MAIN_CATEGORY_SLUGS = [
    'design', 'writing', 'video', 'tutoring', 'content', 'web',
    'marketing', 'admin', 'general', 'programming', 'consulting',
    'engineering', 'music', 'photography', 'finance', 'crafts',
    'garden', 'coaching', 'data', 'pets', 'handyman', 'tours',
    'events', 'online-selling', 'virtual-assistant', 'delivery',
    'micro-tasks', 'caregiving', 'creative-other'
]

# Twilio SMS Configuration
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
twilio_client = None
if twilio_account_sid and twilio_auth_token:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

# Add ProxyFix middleware to handle Railway's proxy headers (X-Forwarded-For, X-Forwarded-Proto, etc.)
# This is essential for OAuth to work correctly when behind a proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1, x_port=1, x_prefix=1)

# Set secret key - CRITICAL for OAuth state management
app.secret_key = os.environ.get("SESSION_SECRET") or os.environ.get("SECRET_KEY")
if not app.secret_key:
    # Generate a random secret key for development if none is set
    # In production, ALWAYS set SESSION_SECRET - OAuth won't work without it!
    app.secret_key = secrets.token_hex(32)
    print("⚠️  WARNING: Using auto-generated SECRET_KEY. Set SESSION_SECRET environment variable in production!")

# Handle DATABASE_URL - use 'or' to catch both None and empty string
database_url = os.environ.get('DATABASE_URL') or 'sqlite:///gighala.db'

# Convert postgres:// to postgresql+psycopg2:// for SQLAlchemy compatibility
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secure session configuration for OAuth
# For Railway/Production: use X-Forwarded-Proto header to detect HTTPS through proxy
# For local: detect HTTPS based on request scheme
is_https = (
    os.environ.get('FLASK_ENV') == 'production' or 
    os.environ.get('RAILWAY_ENVIRONMENT') is not None or
    os.environ.get('RAILWAY_STATIC_URL') is not None
)
app.config['SESSION_COOKIE_SECURE'] = is_https  # CRITICAL for OAuth over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
# Enable session updates on every request to preserve state during OAuth flow
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

db = SQLAlchemy(app)

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Configure CSRF settings
app.config['WTF_CSRF_TIME_LIMIT'] = None  # CSRF tokens don't expire (use session lifetime instead)
app.config['WTF_CSRF_SSL_STRICT'] = is_https  # Match session cookie security
app.config['WTF_CSRF_ENABLED'] = True

# Secure CORS configuration - restrict to specific origins in production
# SECURITY FIX: Fail-safe CORS - require explicit configuration in production
# In development, allow all origins. In production, ALLOWED_ORIGINS must be set.
is_development = os.environ.get('FLASK_ENV') == 'development'
allowed_origins_env = os.environ.get('ALLOWED_ORIGINS', '')

if is_development:
    # Development mode: allow all origins if not specified
    allowed_origins = allowed_origins_env.split(',') if allowed_origins_env else ['*']
else:
    # Production mode: require explicit ALLOWED_ORIGINS
    if not allowed_origins_env or allowed_origins_env.strip() == '*':
        raise ValueError(
            "SECURITY ERROR: ALLOWED_ORIGINS must be explicitly set in production. "
            "Wildcard (*) is not allowed in production mode. "
            "Set ALLOWED_ORIGINS to a comma-separated list of allowed domains."
        )
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(',')]

CORS(app,
     origins=allowed_origins,
     supports_credentials=True,
     max_age=3600)

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.user_loader
def load_user(user_id):
    # User class is defined later in this file, so we access it from globals
    return globals()['User'].query.get(int(user_id))

# OAuth Configuration
oauth = OAuth(app)

# Google OAuth - only register if credentials are provided
# Support both GOOGLE_OAUTH_* and GOOGLE_CLIENT_* environment variable names
google_client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID')
google_client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET') or os.environ.get('GOOGLE_CLIENT_SECRET')

if google_client_id and google_client_secret:
    google = oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
else:
    google = None

# Microsoft OAuth - only register if credentials are provided
if os.environ.get('MICROSOFT_CLIENT_ID') and os.environ.get('MICROSOFT_CLIENT_SECRET'):
    microsoft = oauth.register(
        name='microsoft',
        client_id=os.environ.get('MICROSOFT_CLIENT_ID'),
        client_secret=os.environ.get('MICROSOFT_CLIENT_SECRET'),
        server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
else:
    microsoft = None

# Apple OAuth - only register if credentials are provided
if os.environ.get('APPLE_CLIENT_ID') and os.environ.get('APPLE_CLIENT_SECRET'):
    apple = oauth.register(
        name='apple',
        client_id=os.environ.get('APPLE_CLIENT_ID'),
        client_secret=os.environ.get('APPLE_CLIENT_SECRET'),
        server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'name email'
        }
    )
else:
    apple = None

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'work_photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gig_photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'portfolio'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'verification'), exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_mime_type(filename):
    """Get MIME type from filename extension"""
    if not filename or '.' not in filename:
        return 'application/octet-stream'

    ext = filename.rsplit('.', 1)[1].lower()
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    return mime_types.get(ext, 'application/octet-stream')

# Geolocation Helper Functions
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None

    # Convert latitude and longitude to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in kilometers
    earth_radius_km = 6371

    distance = earth_radius_km * c
    return round(distance, 2)

def geocode_location(location_string):
    """
    Convert a location string (city, state) to latitude and longitude coordinates.
    Uses OpenStreetMap's Nominatim API (free, no API key required).
    Returns tuple (latitude, longitude) or (None, None) if geocoding fails.
    """
    if not location_string or location_string.strip() == '':
        return None, None

    try:
        # Add Malaysia to the search query for better results
        search_query = f"{location_string}, Malaysia"

        # Nominatim API endpoint
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'limit': 1
        }

        # Set a user agent (required by Nominatim)
        headers = {
            'User-Agent': 'GigHala/1.0 (contact@gighala.com)'
        }

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon

        return None, None

    except Exception as e:
        print(f"Geocoding error for '{location_string}': {str(e)}")
        return None, None

# Malaysian cities coordinates cache (for fallback and faster lookups)
MALAYSIAN_CITIES = {
    # Kuala Lumpur
    'Kuala Lumpur, KL': (3.1390, 101.6869),
    'Cheras, KL': (3.1193, 101.7284),
    'Kepong, KL': (3.2176, 101.6386),
    'Bangsar, KL': (3.1279, 101.6707),

    # Johor
    'Johor Bahru, Johor': (1.4927, 103.7414),
    'Skudai, Johor': (1.5327, 103.6572),
    'Kulai, Johor': (1.6553, 103.6005),
    'Kluang, Johor': (2.0307, 103.3170),
    'Muar, Johor': (2.0443, 102.5689),

    # Penang
    'George Town, Penang': (5.4141, 100.3288),
    'Butterworth, Penang': (5.3991, 100.3643),
    'Bayan Lepas, Penang': (5.2974, 100.2665),

    # Selangor
    'Petaling Jaya, Selangor': (3.1073, 101.6067),
    'Shah Alam, Selangor': (3.0733, 101.5185),
    'Subang Jaya, Selangor': (3.0437, 101.5874),
    'Klang, Selangor': (3.0327, 101.4450),
    'Ampang, Selangor': (3.1490, 101.7611),
    'Kajang, Selangor': (2.9920, 101.7885),
    'Rawang, Selangor': (3.3214, 101.5769),
    'Sepang, Selangor': (2.7297, 101.7434),

    # Perak
    'Ipoh, Perak': (4.5975, 101.0901),
    'Taiping, Perak': (4.8598, 100.7336),
    'Teluk Intan, Perak': (4.0275, 101.0213),

    # Kedah
    'Alor Setar, Kedah': (6.1239, 100.3681),
    'Sungai Petani, Kedah': (5.6472, 100.4878),

    # Kelantan
    'Kota Bharu, Kelantan': (6.1331, 102.2386),

    # Terengganu
    'Kuala Terengganu, Terengganu': (5.3302, 103.1408),

    # Pahang
    'Kuantan, Pahang': (3.8077, 103.3260),
    'Temerloh, Pahang': (3.4508, 102.4184),

    # Melaka
    'Melaka City, Melaka': (2.1896, 102.2501),

    # Negeri Sembilan
    'Seremban, Negeri Sembilan': (2.7258, 101.9424),
    'Nilai, Negeri Sembilan': (2.8200, 101.8005),

    # Sabah
    'Kota Kinabalu, Sabah': (5.9804, 116.0735),
    'Sandakan, Sabah': (5.8402, 118.1179),
    'Tawau, Sabah': (4.2451, 117.8934),

    # Sarawak
    'Kuching, Sarawak': (1.5535, 110.3593),
    'Miri, Sarawak': (4.3997, 113.9914),
    'Sibu, Sarawak': (2.3000, 111.8200),

    # Perlis
    'Kangar, Perlis': (6.4414, 100.1986),

    # Putrajaya
    'Putrajaya, Putrajaya': (2.9264, 101.6964),
}

def get_coordinates(location_string):
    """
    Get coordinates for a location, using cache first, then geocoding API.
    Returns tuple (latitude, longitude) or (None, None) if location cannot be resolved.
    """
    if not location_string:
        return None, None

    # Check cache first
    if location_string in MALAYSIAN_CITIES:
        return MALAYSIAN_CITIES[location_string]

    # Try geocoding
    return geocode_location(location_string)

# Rate limiting storage (in-memory, consider Redis for production)
login_attempts = {}
api_rate_limits = {}

# General API rate limiting
def api_rate_limit(requests_per_minute=60):
    """Rate limit decorator for general API endpoints"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            identifier = f"{request.remote_addr}:{f.__name__}"
            current_time = datetime.utcnow()
            
            if identifier not in api_rate_limits:
                api_rate_limits[identifier] = {'requests': [], 'blocked_until': None}
            
            rate_data = api_rate_limits[identifier]
            
            # Check if blocked
            if rate_data['blocked_until'] and current_time < rate_data['blocked_until']:
                remaining = int((rate_data['blocked_until'] - current_time).total_seconds())
                return jsonify({'error': f'Rate limit exceeded. Try again in {remaining} seconds'}), 429
            
            # Remove old requests (older than 1 minute)
            one_minute_ago = current_time - timedelta(minutes=1)
            rate_data['requests'] = [t for t in rate_data['requests'] if t > one_minute_ago]
            
            # Check if rate limit exceeded
            if len(rate_data['requests']) >= requests_per_minute:
                rate_data['blocked_until'] = current_time + timedelta(seconds=60)
                return jsonify({'error': 'Rate limit exceeded. Please wait a moment.'}), 429
            
            # Record this request
            rate_data['requests'].append(current_time)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Cleanup old rate limit entries periodically
_last_cleanup = datetime.utcnow()

def cleanup_rate_limits():
    """Remove stale rate limit entries older than 1 hour"""
    global _last_cleanup
    current_time = datetime.utcnow()
    cutoff = current_time - timedelta(hours=1)
    
    # Cleanup login attempts
    stale_logins = [k for k, v in login_attempts.items() 
                    if v['first_attempt'] < cutoff and 
                    (v['locked_until'] is None or v['locked_until'] < current_time)]
    for k in stale_logins:
        del login_attempts[k]
    
    # Cleanup API rate limits
    stale_api = [k for k, v in api_rate_limits.items() 
                 if not v['requests'] or max(v['requests']) < cutoff]
    for k in stale_api:
        del api_rate_limits[k]
    
    _last_cleanup = current_time

@app.before_request
def before_request_handler():
    """Run periodic cleanup on rate limit storage and log visitor"""
    global _last_cleanup
    current_time = datetime.utcnow()
    # Run cleanup every 5 minutes
    if (current_time - _last_cleanup).total_seconds() > 300:
        cleanup_rate_limits()

    # Log visitor (excluding static and API calls for cleaner analytics)
    if not request.path.startswith('/static') and not request.path.startswith('/api'):
        try:
            visitor = VisitorLog(
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                path=request.path,
                user_id=session.get('user_id'),
                referrer=request.referrer
            )
            db.session.add(visitor)
            
            # Increment legacy counter for the footer
            stats = SiteStats.query.filter_by(key='visitor_count').first()
            if stats:
                stats.value += 1
            
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Error logging visitor: {str(e)}")
            db.session.rollback()

# Translation dictionaries for bilingual support (Malay/English)
TRANSLATIONS = {
    'ms': {
        # Dashboard
        'welcome_back': 'Selamat kembali',
        'happening_today': 'Ini yang berlaku dengan akaun anda hari ini',
        'wallet_balance': 'Baki Dompet',
        'available_withdraw': 'Boleh dikeluarkan',
        'completed_gigs': 'Gig Selesai',
        'successfully_finished': 'Berjaya diselesaikan',
        'accepted_gigs': 'Gig Diterima',
        'applications_accepted': 'Permohonan diterima',
        'active_applications': 'Permohonan Aktif',
        'submitted_proposals': 'Cadangan dihantar',
        'posted_gigs': 'Gig Disiarkan',
        'total_gigs_created': 'Jumlah gig dicipta',
        'total_earned': 'Jumlah Perolehan',
        'all_time_earnings': 'Perolehan sepanjang masa',
        'your_rating': 'Penarafan Anda',
        'no_ratings_yet': 'Tiada penarafan lagi',
        'based_on_reviews': 'Berdasarkan {count} ulasan',
        'based_on_review': 'Berdasarkan {count} ulasan',
        'complete_gigs_rated': 'Selesaikan gig untuk diberi penarafan',

        # Reviews
        'gigs_to_review': 'Gig Untuk Diulas',
        'recent_reviews_received': 'Ulasan Terkini Diterima',
        'no_completed_gigs_review': 'Tiada gig selesai untuk diulas',
        'no_reviews_yet': 'Tiada ulasan lagi',
        'leave_review': 'Beri Ulasan',
        'completed_on': 'Selesai pada',
        'leave_a_review': 'Beri Ulasan',
        'rating': 'Penarafan',
        'comment_optional': 'Komen (Pilihan)',
        'share_experience': 'Kongsi pengalaman anda...',
        'cancel': 'Batal',
        'submit_review': 'Hantar Ulasan',
        'please_select_rating': 'Sila pilih penarafan',
        'review_submitted': 'Ulasan berjaya dihantar!',
        'review_failed': 'Gagal menghantar ulasan',
        'error_occurred': 'Ralat berlaku. Sila cuba lagi.',

        # Other sections
        'active_gigs': 'Gig Aktif',
        'recent_applications': 'Permohonan Terkini',
        'your_posted_gigs': 'Gig Anda Siarkan',
        'recent_transactions': 'Transaksi Terkini',
        'quick_actions': 'Tindakan Pantas',
        'browse_gigs': 'Cari Gig',
        'view_wallet': 'Lihat Dompet',
        'post_gig': 'Siarkan Gig',
        'admin_dashboard': 'Papan Pemuka Admin',
        'view_all': 'Lihat Semua',
        'no_active_gigs': 'Tiada gig aktif',
        'no_applications_yet': 'Tiada permohonan lagi',
        'no_posted_gigs': 'Tiada gig disiarkan',
        'no_transactions_yet': 'Tiada transaksi lagi',
        'payment_sent': 'Bayaran Dihantar',
        'payment_received': 'Bayaran Diterima',
        'application': 'Permohonan',

        # Language
        'language': 'Bahasa',
        'malay': 'Bahasa Melayu',
        'english': 'English',

        # Logout
        'logout': 'Log Keluar',
        'logout_confirm': 'Adakah anda pasti mahu log keluar?',

        # Navigation Menu
        'nav_search': 'Cari',
        'nav_submit': 'Hantar',
        'nav_messages': 'Mesej',
        'nav_wallet': 'Dompet',
        'nav_admin': 'Admin',
        'nav_dashboard': 'Dashboard',
        'nav_accepted_gigs': 'Gig Diterima',
        'nav_escrow': 'Escrow',
        'nav_documents': 'Dokumen',
        'nav_settings': 'Tetapan Akaun',
        'nav_home': 'Laman Utama',
        'nav_post': 'Siar',

        # SOCSO
        'socso_statement': 'Penyata SOCSO',
        'socso_contributions': 'Caruman SOCSO',
        'socso_record': 'Rekod Caruman SOCSO',
        'contribution_period': 'Tempoh Caruman',
        'contribution_date': 'Tarikh Caruman',
        'gross_amount': 'Jumlah Kasar',
        'platform_fee': 'Yuran Platform',
        'net_earnings': 'Pendapatan Bersih',
        'socso_deduction': 'Potongan SOCSO (1.25%)',
        'final_payout': 'Bayaran Akhir',
        'contribution_type': 'Jenis Caruman',
        'remittance_status': 'Status Penghantaran',
        'remitted': 'Telah Dihantar',
        'pending_remittance': 'Menunggu Penghantaran',
        'total_contributions': 'Jumlah Caruman',
        'print_statement': 'Cetak Penyata',
        'back_to_billing': 'Kembali ke Bil',

        # Homepage - Navigation
        'find_gigs': 'Cari Gig',
        'categories': 'Kategori',
        'how_it_works': 'Cara Kerja',
        'login': 'Log Masuk',
        'register_free': 'Daftar Percuma',

        # Homepage - Hero Section
        'active_freelancers': '{} Freelancers Aktif',  # Format with actual count
        'earn_income': 'Jana Pendapatan',
        'halal_blessed': 'Halal & Berkah',
        'from_home': 'dari Rumah',
        'hero_description': 'Platform gig economy #1 Malaysia yang menawarkan peluang side hustle halal untuk raih RM800-RM4,000 sebulan. Tanpa modal, tanpa komitmen panjang.',
        'active_gigs_stat': 'Gig Aktif',
        'paid_this_year': 'Dibayar Tahun Ini',
        'instant_payout': 'Instant Payout',
        'start_earning': 'Mula Jana Pendapatan',
        'watch_demo': 'Tonton Video Demo',
        'registered_ssm': 'Berdaftar SSM',

        # Homepage - Categories
        'popular_categories': 'Kategori Popular',
        'choose_skill_subtitle': 'Pilih skill anda dan mula jana pendapatan hari ini',

        # Homepage - Gigs Section
        'latest_gigs': 'Gig Terkini',
        'search_gigs': 'Cari gig...',
        'all_categories': 'Semua Kategori',
        'all_locations': 'Semua Lokasi',
        'halal_only': 'Halal Sahaja',
        'view_more': 'Lihat Lebih Banyak',

        # Homepage - How It Works
        'easy_fast_subtitle': 'Mudah & Cepat - Mula jana dalam 5 minit',
        'step_1_title': 'Daftar Percuma',
        'step_1_desc': 'Buat akaun dalam 2 minit. Tiada bayaran pendaftaran, tiada syarat rumit.',
        'step_2_title': 'Cari Gig Sesuai',
        'step_2_desc': 'Pilih dari 2000+ gig halal mengikut skill, lokasi dan budget anda.',
        'step_3_title': 'Apply & Kerja',
        'step_3_desc': 'Submit proposal anda atau buat video pitch 30 saat untuk menonjol.',
        'step_4_title': 'Terima Bayaran Selamat',
        'step_4_desc': 'Client deposit dana ke escrow sebelum kerja bermula. Bayaran hanya dilepaskan selepas anda hantar kerja & client puas hati. Instant payout 24 jam ke Touch \'n Go/bank – tiada risiko tak dibayar!',

        # Homepage - Testimonials
        'success_stories': 'Kisah Kejayaan',
        'success_subtitle': 'Ratusan freelancers berjaya jana pendapatan konsisten',
        'testimonial_1': '"Dalam 2 bulan, saya dah buat RM 4,500 dari video editing! Platform ni betul-betul game changer untuk ibu tunggal macam saya."',
        'testimonial_1_name': 'Nurul Huda',
        'testimonial_1_role': 'Video Editor • KL',
        'testimonial_1_earnings': 'Pendapatan: RM 4,500/bulan',
        'testimonial_2': '"Fresh grad cari kerja susah. GigHala bagi peluang saya buat income sambil tunggu tawaran tetap. Sekarang side income saya RM 2,800!"',
        'testimonial_2_name': 'Ahmad Zaki',
        'testimonial_2_role': 'Graphic Designer • Penang',
        'testimonial_2_earnings': 'Pendapatan: RM 2,800/bulan',
        'testimonial_3': '"Saya tutor online part-time. Platform ni connect saya dengan pelajar SPM yang betul-betul perlukan bantuan. Win-win situation!"',
        'testimonial_3_name': 'Siti Aisyah',
        'testimonial_3_role': 'SPM Tutor • JB',
        'testimonial_3_earnings': 'Pendapatan: RM 1,900/bulan',

        # Homepage - CTA
        'ready_to_earn': 'Siap untuk mula jana pendapatan halal?',
        'join_freelancers': 'Join freelancers yang dah berjaya. Daftar percuma sekarang!',
        'register_now_free': 'Daftar Sekarang - 100% Percuma',
        'cta_benefits': '✓ Tiada bayaran tersembunyi  •  ✓ Bayaran instant  •  ✓ Halal verified',

        # Homepage - Footer
        'payhalal_notice': 'Pembayaran Selamat & Halal dengan PayHalal – Gateway Pembayaran Shariah-Compliant Pertama di Dunia 🌙',
        'footer_description': 'Platform gig economy halal #1 di Malaysia. Jana pendapatan berkah dari rumah.',
        'about_us': 'Tentang Kami',
        'platform': 'Platform',
        'pricing': 'Pricing',
        'resources': 'Resources',
        'blog': 'Blog',
        'freelancer_guide': 'Panduan Freelancer',
        'faq': 'FAQ',
        'support': 'Support',
        'legal': 'Legal',
        'terms_conditions': 'Syarat & Terma',
        'privacy_policy': 'Privasi Policy',
        'halal_compliance': 'Halal Compliance',
        'gig_workers_bill': 'Gig Workers Bill',
        'rights_reserved': '© 2025 GigHala. Dimiliki dan dikendalikan oleh Calmic Sdn Bhd (Nombor Pendaftaran: 1466852W / 202201021155). Hak cipta terpelihara.',
        'visitor_count': 'Jumlah Pelawat:',
        'ssm_registered': 'SSM Registered',
        'secure_payment': 'Secure Payment',

        # Homepage - Modals
        'login_title': 'Log Masuk',
        'register_title': 'Daftar Percuma',
        'email': 'Email',
        'password': 'Password',
        'no_account': 'Belum ada akaun?',
        'register_now': 'Daftar sekarang',
        'full_name': 'Nama Penuh',
        'username': 'Username',
        'phone_number': 'No. Telefon',
        'ic_passport_no': 'No. MyKad / Passport',
        'ic_passport_hint': 'Masukkan nombor MyKad (12 digit) atau nombor passport anda',
        'location': 'Lokasi',
        'select_location': 'Pilih lokasi',
        'register_as': 'Daftar sebagai',
        'freelancer_find_work': 'Freelancer (Cari Kerja)',
        'client_post_work': 'Client (Post Kerja)',
        'both': 'Kedua-duanya',
        'have_account': 'Dah ada akaun?',
        'login_now': 'Log masuk',
        'payment_received_popup': 'Bayaran Diterima!',

        # Category Names
        'cat_design': 'Design & Kreatif',
        'cat_writing': 'Penulisan & Terjemahan',
        'cat_content': 'Penciptaan Kandungan',
        'cat_photography': 'Fotografi, Videografi & Animasi',
        'cat_web': 'Pembangunan Web',
        'cat_marketing': 'Pemasaran Digital',
        'cat_tutoring': 'Tunjuk Ajar',
        'cat_admin': 'Sokongan Admin & Pentadbiran Maya',
        'cat_general': 'Kerja Am',
        'cat_delivery': 'Penghantaran & Logistik',
        'cat_micro_tasks': 'Micro-Tasks & Tugasan',
        'cat_events': 'Pengurusan Acara',
        'cat_caregiving': 'Penjagaan & Perkhidmatan',
        'cat_creative_other': 'Lain-lain Kreatif',

        # Category Translations (for API)
        'category_design': 'Reka Bentuk',
        'category_writing': 'Penulisan & Terjemahan',
        'category_video': 'Video & Animasi',
        'category_tutoring': 'Tunjuk Ajar & Pendidikan',
        'category_content': 'Penciptaan Kandungan',
        'category_web': 'Pembangunan Web',
        'category_marketing': 'Pemasaran Digital',
        'category_admin': 'Pentadbiran & Pembantu Maya',
        'category_general': 'Kerja Am',
        'category_programming': 'Pengaturcaraan & Teknologi',
        'category_consulting': 'Perundingan Perniagaan',
        'category_engineering': 'Perkhidmatan Kejuruteraan',
        'category_music': 'Muzik & Audio',
        'category_photography': 'Fotografi',
        'category_finance': 'Kewangan & Simpan Kira',
        'category_crafts': 'Kraftangan & Buatan Tangan',
        'category_garden': 'Rumah & Taman',
        'category_coaching': 'Bimbingan Hidup',
        'category_data': 'Analisis Data',
        'category_pets': 'Perkhidmatan Haiwan Peliharaan',
        'category_handyman': 'Tukang & Pembaikan',
        'category_tours': 'Panduan Pelancongan',
        'category_events': 'Perancangan Acara',
        'category_online-selling': 'Jualan Dalam Talian',
        'category_graphic-design': 'Reka Bentuk Grafik',
        'category_ui-ux': 'Reka Bentuk UI/UX',
        'category_illustration': 'Ilustrasi',
        'category_logo-design': 'Reka Bentuk Logo',
        'category_fashion': 'Fesyen & Tekstil',
        'category_interior-design': 'Reka Bentuk Dalaman',
        'category_content-writing': 'Penulisan Kandungan',
        'category_translation': 'Terjemahan',
        'category_proofreading': 'Pemeriksaan & Penyuntingan',
        'category_resume': 'Penulisan Resume',
        'category_email-marketing': 'Pemasaran Email',
        'category_social-copy': 'Penulisan Media Sosial',
        'category_video-editing': 'Penyuntingan Video',
        'category_animation': 'Animasi',
        'category_voiceover': 'Suara Lepas',
        'category_podcast': 'Pengeluaran Podcast',
        'category_virtual-assistant': 'Pembantu Maya',
        'category_transcription': 'Transkripsi Audio',
        'category_data-entry': 'Pengesanan Data',
        'category_bookkeeping': 'Simpan Kira & Perakaunan',
        'category_legal': 'Nasihat Perundangan',
        'category_wellness-coaching': 'Bimbingan Kesihatan',
        'category_personal-styling': 'Gaya & Imej Peribadi',
        'category_home-repair': 'Pembaikan Rumah',
        'category_cleaning': 'Pembersihan & Penyelenggaraan',
        'category_gardening': 'Berkebun & Landskap',
        'category_music-production': 'Pengeluaran Muzik',
        'category_event-planning': 'Perancangan Acara',

        # Gigs Page
        'search': 'Cari',
        'keywords_placeholder': 'Kata kunci...',
        'all_categories_filter': 'Semua Kategori',
        'design_cat': 'Design',
        'tutoring_education': 'Tunjuk Ajar & Pendidikan',
        'admin_virtual_assistant': 'Admin & Pembantu Maya',
        'budget_rm': 'Budget (RM)',
        'min_placeholder': 'Min',
        'max_placeholder': 'Max',
        'search_gig_btn': 'Cari Gig',
        'gigs_found': 'gig ditemui',
        'sort_by': 'Susun:',
        'newest': 'Terbaru',
        'budget_highest': 'Budget Tertinggi',
        'budget_lowest': 'Budget Terendah',
        'loading_gigs': 'Memuatkan gig...',
        'no_gigs_found': 'Tiada gig ditemui',
        'no_gigs_desc': 'Cuba ubah filter atau semak semula nanti untuk peluang baru',
        'error_loading_gigs': 'Ralat memuatkan gig',
        'reload_page': 'Sila muat semula halaman',
        'flexible': 'Fleksibel',
        'budget': 'Budget',

        # Post Gig Page
        'post_new_gig': 'Siarkan Gig Baru',
        'edit_gig': 'Edit Gig',
        'find_freelancer_subtitle': 'Cari freelancer yang sesuai untuk projek anda',
        'update_gig_subtitle': 'Kemaskini maklumat gig anda',
        'gig_information': 'Maklumat Gig',
        'gig_title': 'Tajuk Gig',
        'gig_title_placeholder': 'e.g., Design logo untuk restoran halal saya',
        'gig_title_hint': 'Tulis tajuk yang jelas dan menarik perhatian',
        'description': 'Penerangan',
        'description_placeholder': 'Terangkan projek anda dengan terperinci. Masukkan keperluan, deliverables, dan arahan khusus.',
        'category': 'Kategori',
        'budget_duration': 'Budget & Tempoh',
        'budget_min': 'Budget Minimum (RM)',
        'budget_max': 'Budget Maksimum (RM)',
        'approved_budget': 'Approved Budget (RM)',
        'approved_budget_hint': 'Jumlah sebenar yang diluluskan',
        'approved_budget_help': 'Pilihan: Masukkan jumlah tepat yang telah diluluskan untuk gig ini',
        'duration': 'Tempoh',
        'select_duration': 'Pilih tempoh',
        'duration_1_3_days': '1-3 hari',
        'duration_1_week': '1 minggu',
        'duration_2_weeks': '2 minggu',
        'duration_1_month': '1 bulan',
        'duration_ongoing': 'Berterusan',
        'deadline': 'Tarikh Akhir',
        'location_skills': 'Lokasi & Kemahiran',
        'type_or_select_location': 'Taip atau pilih lokasi',
        'all_locations_option': 'Semua lokasi',
        'remote_option': 'Remote',
        'skills_required': 'Kemahiran Diperlukan',
        'type_skill_enter': 'Taip kemahiran dan tekan Enter',
        'press_enter_add_skill': 'Tekan Enter untuk menambah setiap kemahiran',
        'reference_photos': 'Gambar Rujukan',
        'upload_photos_optional': 'Muat Naik Fail (Pilihan)',
        'click_to_upload': 'Klik untuk muat naik',
        'drag_photos_here': 'atau seret fail ke sini',
        'photo_format_hint': 'PNG, JPG, WEBP, PDF atau Word (Maksimum 5MB setiap fail, maksimum 5 fail)',
        'additional_options': 'Pilihan Tambahan',
        'remote_work': 'Kerja Remote',
        'remote_work_desc': 'Freelancer boleh bekerja dari mana-mana',
        'halal_compliant': 'Halal Compliant',
        'halal_compliant_desc': 'Projek patuh syariah',
        'instant_payout_label': 'Instant Payout',
        'instant_payout_desc': 'Bayaran dalam 24 jam',
        'brand_partnership': 'Brand Partnership',
        'brand_partnership_desc': 'Kolaborasi dengan jenama',
        'back_to_gig': 'Kembali ke gig',
        'no_post_fee': 'Tiada bayaran untuk post gig',
        'save_changes': 'Simpan Perubahan',
        'post_gig_btn': 'Post Gig',
        'please_select_category': 'Sila pilih kategori',
        'budget_max_error': 'Budget maksimum mesti lebih besar daripada budget minimum',
        'processing': 'Memproses...',
        'max_5_photos': 'Maksimum 5 fail sahaja dibenarkan',
        'only_image_formats': 'Hanya fail PNG, JPG, WEBP, PDF atau Word dibenarkan',
        'max_file_size_5mb': 'Saiz fail mesti kurang daripada 5MB',
        
        # Messages & Chat
        'messages_page_title': 'Mesej',
        'messages_page_subtitle': 'Berkomunikasi dengan klien dan freelancer',
        'no_conversations_yet': 'Tiada Perbualan Lagi',
        'start_conversation_hint': 'Mulakan perbualan dengan memohon ke gig atau menerima permohonan',
        'no_messages_yet': 'Tiada mesej lagi',
        'send_message': 'Hantar Mesej',
        'message_placeholder': 'Taip mesej anda di sini...',
        'type_message': 'Taip mesej...',
        'gig_reference': 'Rujuk:',
    },
    'en': {
        # Dashboard
        'welcome_back': 'Welcome back',
        'happening_today': "Here's what's happening with your account today",
        'wallet_balance': 'Wallet Balance',
        'available_withdraw': 'Available to withdraw',
        'completed_gigs': 'Completed Gigs',
        'successfully_finished': 'Successfully finished',
        'accepted_gigs': 'Accepted Gigs',
        'applications_accepted': 'Applications accepted',
        'active_applications': 'Active Applications',
        'submitted_proposals': 'Submitted proposals',
        'posted_gigs': 'Posted Gigs',
        'total_gigs_created': 'Total gigs created',
        'total_earned': 'Total Earned',
        'all_time_earnings': 'All-time earnings',
        'your_rating': 'Your Rating',
        'no_ratings_yet': 'No ratings yet',
        'based_on_reviews': 'Based on {count} reviews',
        'based_on_review': 'Based on {count} review',
        'complete_gigs_rated': 'Complete gigs to get rated',

        # Reviews
        'gigs_to_review': 'Gigs to Review',
        'recent_reviews_received': 'Recent Reviews Received',
        'no_completed_gigs_review': 'No completed gigs to review',
        'no_reviews_yet': 'No reviews yet',
        'leave_review': 'Leave Review',
        'completed_on': 'Completed on',
        'leave_a_review': 'Leave a Review',
        'rating': 'Rating',
        'comment_optional': 'Comment (Optional)',
        'share_experience': 'Share your experience...',
        'cancel': 'Cancel',
        'submit_review': 'Submit Review',
        'please_select_rating': 'Please select a rating',
        'review_submitted': 'Review submitted successfully!',
        'review_failed': 'Failed to submit review',
        'error_occurred': 'An error occurred. Please try again.',

        # Other sections
        'active_gigs': 'Active Gigs',
        'recent_applications': 'Recent Applications',
        'your_posted_gigs': 'Your Posted Gigs',
        'recent_transactions': 'Recent Transactions',
        'quick_actions': 'Quick Actions',
        'browse_gigs': 'Browse Gigs',
        'view_wallet': 'View Wallet',
        'post_gig': 'Post a Gig',
        'admin_dashboard': 'Admin Dashboard',
        'view_all': 'View All',
        'no_active_gigs': 'No active gigs',
        'no_applications_yet': 'No applications yet',
        'no_posted_gigs': 'No posted gigs',
        'no_transactions_yet': 'No transactions yet',
        'payment_sent': 'Payment Sent',
        'payment_received': 'Payment Received',
        'application': 'Application',

        # Language
        'language': 'Language',
        'malay': 'Bahasa Melayu',
        'english': 'English',

        # Logout
        'logout': 'Logout',
        'logout_confirm': 'Are you sure you want to logout?',

        # Navigation Menu
        'nav_search': 'Search',
        'nav_submit': 'Submit',
        'nav_messages': 'Messages',
        'nav_wallet': 'Wallet',
        'nav_admin': 'Admin',
        'nav_dashboard': 'Dashboard',
        'nav_accepted_gigs': 'Accepted Gigs',
        'nav_escrow': 'Escrow',
        'nav_documents': 'Documents',
        'nav_settings': 'Account Settings',
        'nav_home': 'Home',
        'nav_post': 'Post',

        # SOCSO
        'socso_statement': 'SOCSO Statement',
        'socso_contributions': 'SOCSO Contributions',
        'socso_record': 'SOCSO Contribution Record',
        'contribution_period': 'Contribution Period',
        'contribution_date': 'Contribution Date',
        'gross_amount': 'Gross Amount',
        'platform_fee': 'Platform Fee',
        'net_earnings': 'Net Earnings',
        'socso_deduction': 'SOCSO Deduction (1.25%)',
        'final_payout': 'Final Payout',
        'contribution_type': 'Contribution Type',
        'remittance_status': 'Remittance Status',
        'remitted': 'Remitted',
        'pending_remittance': 'Pending Remittance',
        'total_contributions': 'Total Contributions',
        'print_statement': 'Print Statement',
        'back_to_billing': 'Back to Billing',

        # Homepage - Navigation
        'find_gigs': 'Find Gigs',
        'categories': 'Categories',
        'how_it_works': 'How It Works',
        'login': 'Login',
        'register_free': 'Sign Up Free',

        # Homepage - Hero Section
        'active_freelancers': 'Active Freelancers',
        'earn_income': 'Earn Income',
        'halal_blessed': 'Halal & Blessed',
        'from_home': 'from Home',
        'hero_description': "Malaysia's #1 gig economy platform offering halal side hustle opportunities to earn RM800-RM4,000 per month. No capital required, no long-term commitment.",
        'active_gigs_stat': 'Active Gigs',
        'paid_this_year': 'Paid This Year',
        'instant_payout': 'Instant Payout',
        'start_earning': 'Start Earning Now',
        'watch_demo': 'Watch Demo Video',
        'registered_ssm': 'SSM Registered',

        # Homepage - Categories
        'popular_categories': 'Popular Categories',
        'choose_skill_subtitle': 'Choose your skill and start earning today',

        # Homepage - Gigs Section
        'latest_gigs': 'Latest Gigs',
        'search_gigs': 'Search gigs...',
        'all_categories': 'All Categories',
        'all_locations': 'All Locations',
        'halal_only': 'Halal Only',
        'view_more': 'View More',

        # Homepage - How It Works
        'easy_fast_subtitle': 'Easy & Fast - Start earning in 5 minutes',
        'step_1_title': 'Register Free',
        'step_1_desc': 'Create an account in 2 minutes. No registration fees, no complicated requirements.',
        'step_2_title': 'Find Suitable Gigs',
        'step_2_desc': 'Choose from 2000+ halal gigs based on your skills, location and budget.',
        'step_3_title': 'Apply & Work',
        'step_3_desc': 'Submit your proposal or create a 30-second video pitch to stand out.',
        'step_4_title': 'Receive Secure Payment',
        'step_4_desc': 'Client deposits funds into escrow before work begins. Payment only released after you deliver work & client is satisfied. Instant payout within 24 hours to Touch \'n Go/bank – no risk of non-payment!',

        # Homepage - Testimonials
        'success_stories': 'Success Stories',
        'success_subtitle': 'Hundreds of freelancers successfully earning consistent income',
        'testimonial_1': '"In 2 months, I made RM 4,500 from video editing! This platform is a real game changer for single mothers like me."',
        'testimonial_1_name': 'Nurul Huda',
        'testimonial_1_role': 'Video Editor • KL',
        'testimonial_1_earnings': 'Earnings: RM 4,500/month',
        'testimonial_2': '"Fresh grad finding work is hard. GigHala gave me the opportunity to earn income while waiting for permanent offers. Now my side income is RM 2,800!"',
        'testimonial_2_name': 'Ahmad Zaki',
        'testimonial_2_role': 'Graphic Designer • Penang',
        'testimonial_2_earnings': 'Earnings: RM 2,800/month',
        'testimonial_3': '"I tutor online part-time. This platform connects me with SPM students who really need help. Win-win situation!"',
        'testimonial_3_name': 'Siti Aisyah',
        'testimonial_3_role': 'SPM Tutor • JB',
        'testimonial_3_earnings': 'Earnings: RM 1,900/month',

        # Homepage - CTA
        'ready_to_earn': 'Ready to start earning halal income?',
        'join_freelancers': "Join freelancers who've already succeeded. Sign up free now!",
        'register_now_free': 'Sign Up Now - 100% Free',
        'cta_benefits': '✓ No hidden fees  •  ✓ Instant payments  •  ✓ Halal verified',

        # Homepage - Footer
        'footer_description': "Malaysia's #1 halal gig economy platform. Earn blessed income from home.",
        'payhalal_notice': 'Secure & Halal Payments with PayHalal – The World\'s First Shariah-Compliant Payment Gateway 🌙',
        'about_us': 'About Us',
        'platform': 'Platform',
        'pricing': 'Pricing',
        'resources': 'Resources',
        'blog': 'Blog',
        'freelancer_guide': 'Freelancer Guide',
        'faq': 'FAQ',
        'support': 'Support',
        'legal': 'Legal',
        'terms_conditions': 'Terms & Conditions',
        'privacy_policy': 'Privacy Policy',
        'halal_compliance': 'Halal Compliance',
        'gig_workers_bill': 'Gig Workers Bill',
        'rights_reserved': '© 2025 GigHala. Owned and operated by Calmic Sdn Bhd (Registration Number: 1466852W / 202201021155). All rights reserved.',
        'visitor_count': 'Total Visitors:',
        'ssm_registered': 'SSM Registered',
        'secure_payment': 'Secure Payment',

        # Homepage - Modals
        'login_title': 'Login',
        'register_title': 'Sign Up Free',
        'email': 'Email',
        'password': 'Password',
        'no_account': "Don't have an account?",
        'register_now': 'Sign up now',
        'full_name': 'Full Name',
        'username': 'Username',
        'phone_number': 'Phone Number',
        'ic_passport_no': 'IC / Passport No.',
        'ic_passport_hint': 'Enter your MyKad (12 digits) or passport number',
        'location': 'Location',
        'select_location': 'Select location',
        'register_as': 'Register as',
        'freelancer_find_work': 'Freelancer (Find Work)',
        'client_post_work': 'Client (Post Work)',
        'both': 'Both',
        'have_account': 'Already have an account?',
        'login_now': 'Login',
        'payment_received_popup': 'Payment Received!',

        # Category Names
        'cat_design': 'Design & Creative',
        'cat_writing': 'Writing & Translation',
        'cat_video': 'Video & Animation',
        'cat_web': 'Web Development',
        'cat_marketing': 'Digital Marketing',
        'cat_tutoring': 'Tutoring',
        'cat_content': 'Content Creation',
        'cat_admin': 'Admin Support',
        'cat_general': 'General Works',
        'cat_virtual_assistant': 'Virtual Assistant',
        'cat_delivery': 'Delivery & Logistics',
        'cat_micro_tasks': 'Micro-Tasks & Daily',
        'cat_events': 'Event Management',
        'cat_caregiving': 'Caregiving & Services',
        'cat_photography': 'Photography & Videography',
        'cat_creative_other': 'Other Creative',

        # Category Translations (for API)
        'category_design': 'Design',
        'category_writing': 'Writing & Translation',
        'category_video': 'Video & Animation',
        'category_tutoring': 'Tutoring & Education',
        'category_content': 'Content Creation',
        'category_web': 'Web Development',
        'category_marketing': 'Digital Marketing',
        'category_admin': 'Admin & Virtual Assistant',
        'category_general': 'General Works',
        'category_programming': 'Programming & Tech',
        'category_consulting': 'Business Consulting',
        'category_engineering': 'Engineering Services',
        'category_music': 'Music & Audio',
        'category_photography': 'Photography',
        'category_finance': 'Finance & Bookkeeping',
        'category_crafts': 'Crafts & Handmade',
        'category_garden': 'Home & Garden',
        'category_coaching': 'Life Coaching',
        'category_data': 'Data Analysis',
        'category_pets': 'Pet Services',
        'category_handyman': 'Handyman & Repairs',
        'category_tours': 'Tour Guiding',
        'category_events': 'Event Planning',
        'category_online-selling': 'Online Selling',
        'category_virtual-assistant': 'Virtual Assistant',

        # Gigs Page
        'search': 'Search',
        'keywords_placeholder': 'Keywords...',
        'all_categories_filter': 'All Categories',
        'design_cat': 'Design',
        'tutoring_education': 'Tutoring & Education',
        'admin_virtual_assistant': 'Admin & Virtual Assistant',
        'budget_rm': 'Budget (RM)',
        'min_placeholder': 'Min',
        'max_placeholder': 'Max',
        'search_gig_btn': 'Search Gigs',
        'gigs_found': 'gigs found',
        'sort_by': 'Sort by:',
        'newest': 'Newest',
        'budget_highest': 'Highest Budget',
        'budget_lowest': 'Lowest Budget',
        'loading_gigs': 'Loading gigs...',
        'no_gigs_found': 'No gigs found',
        'no_gigs_desc': 'Try changing filters or check back later for new opportunities',
        'error_loading_gigs': 'Error loading gigs',
        'reload_page': 'Please reload the page',
        'flexible': 'Flexible',
        'budget': 'Budget',

        # Post Gig Page
        'post_new_gig': 'Post a New Gig',
        'edit_gig': 'Edit Gig',
        'find_freelancer_subtitle': 'Find the right freelancer for your project',
        'update_gig_subtitle': 'Update your gig information',
        'gig_information': 'Gig Information',
        'gig_title': 'Gig Title',
        'gig_title_placeholder': 'e.g., Design a logo for my halal restaurant',
        'gig_title_hint': 'Write a clear and attention-grabbing title',
        'description': 'Description',
        'description_placeholder': 'Describe your project in detail. Include requirements, deliverables, and specific instructions.',
        'category': 'Category',
        'budget_duration': 'Budget & Duration',
        'budget_min': 'Minimum Budget (RM)',
        'budget_max': 'Maximum Budget (RM)',
        'approved_budget': 'Approved Budget (RM)',
        'approved_budget_hint': 'Actual approved amount',
        'approved_budget_help': 'Optional: Enter the exact amount approved for this gig',
        'duration': 'Duration',
        'select_duration': 'Select duration',
        'duration_1_3_days': '1-3 days',
        'duration_1_week': '1 week',
        'duration_2_weeks': '2 weeks',
        'duration_1_month': '1 month',
        'duration_ongoing': 'Ongoing',
        'deadline': 'Deadline',
        'location_skills': 'Location & Skills',
        'type_or_select_location': 'Type or select location',
        'all_locations_option': 'All locations',
        'remote_option': 'Remote',
        'skills_required': 'Required Skills',
        'type_skill_enter': 'Type skill and press Enter',
        'press_enter_add_skill': 'Press Enter to add each skill',
        'reference_photos': 'Reference Photos',
        'upload_photos_optional': 'Upload Files (Optional)',
        'click_to_upload': 'Click to upload',
        'drag_photos_here': 'or drag files here',
        'photo_format_hint': 'PNG, JPG, WEBP, PDF or Word (Max 5MB per file, max 5 files)',
        'additional_options': 'Additional Options',
        'remote_work': 'Remote Work',
        'remote_work_desc': 'Freelancer can work from anywhere',
        'halal_compliant': 'Halal Compliant',
        'halal_compliant_desc': 'Sharia-compliant project',
        'instant_payout_label': 'Instant Payout',
        'instant_payout_desc': 'Payment within 24 hours',
        'brand_partnership': 'Brand Partnership',
        'brand_partnership_desc': 'Collaboration with brand',
        'back_to_gig': 'Back to gig',
        'no_post_fee': 'No fee to post gig',
        'save_changes': 'Save Changes',
        'post_gig_btn': 'Post Gig',
        'please_select_category': 'Please select a category',
        'budget_max_error': 'Maximum budget must be greater than minimum budget',
        'processing': 'Processing...',
        'max_5_photos': 'Maximum 5 files allowed',
        'only_image_formats': 'Only PNG, JPG, WEBP, PDF or Word files allowed',
        'max_file_size_5mb': 'File size must be less than 5MB',
        
        # Messages & Chat
        'messages_page_title': 'Messages',
        'messages_page_subtitle': 'Communicate with clients and freelancers',
        'no_conversations_yet': 'No Conversations Yet',
        'start_conversation_hint': 'Start a conversation by applying to a gig or accepting an application',
        'no_messages_yet': 'No messages yet',
        'send_message': 'Send Message',
        'message_placeholder': 'Type your message here...',
        'type_message': 'Type a message...',
        'gig_reference': 'Reference:',
    }
}

def get_user_language():
    """Get current user's language preference"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return user.language if user and user.language else 'ms'
    return session.get('language', 'ms')

def t(key, **kwargs):
    """Translate a key to the user's language"""
    lang = get_user_language()
    translation = TRANSLATIONS.get(lang, TRANSLATIONS['ms']).get(key, key)
    # Replace placeholders
    for k, v in kwargs.items():
        translation = translation.replace('{' + k + '}', str(v))
    return translation

# Islamic (Hijri) month names in Malay and English
# Malay names follow Malaysia's official JAKIM (Jabatan Agama Islam Malaysia) standards
HIJRI_MONTHS = {
    'ms': ['Muharram', 'Safar', 'Rabiul Awal', 'Rabiul Akhir', 'Jumadil Awal', 'Jumadil Akhir',
           'Rajab', 'Syaaban', 'Ramadan', 'Syawal', 'Zulkaidah', 'Zulhijah'],
    'en': ['Muharram', 'Safar', 'Rabi al-Awwal', 'Rabi al-Thani', 'Jumada al-Awwal', 'Jumada al-Thani',
           'Rajab', 'Shaban', 'Ramadan', 'Shawwal', 'Dhul Qadah', 'Dhul Hijjah']
}

GREGORIAN_MONTHS = {
    'ms': ['Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun', 
           'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember'],
    'en': ['January', 'February', 'March', 'April', 'May', 'June',
           'July', 'August', 'September', 'October', 'November', 'December']
}

def get_dual_date(date_obj=None, lang=None):
    """Get formatted dual date (Gregorian and Hijri)"""
    if date_obj is None:
        date_obj = datetime.now()
    if lang is None:
        lang = get_user_language()

    # Gregorian date
    greg_month = GREGORIAN_MONTHS.get(lang, GREGORIAN_MONTHS['ms'])[date_obj.month - 1]
    gregorian = f"{date_obj.day} {greg_month} {date_obj.year}"

    # Convert to Hijri - Always use Malaysian (Malay) month names
    hijri = Gregorian(date_obj.year, date_obj.month, date_obj.day).to_hijri()
    hijri_month = HIJRI_MONTHS['ms'][hijri.month - 1]  # Force Malaysian style
    hijri_str = f"{hijri.day} {hijri_month} {hijri.year}H"

    return {'gregorian': gregorian, 'hijri': hijri_str, 'full': f"{gregorian} / {hijri_str}"}

def format_date_dual(date_obj, lang=None):
    """Format a specific date with both calendars"""
    if date_obj is None:
        return None
    if lang is None:
        lang = get_user_language()
    return get_dual_date(date_obj, lang)

# Make translation function and dates available in templates
@app.context_processor
def inject_translations():
    today_dual = get_dual_date()

    # Calculate unread message count for logged-in users
    unread_message_count = 0
    wallet = None
    total_gigs_accepted = 0
    total_gigs_posted = 0
    user = None

    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)

        # Get all non-archived conversations for the user
        conversations = Conversation.query.filter(
            ((Conversation.participant_1_id == user_id) & (Conversation.is_archived_by_1 == False)) |
            ((Conversation.participant_2_id == user_id) & (Conversation.is_archived_by_2 == False))
        ).all()

        # Count unread messages across all conversations
        for conv in conversations:
            unread_message_count += Message.query.filter_by(
                conversation_id=conv.id,
                is_read=False
            ).filter(Message.sender_id != user_id).count()

        # Get wallet balance
        if user:
            wallet = Wallet.query.filter_by(user_id=user_id).first()

            # Calculate total gigs posted (for clients)
            if user.user_type in ['client', 'both']:
                total_gigs_posted = Gig.query.filter_by(client_id=user_id).count()

            # Calculate total gigs accepted (for freelancers)
            if user.user_type in ['freelancer', 'both']:
                total_gigs_accepted = Application.query.filter_by(
                    freelancer_id=user_id,
                    status='accepted'
                ).count()

                # Also count gigs where user is directly assigned as freelancer
                if user.user_type == 'both':
                    client_accepted = Gig.query.filter_by(
                        freelancer_id=user_id
                    ).filter(Gig.status.in_(['in_progress', 'submitted', 'completed'])).count()
                    total_gigs_accepted += client_accepted

    return dict(
        t=t,
        lang=get_user_language(),
        today_gregorian=today_dual['gregorian'],
        today_hijri=today_dual['hijri'],
        today_dual=today_dual['full'],
        format_date_dual=format_date_dual,
        unread_message_count=unread_message_count,
        csrf_token=generate_csrf,
        user=user,
        wallet=wallet,
        total_gigs_accepted=total_gigs_accepted,
        total_gigs_posted=total_gigs_posted
    )

# Security headers middleware
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'"
    return response

# Input validation functions
def validate_password_strength(password):
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def validate_username(username):
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, "Username is valid"

def validate_phone(phone):
    """Validate Malaysian phone number format"""
    if not phone:
        return True, "Phone is optional"
    # Malaysian phone format: +60... or 01...
    if re.match(r'^(\+?60|0)[1-9]\d{7,9}$', phone):
        return True, "Phone is valid"
    return False, "Invalid Malaysian phone number format"

def validate_ic_number(ic_number):
    """
    Validate Malaysian IC/MyKad or passport number.
    This will be done by IC / Passport Verification in the system
    Returns (is_valid, error_message)
    """
    return True, ""

def validate_mykad_checkdigit(mykad):
    """
    Validate Malaysian MyKad check digit.
    Algorithm: Weights are [2,7,6,5,4,3,2,7,6,5,4,3]
    Check digit = 11 - (sum % 11), with special cases for 10->0 and 11->1
    """
    if not mykad or len(mykad) != 12 or not mykad.isdigit():
        return False
    
    try:
        weights = [2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3]
        total = sum(int(mykad[i]) * weights[i] for i in range(11))
        
        remainder = total % 11
        expected_check = 11 - remainder
        
        # Handle special cases
        if expected_check == 10:
            expected_check = 0
        elif expected_check == 11:
            expected_check = 1
        
        actual_check = int(mykad[11])
        return expected_check == actual_check
    except (ValueError, IndexError):
        return False

def sanitize_input(text, max_length=1000):
    """Sanitize text input to prevent injection attacks"""
    if not text:
        return text
    # Remove any potentially harmful characters
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text

def generate_phone_otp():
    """Generate a 6-digit OTP code for phone verification"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_phone_verification_sms(phone, otp_code):
    """
    Send verification SMS with OTP code to phone number
    Returns (success, message) tuple
    """
    if not twilio_client or not twilio_phone_number:
        return False, "SMS service is not configured"

    try:
        # Format phone number to E.164 format if needed
        if phone.startswith('01'):
            phone = '+6' + phone  # Convert 01X to +601X
        elif not phone.startswith('+'):
            phone = '+' + phone

        # Send SMS with OTP code
        message = twilio_client.messages.create(
            body=f"Your GigHala verification code is: {otp_code}. This code will expire in 10 minutes. Do not share this code with anyone.",
            from_=twilio_phone_number,
            to=phone
        )

        app.logger.info(f"Verification SMS sent to {phone}: {message.sid}")
        return True, "Verification code sent successfully"
    except Exception as e:
        app.logger.error(f"Failed to send verification SMS to {phone}: {str(e)}")
        return False, f"Failed to send SMS: {str(e)}"

def verify_phone_otp(user, submitted_code):
    """
    Verify OTP code for phone verification
    Returns (success, message) tuple
    """
    if not user.phone_verification_code:
        return False, "No verification code found. Please request a new code."

    # Check if code has expired (10 minutes)
    if user.phone_verification_expires and datetime.utcnow() > user.phone_verification_expires:
        return False, "Verification code has expired. Please request a new code."

    # Verify the code
    if user.phone_verification_code != submitted_code:
        return False, "Invalid verification code. Please try again."

    # Code is valid - mark phone as verified
    user.phone_verified = True
    user.phone_verified_at = datetime.utcnow()
    user.phone_verification_code = None
    user.phone_verification_expires = None

    return True, "Phone number verified successfully"

def generate_email_verification_token():
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)

def send_verification_email(user_email, token, username):
    """
    Send email verification link to user
    Returns (success, message) tuple
    """
    try:
        verification_url = f"{os.getenv('APP_URL', 'http://localhost:5000')}/verify-email?token={token}"

        subject = "Verify Your GigHala Email Address"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">Welcome to GigHala!</h2>
                    <p>Hi {username},</p>
                    <p>Thank you for registering with GigHala. Please verify your email address to activate your account.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}"
                           style="background-color: #2563eb; color: white; padding: 12px 30px;
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Verify Email Address
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{verification_url}">{verification_url}</a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        This verification link will expire in 24 hours.
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        If you didn't create a GigHala account, please ignore this email.
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        GigHala - Halal Gig Economy Platform
                    </p>
                </div>
            </body>
        </html>
        """

        # Send email using the email service
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content
        )

        if success:
            app.logger.info(f"Verification email sent to {user_email}")
            return True, "Verification email sent successfully"
        else:
            app.logger.error(f"Failed to send verification email to {user_email}")
            return False, "Failed to send verification email"
    except Exception as e:
        app.logger.error(f"Error sending verification email to {user_email}: {str(e)}")
        return False, f"Error sending email: {str(e)}"

def verify_email_token(token):
    """
    Verify email token and mark user as verified
    Returns (success, message, user) tuple
    """
    try:
        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            return False, "Invalid verification token", None

        # Check if token has expired (24 hours)
        if user.email_verification_expires and datetime.utcnow() > user.email_verification_expires:
            return False, "Verification link has expired. Please request a new one.", None

        # Check if already verified
        if user.is_verified:
            return True, "Email already verified", user

        # Mark user as verified
        user.is_verified = True
        user.email_verification_token = None
        user.email_verification_expires = None
        db.session.commit()

        app.logger.info(f"Email verified for user {user.username} ({user.email})")
        return True, "Email verified successfully", user
    except Exception as e:
        app.logger.error(f"Error verifying email token: {str(e)}")
        return False, f"Error verifying email: {str(e)}", None

def send_password_reset_email(user_email, token, username):
    """
    Send password reset link to user
    Returns (success, message) tuple
    """
    try:
        reset_url = f"{os.getenv('APP_URL', 'http://localhost:5000')}/reset-password?token={token}"

        subject = "Reset Your GigHala Password"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">Password Reset Request</h2>
                    <p>Hi {username},</p>
                    <p>We received a request to reset your password for your GigHala account.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}"
                           style="background-color: #2563eb; color: white; padding: 12px 30px;
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{reset_url}">{reset_url}</a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        This password reset link will expire in 24 hours.
                    </p>
                    <p style="color: #d32f2f; font-size: 14px; font-weight: bold;">
                        If you didn't request a password reset, please ignore this email and your password will remain unchanged.
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        GigHala - Halal Gig Economy Platform
                    </p>
                </div>
            </body>
        </html>
        """

        # Send email using the email service
        success = email_service.send_email(
            to_email=user_email,
            subject=subject,
            html_content=html_content
        )

        if success:
            app.logger.info(f"Password reset email sent to {user_email}")
            return True, "Password reset email sent successfully"
        else:
            app.logger.error(f"Failed to send password reset email to {user_email}")
            return False, "Failed to send password reset email"
    except Exception as e:
        app.logger.error(f"Error sending password reset email to {user_email}: {str(e)}")
        return False, f"Error sending email: {str(e)}"

def verify_password_reset_token(token):
    """
    Verify password reset token
    Returns (success, message, user) tuple
    """
    try:
        user = User.query.filter_by(password_reset_token=token).first()

        if not user:
            return False, "Invalid password reset token", None

        # Check if token has expired (24 hours)
        if user.password_reset_expires and datetime.utcnow() > user.password_reset_expires:
            return False, "Password reset link has expired. Please request a new one.", None

        return True, "Token is valid", user
    except Exception as e:
        app.logger.error(f"Error verifying password reset token: {str(e)}")
        return False, f"Error verifying token: {str(e)}", None

def send_transaction_sms_notification(phone, message_text):
    """
    Send SMS notification for transaction events
    Returns (success, message) tuple
    """
    if not twilio_client or not twilio_phone_number:
        return False, "SMS service is not configured"

    if not phone:
        return False, "No phone number provided"

    try:
        # Format phone number to E.164 format if needed
        if phone.startswith('01'):
            phone = '+6' + phone  # Convert 01X to +601X
        elif not phone.startswith('+'):
            phone = '+' + phone

        message = twilio_client.messages.create(
            body=message_text,
            from_=twilio_phone_number,
            to=phone
        )

        app.logger.info(f"Transaction SMS sent to {phone}: {message.sid}")
        return True, "Notification sent successfully"
    except Exception as e:
        app.logger.error(f"Failed to send transaction SMS to {phone}: {str(e)}")
        return False, f"Failed to send SMS: {str(e)}"

def send_interaction_notification(user, subject, message, html_content=None, text_content=None, sms_message=None):
    """
    Send comprehensive notification via email and SMS for client-worker interactions

    Args:
        user: User object (recipient)
        subject: Notification subject/title
        message: Short message for in-app notification
        html_content: HTML email body (optional, will be auto-generated if not provided)
        text_content: Plain text email body (optional, will be auto-generated if not provided)
        sms_message: SMS message (optional, will use message if not provided)

    Returns:
        dict: Status of email and SMS sending
    """
    result = {
        'email_sent': False,
        'sms_sent': False,
        'errors': []
    }

    # Generate default HTML and text content if not provided
    if not html_content:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2ecc71; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{subject}</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                </div>
                <div class="footer">
                    <p>GigHala - Your Trusted Halal Gig Platform</p>
                    <p>This is an automated notification. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

    if not text_content:
        text_content = f"{subject}\n\n{message}\n\n---\nGigHala - Your Trusted Halal Gig Platform"

    # Send email if user has email
    if user and user.email:
        try:
            email_service.send_single_email(
                to_email=user.email,
                to_name=user.full_name or user.username,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            result['email_sent'] = True
            app.logger.info(f"Interaction email sent to user {user.id}: {subject}")
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            result['errors'].append(error_msg)
            app.logger.error(f"Failed to send interaction email to user {user.id}: {str(e)}")

    # Send SMS if user has verified phone
    if user and user.phone and user.phone_verified:
        try:
            sms_text = sms_message if sms_message else f"GigHala: {message}"
            send_transaction_sms_notification(user.phone, sms_text)
            result['sms_sent'] = True
            app.logger.info(f"Interaction SMS sent to user {user.id}: {subject}")
        except Exception as e:
            error_msg = f"Failed to send SMS: {str(e)}"
            result['errors'].append(error_msg)
            app.logger.error(f"Failed to send interaction SMS to user {user.id}: {str(e)}")

    return result

def contains_blocked_contact_info(text):
    """
    Check if message contains phone numbers or email addresses to prevent phishing.
    Returns (is_blocked, reason) tuple.
    """
    if not text:
        return False, None

    # Email pattern - comprehensive regex for email detection
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    # Phone number patterns - detect various formats
    phone_patterns = [
        r'\+?\d{1,4}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}',  # International formats
        r'\b0\d{1,2}[\s-]?\d{3,4}[\s-]?\d{4}\b',  # Malaysian local format (01X-XXX-XXXX)
        r'\b\d{3}[\s-]\d{3}[\s-]\d{4}\b',  # Common format (XXX-XXX-XXXX)
        r'\b\d{10,}\b',  # 10+ consecutive digits
        r'\+60[\s-]?\d{1,2}[\s-]?\d{3,4}[\s-]?\d{4}',  # Malaysian international (+60)
    ]

    # Check for email addresses
    if re.search(email_pattern, text):
        return True, "Email addresses are not allowed in messages to prevent phishing"

    # Check for phone numbers
    for pattern in phone_patterns:
        if re.search(pattern, text):
            return True, "Phone numbers are not allowed in messages to prevent phishing"

    # Check for common contact info indicators (case-insensitive)
    contact_keywords = [
        r'\b(email|e-mail)\s*(me|is|:|@)',
        r'\b(call|text|whatsapp|telegram|viber|wechat)\s*(me|at)',
        r'\bcontact\s*(me|at|via)',
        r'\bphone\s*(number|is|:|#)',
        r'\breach\s*(me|out)\s*(at|via|on)',
    ]

    for keyword_pattern in contact_keywords:
        if re.search(keyword_pattern, text, re.IGNORECASE):
            return True, "Messages suggesting off-platform contact are not allowed to prevent phishing"

    return False, None

# Rate limiting decorator
def rate_limit(max_attempts=5, window_minutes=15, lockout_minutes=30):
    """Rate limit decorator to prevent brute force attacks"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            identifier = request.remote_addr
            current_time = datetime.utcnow()

            if identifier not in login_attempts:
                login_attempts[identifier] = {'count': 0, 'first_attempt': current_time, 'locked_until': None}

            attempt_data = login_attempts[identifier]

            # Check if account is locked
            if attempt_data['locked_until'] and current_time < attempt_data['locked_until']:
                remaining = int((attempt_data['locked_until'] - current_time).total_seconds() / 60)
                return jsonify({'error': f'Too many failed attempts. Account locked for {remaining} more minutes'}), 429

            # Reset if window has passed
            if (current_time - attempt_data['first_attempt']).total_seconds() > window_minutes * 60:
                attempt_data['count'] = 0
                attempt_data['first_attempt'] = current_time
                attempt_data['locked_until'] = None

            # Check if rate limit exceeded
            if attempt_data['count'] >= max_attempts:
                attempt_data['locked_until'] = current_time + timedelta(minutes=lockout_minutes)
                return jsonify({'error': f'Too many failed attempts. Account locked for {lockout_minutes} minutes'}), 429

            # Increment attempt counter
            attempt_data['count'] += 1

            return f(*args, **kwargs)
        return wrapped
    return decorator

def reset_rate_limit(identifier):
    """Reset rate limit for successful login"""
    if identifier in login_attempts:
        login_attempts[identifier] = {'count': 0, 'first_attempt': datetime.utcnow(), 'locked_until': None}

# Commission calculation function
def calculate_commission(amount):
    """
    Calculate tiered commission based on transaction amount

    Tier 1: MYR 0 - 500     → 15% commission
    Tier 2: MYR 501 - 2,000  → 10% commission
    Tier 3: MYR 2,001+       → 5% commission

    Args:
        amount (float): Transaction amount in MYR

    Returns:
        float: Commission amount
    """
    if amount <= 500:
        return round(amount * 0.15, 2)  # 15%
    elif amount <= 2000:
        return round(amount * 0.10, 2)  # 10%
    else:
        return round(amount * 0.05, 2)  # 5%

def calculate_socso(net_earnings):
    """
    Calculate SOCSO contribution as per Gig Workers Bill 2025

    SOCSO Rate: 1.25% of net earnings (after platform commission)
    Required by Self-Employment Social Security Scheme (SESKSO/SKSPS)

    Args:
        net_earnings (float): Net earnings after platform commission in MYR

    Returns:
        float: SOCSO contribution amount rounded to 2 decimal places (sen)
    """
    if net_earnings <= 0:
        return 0.0
    return round(net_earnings * 0.0125, 2)  # 1.25%

def create_socso_contribution(freelancer_id, gross_amount, platform_commission, net_earnings,
                               contribution_type='escrow_release', gig_id=None,
                               transaction_id=None, payout_id=None):
    """
    Create a SOCSO contribution record for compliance tracking

    Args:
        freelancer_id (int): ID of the freelancer
        gross_amount (float): Original gig/transaction amount
        platform_commission (float): Platform fee deducted
        net_earnings (float): Amount after commission, before SOCSO
        contribution_type (str): Type of contribution ('escrow_release', 'payout', 'transaction')
        gig_id (int, optional): Related gig ID
        transaction_id (int, optional): Related transaction ID
        payout_id (int, optional): Related payout ID

    Returns:
        SocsoContribution: The created contribution record
    """
    socso_amount = calculate_socso(net_earnings)
    final_payout = round(net_earnings - socso_amount, 2)

    # Get current month and year for reporting
    now = datetime.utcnow()
    contribution_month = now.strftime('%Y-%m')
    contribution_year = now.year

    contribution = SocsoContribution(
        freelancer_id=freelancer_id,
        transaction_id=transaction_id,
        payout_id=payout_id,
        gig_id=gig_id,
        gross_amount=gross_amount,
        platform_commission=platform_commission,
        net_earnings=net_earnings,
        socso_amount=socso_amount,
        final_payout=final_payout,
        contribution_month=contribution_month,
        contribution_year=contribution_year,
        contribution_type=contribution_type
    )

    db.session.add(contribution)
    return contribution

def check_socso_compliance(user):
    """
    Check if a user is compliant with SOCSO requirements

    Args:
        user (User): User object to check

    Returns:
        tuple: (is_compliant: bool, reason: str)
    """
    # Only freelancers need SOCSO compliance
    if user.user_type not in ['freelancer', 'both']:
        return (True, 'Not a freelancer')

    # Check if IC number is provided
    if not user.ic_number or user.ic_number.strip() == '':
        return (False, 'IC number is required for SOCSO registration')

    # Check if SOCSO consent has been given
    if not user.socso_consent:
        return (False, 'SOCSO consent is required')

    # Mark as data complete if all checks pass
    if not user.socso_data_complete:
        user.socso_data_complete = True
        db.session.commit()

    return (True, 'SOCSO compliant')

def generate_receipt_number(receipt_type='RCP'):
    """Generate a unique receipt number with collision resistance"""
    import uuid
    prefix_map = {
        'escrow_funding': 'ESC-RCP',
        'payment': 'PAY-RCP',
        'refund': 'REF-RCP',
        'payout': 'OUT-RCP'
    }
    prefix = prefix_map.get(receipt_type, 'RCP')
    date_part = datetime.utcnow().strftime('%Y%m%d')
    unique_part = uuid.uuid4().hex[:8].upper()
    receipt_number = f"{prefix}-{date_part}-{unique_part}"
    
    max_attempts = 5
    for attempt in range(max_attempts):
        existing = Receipt.query.filter_by(receipt_number=receipt_number).first()
        if not existing:
            return receipt_number
        unique_part = uuid.uuid4().hex[:8].upper()
        receipt_number = f"{prefix}-{date_part}-{unique_part}"
    
    return receipt_number

def generate_escrow_number():
    """Generate a unique escrow number with collision resistance"""
    import uuid
    date_part = datetime.utcnow().strftime('%Y%m%d')
    unique_part = uuid.uuid4().hex[:8].upper()
    escrow_number = f"ESC-{date_part}-{unique_part}"

    max_attempts = 5
    for attempt in range(max_attempts):
        existing = Escrow.query.filter_by(escrow_number=escrow_number).first()
        if not existing:
            return escrow_number
        unique_part = uuid.uuid4().hex[:8].upper()
        escrow_number = f"ESC-{date_part}-{unique_part}"

    return escrow_number

def create_escrow_receipt(escrow, gig, payment_method='fpx'):
    """Create receipts for escrow funding for both client and freelancer (idempotent - only creates if none exists)"""
    # Check if receipts already exist
    existing_client_receipt = Receipt.query.filter_by(
        escrow_id=escrow.id,
        receipt_type='escrow_funding',
        user_id=escrow.client_id
    ).first()

    if existing_client_receipt:
        app.logger.info(f"Receipts already exist for escrow {escrow.id}: {existing_client_receipt.receipt_number}")
        return existing_client_receipt

    # Create receipt for client (payer)
    client_receipt = Receipt(
        receipt_number=generate_receipt_number('escrow_funding'),
        receipt_type='escrow_funding',
        user_id=escrow.client_id,
        gig_id=gig.id,
        escrow_id=escrow.id,
        amount=escrow.amount,
        platform_fee=escrow.platform_fee,
        total_amount=escrow.amount,
        payment_method=payment_method,
        payment_reference=escrow.payment_reference,
        description=f"Escrow funding for gig: {gig.title}"
    )
    db.session.add(client_receipt)

    # Create receipt for freelancer (recipient) if freelancer is assigned
    if gig.freelancer_id:
        freelancer_receipt = Receipt(
            receipt_number=generate_receipt_number('escrow_funding'),
            receipt_type='escrow_funding',
            user_id=gig.freelancer_id,
            gig_id=gig.id,
            escrow_id=escrow.id,
            amount=escrow.amount,
            platform_fee=escrow.platform_fee,
            total_amount=escrow.amount,
            payment_method=payment_method,
            payment_reference=escrow.payment_reference,
            description=f"Escrow funding for gig: {gig.title}"
        )
        db.session.add(freelancer_receipt)

    return client_receipt

# Login required decorator for API routes
def login_required(f):
    """Decorator to require user authentication for API routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized - Please login'}), 401

        # Verify user still exists in database
        # User class is defined later in this file, so we access it from globals
        user = globals()['User'].query.get(session['user_id'])
        if not user:
            session.clear()
            return jsonify({'error': 'Session expired - Please login again'}), 401

        return f(*args, **kwargs)
    return decorated_function

# Login required decorator for page routes (redirects to home page)
def page_login_required(f):
    """Decorator to require user authentication for page routes - redirects to home"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')

        # Verify user still exists in database
        # User class is defined later in this file, so we access it from globals
        user = globals()['User'].query.get(session['user_id'])
        if not user:
            session.clear()
            flash('Sesi anda telah tamat tempoh. Sila log masuk semula.', 'info')
            return redirect('/')

        return f(*args, **kwargs)
    return decorated_function

# Admin authentication decorator
def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Log unauthorized access attempt
            from security_logger import security_logger
            if security_logger:
                security_logger.log_authorization(
                    resource_type='admin_endpoint',
                    resource_id=f.__name__,
                    action=f'Attempted to access admin endpoint: {f.__name__}',
                    status='blocked',
                    message='Unauthorized - not logged in'
                )
            return jsonify({'error': 'Unauthorized - Please login'}), 401

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            # Log permission denied
            from security_logger import security_logger
            if security_logger:
                security_logger.log_authorization(
                    resource_type='admin_endpoint',
                    resource_id=f.__name__,
                    action=f'Non-admin user attempted to access admin endpoint: {f.__name__}',
                    status='blocked',
                    message=f'Forbidden - User {user.username if user else "unknown"} is not an admin'
                )
            return jsonify({'error': 'Forbidden - Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function

def billing_admin_required(f):
    """Decorator to require billing/accountant admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Log unauthorized access attempt
            from security_logger import security_logger
            if security_logger:
                security_logger.log_authorization(
                    resource_type='billing_endpoint',
                    resource_id=f.__name__,
                    action=f'Attempted to access billing endpoint: {f.__name__}',
                    status='blocked',
                    message='Unauthorized - not logged in'
                )
            return jsonify({'error': 'Unauthorized - Please login'}), 401

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            # Log permission denied
            from security_logger import security_logger
            if security_logger:
                security_logger.log_authorization(
                    resource_type='billing_endpoint',
                    resource_id=f.__name__,
                    action=f'Non-admin user attempted to access billing endpoint: {f.__name__}',
                    status='blocked',
                    message=f'Forbidden - User {user.username if user else "unknown"} is not an admin'
                )
            return jsonify({'error': 'Forbidden - Admin access required'}), 403

        # Check if user has billing or super_admin role
        if user.admin_role not in ['super_admin', 'billing']:
            # Log permission denied
            from security_logger import security_logger
            if security_logger:
                security_logger.log_authorization(
                    resource_type='billing_endpoint',
                    resource_id=f.__name__,
                    action=f'Admin user without billing role attempted to access billing endpoint: {f.__name__}',
                    status='blocked',
                    message=f'Forbidden - User {user.username} (role: {user.admin_role}) does not have billing access'
                )
            return jsonify({'error': 'Forbidden - Billing/Accounting access required'}), 403

        return f(*args, **kwargs)
    return decorated_function

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    phone = db.Column(db.String(20))
    full_name = db.Column(db.String(120))
    user_type = db.Column(db.String(20), default='freelancer')  # freelancer, client, both
    location = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=True)  # Geolocation latitude
    longitude = db.Column(db.Float, nullable=True)  # Geolocation longitude
    skills = db.Column(db.Text)  # JSON string
    bio = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    completed_gigs = db.Column(db.Integer, default=0)
    profile_video = db.Column(db.String(255))
    language = db.Column(db.String(5), default='ms')  # ms (Malay) or en (English)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))  # Token for email verification
    email_verification_expires = db.Column(db.DateTime)  # When verification token expires
    password_reset_token = db.Column(db.String(100))  # Token for password reset
    password_reset_expires = db.Column(db.DateTime)  # When password reset token expires
    halal_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    admin_role = db.Column(db.String(50))  # super_admin, billing, moderator, etc.
    admin_permissions = db.Column(db.Text)  # JSON string of specific permissions
    # IC Number (Malaysian Identity Card - 12 digits) or Passport Number (up to 20 chars)
    ic_number = db.Column(db.String(20))
    # Bank account details for payment transfers
    bank_name = db.Column(db.String(100))
    bank_account_number = db.Column(db.String(30))
    bank_account_holder = db.Column(db.String(120))
    # Stripe customer ID for saved payment methods
    stripe_customer_id = db.Column(db.String(100))  # Stripe customer ID (cus_xxx)
    # OAuth fields for social login
    oauth_provider = db.Column(db.String(20))  # google, apple, microsoft, or null for regular
    oauth_id = db.Column(db.String(255))  # User ID from OAuth provider
    # SOCSO compliance fields (Gig Workers Bill 2025)
    socso_registered = db.Column(db.Boolean, default=False)  # Whether freelancer is registered with SOCSO
    socso_consent = db.Column(db.Boolean, default=False)  # User consent to SOCSO deductions
    socso_consent_date = db.Column(db.DateTime)  # When consent was given
    socso_data_complete = db.Column(db.Boolean, default=False)  # IC number and required data available
    socso_membership_number = db.Column(db.String(20))  # SOCSO membership number
    # Two-Factor Authentication (2FA) fields
    totp_secret = db.Column(db.String(32))  # TOTP secret key for 2FA
    totp_enabled = db.Column(db.Boolean, default=False)  # Whether 2FA is enabled
    totp_enabled_at = db.Column(db.DateTime)  # When 2FA was enabled
    # Phone verification fields
    phone_verified = db.Column(db.Boolean, default=False)  # Whether phone number is verified
    phone_verification_code = db.Column(db.String(6))  # OTP code for phone verification
    phone_verification_expires = db.Column(db.DateTime)  # When verification code expires
    phone_verified_at = db.Column(db.DateTime)  # When phone was verified
    # Additional SOCSO registration fields (required for SESKSO compliance)
    date_of_birth = db.Column(db.Date)  # Date of birth
    gender = db.Column(db.String(10))  # Male, Female, Other
    marital_status = db.Column(db.String(20))  # Single, Married, Divorced, Widowed
    nationality = db.Column(db.String(50), default='Malaysian')  # Nationality
    race = db.Column(db.String(50))  # Malay, Chinese, Indian, Other
    address_line1 = db.Column(db.String(255))  # Street address line 1
    address_line2 = db.Column(db.String(255))  # Street address line 2 (optional)
    postcode = db.Column(db.String(10))  # Postal code
    city = db.Column(db.String(100))  # City
    state = db.Column(db.String(100))  # State/Province
    country = db.Column(db.String(100), default='Malaysia')  # Country
    self_employment_start_date = db.Column(db.Date)  # Date started self-employment
    monthly_income_range = db.Column(db.String(50))  # Income bracket for SOCSO categorization
    socso_registration_date = db.Column(db.DateTime)  # When registered for SOCSO via platform
    # SOCSO Portal Submission Tracking
    socso_submitted_to_portal = db.Column(db.Boolean, default=False)  # Whether submitted to SOCSO ASSIST Portal
    socso_portal_submission_date = db.Column(db.DateTime)  # When submitted to SOCSO portal
    socso_portal_reference_number = db.Column(db.String(50))  # Reference number from SOCSO portal (if any)

class EmailHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_email = db.Column(db.String(120), nullable=False)
    new_email = db.Column(db.String(120), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))

class EmailDigestLog(db.Model):
    """Tracks email digest sends (e.g., new gigs notifications)"""
    id = db.Column(db.Integer, primary_key=True)
    digest_type = db.Column(db.String(50), nullable=False)  # 'new_gigs', 'weekly_summary', etc.
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    recipient_count = db.Column(db.Integer, default=0)  # Number of emails sent
    gig_count = db.Column(db.Integer, default=0)  # Number of gigs included in digest
    success = db.Column(db.Boolean, default=True)  # Whether send was successful
    error_message = db.Column(db.Text)  # Error message if failed

class EmailSendLog(db.Model):
    """Tracks all email sends for auditing and debugging"""
    __tablename__ = 'email_send_log'
    id = db.Column(db.Integer, primary_key=True)
    email_type = db.Column(db.String(50), nullable=False)  # 'admin_bulk', 'admin_single', 'digest', 'transactional'
    subject = db.Column(db.String(500))
    sender_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who sent (if applicable)
    recipient_count = db.Column(db.Integer, default=0)
    successful_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    recipient_type = db.Column(db.String(50))  # 'all', 'freelancers', 'clients', 'selected'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    brevo_message_ids = db.Column(db.Text)  # JSON array of message IDs from Brevo
    failed_recipients = db.Column(db.Text)  # JSON array of failed email addresses

    sender = db.relationship('User', foreign_keys=[sender_user_id], backref='sent_emails')

class Gig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_code = db.Column(db.String(20), unique=True, nullable=True)  # Unique readable ID like GIG-00001
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    budget_min = db.Column(db.Float, nullable=False)
    budget_max = db.Column(db.Float, nullable=False)
    approved_budget = db.Column(db.Float)  # Actual amount approved by client
    duration = db.Column(db.String(50))  # e.g., "1-3 days", "1 week"
    location = db.Column(db.String(100))
    latitude = db.Column(db.Float, nullable=True)  # Geolocation latitude
    longitude = db.Column(db.Float, nullable=True)  # Geolocation longitude
    is_remote = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='open')  # open, in_progress, pending_review, completed, cancelled, blocked
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    agreed_amount = db.Column(db.Float)
    halal_compliant = db.Column(db.Boolean, default=True)
    halal_verified = db.Column(db.Boolean, default=False)
    is_instant_payout = db.Column(db.Boolean, default=False)
    is_brand_partnership = db.Column(db.Boolean, default=False)
    skills_required = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deadline = db.Column(db.DateTime)
    views = db.Column(db.Integer, default=0)
    applications = db.Column(db.Integer, default=0)
    cancellation_reason = db.Column(db.Text)  # Reason for cancellation
    cancelled_at = db.Column(db.DateTime)  # When the gig was cancelled
    blocked_at = db.Column(db.DateTime)  # When the gig was blocked
    blocked_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who blocked it
    block_reason = db.Column(db.Text)  # Reason for blocking
    report_count = db.Column(db.Integer, default=0)  # Number of reports received

class GigReport(db.Model):
    """User reports for flagging inappropriate or haram content in gigs"""
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.String(50), nullable=False)  # haram_content, inappropriate, spam, fraud, other
    description = db.Column(db.Text)  # Detailed explanation from reporter
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, dismissed, action_taken
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who reviewed
    reviewed_at = db.Column(db.DateTime)  # When it was reviewed
    admin_notes = db.Column(db.Text)  # Admin's notes on the report
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    gig = db.relationship('Gig', backref='reports')
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='gig_reports_made')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='gig_reports_reviewed')

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    proposed_price = db.Column(db.Float)
    video_pitch = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    work_submitted = db.Column(db.Boolean, default=False)  # Track if work has been submitted
    work_submission_date = db.Column(db.DateTime)  # When work was submitted
    completion_notes = db.Column(db.Text)  # Freelancer's notes when marking work as completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, nullable=False)
    socso_amount = db.Column(db.Float, default=0.0)  # SOCSO contribution (1.25% of net_amount)
    payment_method = db.Column(db.String(50))  # ipay88, bank_transfer, touch_n_go
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __table_args__ = (
        db.UniqueConstraint('gig_id', 'reviewer_id', name='unique_review_per_gig'),
    )
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MicroTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reward = db.Column(db.Float, nullable=False)
    task_type = db.Column(db.String(50))  # review, survey, content_creation
    status = db.Column(db.String(20), default='available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reward_amount = db.Column(db.Float, default=10.0)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VisitorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    path = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    referrer = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SiteStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    held_balance = db.Column(db.Float, default=0.0, nullable=False)
    total_earned = db.Column(db.Float, default=0.0, nullable=False)
    total_spent = db.Column(db.Float, default=0.0, nullable=False)
    currency = db.Column(db.String(3), default='MYR', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, issued, paid, cancelled, refunded
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    due_date = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    # Freelancer invoice submission fields
    invoice_submitted = db.Column(db.Boolean, default=False)
    freelancer_invoice_number = db.Column(db.String(100))
    freelancer_invoice_date = db.Column(db.DateTime)
    freelancer_submitted_at = db.Column(db.DateTime)
    freelancer_invoice_file = db.Column(db.String(255))
    freelancer_invoice_notes = db.Column(db.Text)

class Receipt(db.Model):
    """Model for storing payment receipts for escrow funding and other payments"""
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    receipt_type = db.Column(db.String(30), nullable=False)  # escrow_funding, payment, refund, payout
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'))
    escrow_id = db.Column(db.Integer, db.ForeignKey('escrow.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    amount = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert receipt to dictionary for JSON response"""
        return {
            'id': self.id,
            'receipt_number': self.receipt_number,
            'receipt_type': self.receipt_type,
            'user_id': self.user_id,
            'gig_id': self.gig_id,
            'escrow_id': self.escrow_id,
            'invoice_id': self.invoice_id,
            'amount': self.amount,
            'platform_fee': self.platform_fee,
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Payout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payout_number = db.Column(db.String(50), unique=True, nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    socso_amount = db.Column(db.Float, default=0.0)  # SOCSO contribution (1.25% of amount)
    net_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # bank_transfer, fpx, touch_n_go, grab_pay, boost
    account_number = db.Column(db.String(100))
    account_name = db.Column(db.String(200))
    bank_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed, cancelled
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    failure_reason = db.Column(db.Text)
    admin_notes = db.Column(db.Text)

class PaymentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    payout_id = db.Column(db.Integer, db.ForeignKey('payout.id'))
    type = db.Column(db.String(30), nullable=False)  # deposit, withdrawal, payment, refund, commission, payout, hold, release, socso
    amount = db.Column(db.Float, nullable=False)
    socso_amount = db.Column(db.Float, default=0.0)  # SOCSO contribution amount
    balance_before = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    reference_number = db.Column(db.String(100))
    payment_gateway = db.Column(db.String(50))
    gateway_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StripeWebhookLog(db.Model):
    """Log all Stripe webhook events for debugging and auditing"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100), unique=True, nullable=False)  # Stripe event ID
    event_type = db.Column(db.String(100), nullable=False)  # e.g., checkout.session.completed
    payload = db.Column(db.Text)  # Full event payload (JSON)
    processed = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)  # Error if processing failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WorkPhoto(db.Model):
    """Model for storing work photos uploaded by freelancers and clients"""
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploader_type = db.Column(db.String(20), nullable=False)  # 'freelancer' or 'client'
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    caption = db.Column(db.Text)
    upload_stage = db.Column(db.String(50), default='work_in_progress')  # work_in_progress, completed, revision
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert work photo to dictionary for JSON response"""
        return {
            'id': self.id,
            'gig_id': self.gig_id,
            'uploader_id': self.uploader_id,
            'uploader_type': self.uploader_type,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_url': f'/uploads/work_photos/{self.filename}',
            'file_size': self.file_size,
            'caption': self.caption,
            'upload_stage': self.upload_stage,
            'created_at': self.created_at.isoformat()
        }

class GigPhoto(db.Model):
    """Model for storing reference photos uploaded by clients when posting gigs"""
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # in bytes
    caption = db.Column(db.Text)
    photo_type = db.Column(db.String(50), default='reference')  # reference, example, inspiration
    mime_type = db.Column(db.String(100))  # MIME type of the file (image/png, application/pdf, etc.)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert gig photo to dictionary for JSON response"""
        return {
            'id': self.id,
            'gig_id': self.gig_id,
            'uploader_id': self.uploader_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_url': f'/uploads/gig_photos/{self.filename}',
            'file_size': self.file_size,
            'caption': self.caption,
            'photo_type': self.photo_type,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat()
        }

class SiteSettings(db.Model):
    """Model for storing site-wide settings including payment gateway preferences"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

def get_site_setting(key, default=None):
    """Get a site setting value"""
    setting = SiteSettings.query.filter_by(key=key).first()
    return setting.value if setting else default

def set_site_setting(key, value, description=None, user_id=None):
    """Set a site setting value"""
    setting = SiteSettings.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
        if user_id:
            setting.updated_by = user_id
    else:
        setting = SiteSettings(key=key, value=value, description=description, updated_by=user_id)
        db.session.add(setting)
    db.session.commit()
    return setting

def get_active_payment_gateway():
    """Get the currently active payment gateway"""
    return get_site_setting('payment_gateway', 'stripe')

class Escrow(db.Model):
    """Model for tracking escrow payments between clients and freelancers"""
    id = db.Column(db.Integer, primary_key=True)
    escrow_number = db.Column(db.String(50), unique=True, nullable=False)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default='pending')
    payment_reference = db.Column(db.String(100))
    payment_gateway = db.Column(db.String(50))  # stripe, payhalal, bank_transfer
    refunded_amount = db.Column(db.Float, default=0.0)  # Track partial refunds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    funded_at = db.Column(db.DateTime)
    released_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    dispute_reason = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    
    def to_dict(self):
        """Convert escrow to dictionary for JSON response"""
        # Calculate SOCSO on net amount (after platform fee)
        socso_amount = calculate_socso(self.net_amount)
        final_payout = round(self.net_amount - socso_amount, 2)

        return {
            'id': self.id,
            'escrow_number': self.escrow_number,
            'gig_id': self.gig_id,
            'client_id': self.client_id,
            'freelancer_id': self.freelancer_id,
            'amount': self.amount,
            'platform_fee': self.platform_fee,
            'net_amount': self.net_amount,
            'socso_amount': socso_amount,
            'final_payout': final_payout,
            'refunded_amount': self.refunded_amount or 0.0,
            'remaining_amount': self.amount - (self.refunded_amount or 0.0),
            'status': self.status,
            'status_label': self.get_status_label(),
            'status_color': self.get_status_color(),
            'payment_reference': self.payment_reference,
            'payment_gateway': self.payment_gateway,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'funded_at': self.funded_at.isoformat() if self.funded_at else None,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'refunded_at': self.refunded_at.isoformat() if self.refunded_at else None
        }
    
    def get_status_label(self):
        """Get human-readable status label"""
        labels = {
            'pending': 'Pending Payment',
            'funded': 'Funds Held in Escrow',
            'released': 'Released to Freelancer',
            'refunded': 'Refunded to Client',
            'partial_refund': 'Partially Refunded',
            'disputed': 'Under Dispute',
            'cancelled': 'Cancelled'
        }
        return labels.get(self.status, self.status.title())

    def get_status_color(self):
        """Get Bootstrap color class for status"""
        colors = {
            'pending': 'warning',
            'funded': 'info',
            'released': 'success',
            'refunded': 'secondary',
            'partial_refund': 'warning',
            'disputed': 'danger',
            'cancelled': 'dark'
        }
        return colors.get(self.status, 'secondary')

class PortfolioItem(db.Model):
    """Model for freelancer portfolio items to showcase past work"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    image_filename = db.Column(db.String(255))
    image_path = db.Column(db.String(500))
    external_url = db.Column(db.String(500))
    is_featured = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'image_url': f'/uploads/portfolio/{self.image_filename}' if self.image_filename else None,
            'external_url': self.external_url,
            'is_featured': self.is_featured,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Conversation(db.Model):
    """Model for chat conversations between users"""
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'))
    participant_1_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    participant_2_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_archived_by_1 = db.Column(db.Boolean, default=False)
    is_archived_by_2 = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'gig_id': self.gig_id,
            'participant_1_id': self.participant_1_id,
            'participant_2_id': self.participant_2_id,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Message(db.Model):
    """Model for individual chat messages"""
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')  # text, image, file, system
    attachment_url = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender_id': self.sender_id,
            'content': self.content,
            'message_type': self.message_type,
            'attachment_url': self.attachment_url,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Notification(db.Model):
    """Model for user notifications"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # new_gig, message, payment, review, application, dispute
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(500))
    related_id = db.Column(db.Integer)  # ID of related entity (gig_id, message_id, etc.)
    is_read = db.Column(db.Boolean, default=False)
    is_push_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'notification_type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class NotificationPreference(db.Model):
    """Model for user notification preferences"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    push_enabled = db.Column(db.Boolean, default=True)
    push_subscription = db.Column(db.Text)  # JSON web push subscription
    email_new_gig = db.Column(db.Boolean, default=True)
    email_message = db.Column(db.Boolean, default=True)
    email_payment = db.Column(db.Boolean, default=True)
    email_review = db.Column(db.Boolean, default=True)
    push_new_gig = db.Column(db.Boolean, default=True)
    push_message = db.Column(db.Boolean, default=True)
    push_payment = db.Column(db.Boolean, default=True)
    push_review = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IdentityVerification(db.Model):
    """Model for IC/MyKad identity verification requests"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ic_number = db.Column(db.String(12), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    ic_front_image = db.Column(db.String(500))
    ic_back_image = db.Column(db.String(500))
    selfie_image = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, expired
    rejection_reason = db.Column(db.Text)
    verified_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ic_number': self.ic_number[:4] + '****' + self.ic_number[-4:] if self.ic_number else None,
            'full_name': self.full_name,
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Dispute(db.Model):
    """Model for dispute resolution between clients and freelancers"""
    id = db.Column(db.Integer, primary_key=True)
    dispute_number = db.Column(db.String(50), unique=True, nullable=False)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    escrow_id = db.Column(db.Integer, db.ForeignKey('escrow.id'))
    filed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    against_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    dispute_type = db.Column(db.String(50), nullable=False)  # quality, non_delivery, payment, harassment, other
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_files = db.Column(db.Text)  # JSON array of file paths
    status = db.Column(db.String(30), default='open')  # open, under_review, awaiting_response, resolved, escalated, closed
    resolution = db.Column(db.Text)
    resolution_type = db.Column(db.String(30))  # refund_full, refund_partial, release_payment, no_action, mutual_agreement
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'dispute_number': self.dispute_number,
            'gig_id': self.gig_id,
            'escrow_id': self.escrow_id,
            'filed_by_id': self.filed_by_id,
            'against_id': self.against_id,
            'dispute_type': self.dispute_type,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'resolution': self.resolution,
            'resolution_type': self.resolution_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

class DisputeMessage(db.Model):
    """Model for messages within a dispute"""
    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey('dispute.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    attachments = db.Column(db.Text)  # JSON array of file paths
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Milestone(db.Model):
    """Model for escrow milestone payments"""
    id = db.Column(db.Integer, primary_key=True)
    escrow_id = db.Column(db.Integer, db.ForeignKey('escrow.id'), nullable=False)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    milestone_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float)  # Percentage of total escrow
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(30), default='pending')  # pending, funded, in_progress, submitted, approved, released, disputed
    work_submitted = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    released_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'escrow_id': self.escrow_id,
            'gig_id': self.gig_id,
            'milestone_number': self.milestone_number,
            'title': self.title,
            'description': self.description,
            'amount': self.amount,
            'percentage': self.percentage,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'work_submitted': self.work_submitted,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'released_at': self.released_at.isoformat() if self.released_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PlatformFeedback(db.Model):
    """Model for user feedback about the GigHala platform"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_type = db.Column(db.String(50), nullable=False)  # suggestion, bug, complaint, praise, other
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new')  # new, reviewed, resolved, closed
    admin_response = db.Column(db.Text)
    responded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    responded_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'feedback_type': self.feedback_type,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'admin_response': self.admin_response,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SocsoContribution(db.Model):
    """
    Model for tracking SOCSO (Social Security Organization) contributions
    Required by Gig Workers Bill 2025 - Self-Employment Social Security Scheme (SESKSO/SKSPS)
    Platform must deduct 1.25% of net earnings and remit to SOCSO via ASSIST Portal
    """
    id = db.Column(db.Integer, primary_key=True)

    # Worker identification
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Source transaction references (one will be populated)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    payout_id = db.Column(db.Integer, db.ForeignKey('payout.id'))
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'))

    # Financial details
    gross_amount = db.Column(db.Float, nullable=False)  # Original gig amount
    platform_commission = db.Column(db.Float, nullable=False)  # Platform fee deducted
    net_earnings = db.Column(db.Float, nullable=False)  # Amount after commission, before SOCSO
    socso_amount = db.Column(db.Float, nullable=False)  # 1.25% of net_earnings
    final_payout = db.Column(db.Float, nullable=False)  # Amount after SOCSO deduction

    # Contribution metadata
    contribution_month = db.Column(db.String(7), nullable=False)  # YYYY-MM format
    contribution_year = db.Column(db.Integer, nullable=False)
    contribution_type = db.Column(db.String(20), nullable=False)  # 'escrow_release', 'payout', 'transaction'

    # ASSIST Portal remittance tracking
    remitted_to_socso = db.Column(db.Boolean, default=False)
    remittance_date = db.Column(db.DateTime)
    remittance_reference = db.Column(db.String(100))  # ASSIST Portal reference number
    remittance_batch_id = db.Column(db.String(100))  # Batch upload identifier

    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'freelancer_id': self.freelancer_id,
            'transaction_id': self.transaction_id,
            'payout_id': self.payout_id,
            'gig_id': self.gig_id,
            'gross_amount': self.gross_amount,
            'platform_commission': self.platform_commission,
            'net_earnings': self.net_earnings,
            'socso_amount': self.socso_amount,
            'final_payout': self.final_payout,
            'contribution_month': self.contribution_month,
            'contribution_year': self.contribution_year,
            'contribution_type': self.contribution_type,
            'remitted_to_socso': self.remitted_to_socso,
            'remittance_date': self.remittance_date.isoformat() if self.remittance_date else None,
            'remittance_reference': self.remittance_reference,
            'remittance_batch_id': self.remittance_batch_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'notes': self.notes
        }

class AuditLog(db.Model):
    """
    Model for security event logging and audit trail
    Tracks authentication, authorization, admin operations, financial transactions, and data changes
    """
    id = db.Column(db.Integer, primary_key=True)

    # Event classification
    event_category = db.Column(db.String(50), nullable=False, index=True)  # authentication, authorization, admin, financial, data_access, system
    event_type = db.Column(db.String(100), nullable=False, index=True)  # login_success, login_failure, permission_denied, etc.
    severity = db.Column(db.String(20), nullable=False, index=True)  # low, medium, high, critical

    # Actor information (who performed the action)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    username = db.Column(db.String(80))
    ip_address = db.Column(db.String(45), index=True)
    user_agent = db.Column(db.Text)

    # Action details (what was done)
    action = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(50))  # user, gig, transaction, escrow, payout, etc.
    resource_id = db.Column(db.String(100))  # ID of affected resource

    # Result and details
    status = db.Column(db.String(20), nullable=False)  # success, failure, blocked
    message = db.Column(db.Text)
    details = db.Column(db.Text)  # JSON string with additional context

    # Data change tracking (for sensitive operations)
    old_value = db.Column(db.Text)  # JSON string
    new_value = db.Column(db.Text)  # JSON string

    # Request context
    request_method = db.Column(db.String(10))  # GET, POST, PUT, DELETE
    request_path = db.Column(db.String(500))
    request_id = db.Column(db.String(100))  # Correlation ID for tracing

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # SIEM integration fields
    siem_forwarded = db.Column(db.Boolean, default=False)
    siem_forwarded_at = db.Column(db.DateTime)

    def to_dict(self):
        """Convert audit log to dictionary for JSON response"""
        return {
            'id': self.id,
            'event_category': self.event_category,
            'event_type': self.event_type,
            'severity': self.severity,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'status': self.status,
            'message': self.message,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def to_siem_format(self):
        """Convert to SIEM-friendly format (CEF - Common Event Format)"""
        # CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        cef_severity = {
            'low': 3,
            'medium': 5,
            'high': 8,
            'critical': 10
        }.get(self.severity, 5)

        extensions = []
        if self.user_id:
            extensions.append(f"suser={self.username}")
            extensions.append(f"suid={self.user_id}")
        if self.ip_address:
            extensions.append(f"src={self.ip_address}")
        if self.resource_type:
            extensions.append(f"cs1Label=ResourceType cs1={self.resource_type}")
        if self.resource_id:
            extensions.append(f"cs2Label=ResourceID cs2={self.resource_id}")
        if self.status:
            extensions.append(f"outcome={self.status}")
        if self.request_path:
            extensions.append(f"request={self.request_path}")

        extension_str = ' '.join(extensions)

        return f"CEF:0|GigHala|GigHala Platform|1.0|{self.event_type}|{self.action}|{cef_severity}|{extension_str}"

# Initialize Security Logger after all models are defined
from security_logger import init_security_logger
security_logger = init_security_logger(app, db)

# Routes
@app.route('/')
def index():
    # If user is logged in, redirect to their personalized dashboard
    if 'user_id' in session:
        return redirect('/dashboard')

    # Show public homepage for visitors
    # Sync with VisitorLog count
    total_visits = VisitorLog.query.count()
    
    # Update SiteStats for historical compatibility if needed, but use VisitorLog as source of truth
    stats = SiteStats.query.filter_by(key='visitor_count').first()
    if not stats:
        stats = SiteStats(key='visitor_count', value=total_visits)
        db.session.add(stats)
    else:
        stats.value = total_visits
    db.session.commit()

    # Get dual date
    today_dual = get_dual_date()

    # Count active freelancers (users with user_type 'freelancer' or 'both')
    freelancer_count = User.query.filter(
        (User.user_type == 'freelancer') | (User.user_type == 'both')
    ).count()
    
    # Count active gigs (open or in progress)
    active_gigs_count = Gig.query.filter(
        Gig.status.in_(['open', 'in_progress'])
    ).count()
    
    # Calculate total amount paid out in the last year (from completed transactions)
    from datetime import datetime, timedelta
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    total_paid_year = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.transaction_date >= one_year_ago,
        Transaction.status == 'completed'
    ).scalar() or 0
    
    # Format paid amount (convert to millions if applicable)
    if total_paid_year >= 1000000:
        paid_display = f"RM {total_paid_year/1000000:.1f}J"
    else:
        paid_display = f"RM {total_paid_year:,.0f}"

    # Pass stats to index
    user_count = User.query.count()
    return render_template('index.html',
                         visitor_count=stats.value,
                         freelancer_count=freelancer_count,
                         user_count=user_count,
                         active_gigs_count=active_gigs_count or 2847,
                         total_paid_year=paid_display or "RM 2.3J",
                         lang=get_user_language(),
                         t=t,
                         today_gregorian=today_dual['gregorian'],
                         today_hijri=today_dual['hijri'])

@app.route('/gigs')
@page_login_required
def browse_gigs():
    """Browse available gigs page"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    # Get main categories only (exclude detailed subcategories)
    categories = Category.query.filter(Category.slug.in_(MAIN_CATEGORY_SLUGS)).all()
    return render_template('gigs.html', user=user, categories=categories, active_page='gigs', lang=get_user_language(), t=t)

@app.route('/gig/<int:gig_id>')
def view_gig(gig_id):
    """View individual gig details"""
    from werkzeug.exceptions import HTTPException
    
    try:
        gig = Gig.query.get_or_404(gig_id)
        
        # Only increment view count for authenticated users to prevent abuse
        if 'user_id' in session:
            gig.views = (gig.views or 0) + 1
            db.session.commit()
        
        # Get client info with null safety
        client = User.query.get(gig.client_id) if gig.client_id else None
        client_gigs_posted = Gig.query.filter_by(client_id=gig.client_id).count() if gig.client_id else 0
        
        # Parse skills if available
        skills = []
        if gig.skills_required:
            try:
                skills = json.loads(gig.skills_required)
            except:
                skills = []
        
        # Check if current user is logged in
        current_user = None
        is_own_gig = False
        existing_application = None
        
        escrow = None
        is_freelancer = False
        
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
            is_own_gig = gig.client_id == session['user_id'] if gig.client_id else False
            is_freelancer = gig.freelancer_id == session['user_id'] if gig.freelancer_id else False
            existing_application = Application.query.filter_by(
                gig_id=gig_id, 
                freelancer_id=session['user_id']
            ).first()
            # Get escrow if user is client or freelancer
            if is_own_gig or is_freelancer:
                try:
                    escrow = Escrow.query.filter_by(gig_id=gig_id).first()
                except Exception as escrow_err:
                    app.logger.warning(f"Escrow lookup error for gig {gig_id}: {str(escrow_err)}")
                    escrow = None
        
        # Get gig photos
        gig_photos = GigPhoto.query.filter_by(gig_id=gig_id).order_by(GigPhoto.created_at.desc()).all()
        
        # Get applications for gig owner to manage
        gig_applications = []
        if is_own_gig:
            applications_raw = Application.query.filter_by(gig_id=gig_id).order_by(Application.created_at.desc()).all()
            for app_item in applications_raw:
                freelancer = User.query.get(app_item.freelancer_id)
                if freelancer:
                    gig_applications.append({
                        'id': app_item.id,
                        'freelancer_id': app_item.freelancer_id,
                        'freelancer_name': freelancer.full_name or freelancer.username,
                        'freelancer_username': freelancer.username,
                        'freelancer_rating': freelancer.rating,
                        'freelancer_review_count': freelancer.review_count or 0,
                        'freelancer_completed_gigs': freelancer.completed_gigs or 0,
                        'freelancer_is_verified': freelancer.is_verified,
                        'freelancer_bio': freelancer.bio,
                        'proposed_price': app_item.proposed_price,
                        'cover_letter': app_item.cover_letter,
                        'status': app_item.status,
                        'created_at': app_item.created_at
                    })
        
        # Get reviews for this gig (for mutual rating display)
        gig_reviews = []
        user_has_reviewed = False
        user_review = None
        other_party_review = None
        freelancer_user = None
        
        if gig.status == 'completed':
            reviews = Review.query.filter_by(gig_id=gig_id).all()
            for review in reviews:
                reviewer = User.query.get(review.reviewer_id)
                reviewee = User.query.get(review.reviewee_id)
                review_data = {
                    'id': review.id,
                    'reviewer_id': review.reviewer_id,
                    'reviewer_name': reviewer.full_name or reviewer.username if reviewer else 'Unknown',
                    'reviewee_id': review.reviewee_id,
                    'reviewee_name': reviewee.full_name or reviewee.username if reviewee else 'Unknown',
                    'rating': review.rating,
                    'comment': review.comment,
                    'created_at': review.created_at
                }
                gig_reviews.append(review_data)
                
                # Check if current user has reviewed
                if current_user and review.reviewer_id == current_user.id:
                    user_has_reviewed = True
                    user_review = review_data
                # Get the other party's review based on role
                elif current_user:
                    # If current user is client, show freelancer's review
                    if is_own_gig and review.reviewer_id == gig.freelancer_id:
                        other_party_review = review_data
                    # If current user is freelancer, show client's review
                    elif is_freelancer and review.reviewer_id == gig.client_id:
                        other_party_review = review_data
            
            # Get freelancer info for review form
            if gig.freelancer_id:
                freelancer_user = User.query.get(gig.freelancer_id)
        
        # Get invoices and receipts for this gig
        gig_invoices = []
        gig_receipts = []
        if current_user and (is_own_gig or is_freelancer):
            invoices = Invoice.query.filter_by(gig_id=gig_id).order_by(Invoice.created_at.desc()).all()
            for inv in invoices:
                gig_invoices.append({
                    'id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'amount': inv.total_amount,
                    'status': inv.status,
                    'created_at': inv.created_at,
                    'invoice_submitted': inv.invoice_submitted,
                    'freelancer_invoice_number': inv.freelancer_invoice_number,
                    'freelancer_invoice_date': inv.freelancer_invoice_date,
                    'freelancer_submitted_at': inv.freelancer_submitted_at,
                    'freelancer_invoice_file': inv.freelancer_invoice_file
                })
            
            receipts = Receipt.query.filter_by(gig_id=gig_id).order_by(Receipt.created_at.desc()).all()
            for rec in receipts:
                gig_receipts.append({
                    'id': rec.id,
                    'receipt_number': rec.receipt_number,
                    'receipt_type': rec.receipt_type,
                    'amount': rec.total_amount,
                    'created_at': rec.created_at
                })
        
        return render_template('gig_detail.html',
                              gig=gig,
                              client=client,
                              client_gigs_posted=client_gigs_posted,
                              skills=skills,
                              user=current_user,
                              current_user=current_user,
                              is_own_gig=is_own_gig,
                              is_freelancer=is_freelancer,
                              existing_application=existing_application,
                              escrow=escrow,
                              gig_photos=gig_photos,
                              gig_applications=gig_applications,
                              gig_reviews=gig_reviews,
                              user_has_reviewed=user_has_reviewed,
                              user_review=user_review,
                              other_party_review=other_party_review,
                              freelancer_user=freelancer_user,
                              gig_invoices=gig_invoices,
                              gig_receipts=gig_receipts,
                              timedelta=timedelta,
                              lang=get_user_language(),
                              t=t)
    except HTTPException:
        # Let 404 and other HTTP exceptions propagate normally
        raise
    except Exception as e:
        app.logger.error(f"Error viewing gig {gig_id}: {str(e)}")
        return render_template('error.html', error="Terdapat masalah teknikal. Sila cuba lagi.", lang=get_user_language(), t=t), 500

@app.route('/post-gig', methods=['GET', 'POST'])
@page_login_required
def post_gig():
    """Post a new gig page"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Only clients or 'both' user types can post gigs
    if user.user_type not in ['client', 'both']:
        return redirect('/dashboard')

    # Get main categories only (exclude detailed subcategories)
    categories = Category.query.filter(Category.slug.in_(MAIN_CATEGORY_SLUGS)).all()
    
    form_data = {}
    
    if request.method == 'POST':
        form_data = {
            'title': request.form.get('title', ''),
            'description': request.form.get('description', ''),
            'category': request.form.get('category', ''),
            'duration': request.form.get('duration', ''),
            'location': request.form.get('location', ''),
            'budget_min': request.form.get('budget_min', ''),
            'budget_max': request.form.get('budget_max', ''),
            'deadline': request.form.get('deadline', ''),
            'is_remote': request.form.get('is_remote') == 'on',
            'halal_compliant': request.form.get('halal_compliant') == 'on',
            'is_instant_payout': request.form.get('is_instant_payout') == 'on',
            'is_brand_partnership': request.form.get('is_brand_partnership') == 'on',
            'skills_required': request.form.get('skills_required', '[]')
        }
        
        try:
            title = sanitize_input(form_data['title'], max_length=200)
            description = sanitize_input(form_data['description'], max_length=5000)
            category = sanitize_input(form_data['category'], max_length=50)
            duration = sanitize_input(form_data['duration'], max_length=50)
            location = sanitize_input(form_data['location'], max_length=100)
            
            if not title or not description or not category:
                flash('Sila isi semua maklumat yang diperlukan.', 'error')
                return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)
            
            try:
                budget_min = float(form_data['budget_min']) if form_data['budget_min'] else 0
                budget_max = float(form_data['budget_max']) if form_data['budget_max'] else 0
                approved_budget = float(form_data['approved_budget']) if form_data.get('approved_budget') else None
                if budget_min < 0 or budget_max < 0 or budget_min > budget_max:
                    flash('Nilai budget tidak sah.', 'error')
                    return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)
                if approved_budget is not None and approved_budget < 0:
                    flash('Nilai approved budget tidak sah.', 'error')
                    return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)
            except (ValueError, TypeError):
                flash('Format budget tidak sah.', 'error')
                return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)
            
            skills_json = form_data['skills_required']
            try:
                skills_required = json.loads(skills_json) if skills_json else []
                if not isinstance(skills_required, list):
                    skills_required = []
                skills_required = [sanitize_input(str(skill), max_length=50) for skill in skills_required[:20]]
            except json.JSONDecodeError:
                skills_required = []
            
            deadline = None
            deadline_str = form_data['deadline']
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str)
                    if deadline < datetime.utcnow():
                        flash('Tarikh akhir mesti pada masa hadapan.', 'error')
                        return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)
                except (ValueError, TypeError):
                    flash('Format tarikh tidak sah.', 'error')
                    return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)

            # HALAL COMPLIANCE VALIDATION
            # GigHala enforces strict halal compliance - all gigs must pass validation
            skills_text = ' '.join(skills_required) if skills_required else ''
            is_halal_compliant, halal_result = validate_gig_halal_compliance(
                title=title,
                description=description,
                category=category,
                skills=skills_text
            )

            if not is_halal_compliant:
                # Log the violation for admin review
                from security_logger import log_security_event
                log_security_event(
                    event_type='halal_violation_attempt',
                    user_id=user_id,
                    details={
                        'action': 'create_gig',
                        'violations': halal_result['violations'],
                        'title': title[:100],
                        'category': category
                    },
                    ip_address=request.headers.get('X-Forwarded-For', request.remote_addr)
                )

                # Show detailed error message to user
                error_msg = halal_result['message_ms'] + ' ' + halal_result['message_en']
                if halal_result['errors']:
                    error_msg += '\n\nDetails:\n' + '\n'.join(halal_result['errors'][:3])

                flash(error_msg, 'error')
                return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)

            new_gig = Gig(
                title=title,
                description=description,
                category=category,
                budget_min=budget_min,
                budget_max=budget_max,
                approved_budget=approved_budget,
                duration=duration,
                location=location,
                is_remote=form_data['is_remote'],
                client_id=user_id,
                halal_compliant=form_data['halal_compliant'],
                is_instant_payout=form_data['is_instant_payout'],
                is_brand_partnership=form_data['is_brand_partnership'],
                skills_required=json.dumps(skills_required),
                deadline=deadline
            )
            
            db.session.add(new_gig)
            db.session.flush()  # Flush to get the ID without committing
            
            # Generate unique gig code
            new_gig.gig_code = f"GIG-{new_gig.id:05d}"
            db.session.commit()
            
            # Handle photo uploads
            photos = request.files.getlist('photos')
            if photos:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'pdf', 'doc', 'docx'}
                max_size = 5 * 1024 * 1024  # 5MB

                for photo in photos[:5]:  # Max 5 photos
                    if photo and photo.filename:
                        ext = photo.filename.rsplit('.', 1)[-1].lower() if '.' in photo.filename else ''
                        if ext not in allowed_extensions:
                            continue
                        
                        # Check file size
                        photo.seek(0, 2)  # Seek to end
                        file_size = photo.tell()
                        photo.seek(0)  # Reset to beginning
                        
                        if file_size > max_size:
                            continue
                        
                        # Generate unique filename with sanitized original name
                        from werkzeug.utils import secure_filename
                        safe_name = secure_filename(photo.filename) or 'photo'
                        unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
                        file_path = os.path.join(UPLOAD_FOLDER, 'gig_photos', unique_filename)
                        # Ensure the path stays within the upload folder
                        if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOAD_FOLDER)):
                            continue
                        photo.save(file_path)
                        
                        # Create GigPhoto record
                        gig_photo = GigPhoto(
                            gig_id=new_gig.id,
                            uploader_id=user_id,
                            filename=unique_filename,
                            original_filename=photo.filename,
                            file_path=file_path,
                            file_size=file_size,
                            photo_type='reference',
                            mime_type=get_mime_type(photo.filename)
                        )
                        db.session.add(gig_photo)
                
                db.session.commit()
            
            flash('Gig berjaya dipost!', 'success')
            return redirect('/dashboard')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Create gig error: {str(e)}")
            flash('Ralat berlaku. Sila cuba lagi.', 'error')
            return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)
    
    return render_template('post_gig.html', user=user, categories=categories, active_page='post-gig', lang=get_user_language(), t=t, form_data=form_data)

@app.route('/edit-gig/<int:gig_id>', methods=['GET', 'POST'])
@page_login_required
def edit_gig(gig_id):
    """Edit an existing gig"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    gig = Gig.query.get_or_404(gig_id)

    if gig.client_id != user_id:
        flash('Anda tidak mempunyai kebenaran untuk mengedit gig ini.', 'error')
        return redirect('/dashboard')

    if gig.status not in ['open', 'in_progress']:
        flash('Gig yang sudah selesai atau dibatalkan tidak boleh diedit.', 'error')
        return redirect(f'/gig/{gig_id}')

    # Get main categories only (exclude detailed subcategories)
    categories = Category.query.filter(Category.slug.in_(MAIN_CATEGORY_SLUGS)).all()
    
    try:
        existing_skills = json.loads(gig.skills_required) if gig.skills_required else []
    except (json.JSONDecodeError, TypeError):
        existing_skills = []
    
    form_data = {
        'title': gig.title,
        'description': gig.description,
        'category': gig.category,
        'duration': gig.duration or '',
        'location': gig.location or '',
        'budget_min': gig.budget_min,
        'budget_max': gig.budget_max,
        'approved_budget': gig.approved_budget or '',
        'deadline': gig.deadline.strftime('%Y-%m-%d') if gig.deadline else '',
        'is_remote': gig.is_remote,
        'halal_compliant': gig.halal_compliant,
        'is_instant_payout': gig.is_instant_payout,
        'is_brand_partnership': gig.is_brand_partnership,
        'skills_required': json.dumps(existing_skills)
    }
    
    if request.method == 'POST':
        form_data = {
            'title': request.form.get('title', ''),
            'description': request.form.get('description', ''),
            'category': request.form.get('category', ''),
            'duration': request.form.get('duration', ''),
            'location': request.form.get('location', ''),
            'budget_min': request.form.get('budget_min', ''),
            'budget_max': request.form.get('budget_max', ''),
            'approved_budget': request.form.get('approved_budget', ''),
            'deadline': request.form.get('deadline', ''),
            'is_remote': request.form.get('is_remote') == 'on',
            'halal_compliant': request.form.get('halal_compliant') == 'on',
            'is_instant_payout': request.form.get('is_instant_payout') == 'on',
            'is_brand_partnership': request.form.get('is_brand_partnership') == 'on',
            'skills_required': request.form.get('skills_required', '[]')
        }

        try:
            title = sanitize_input(form_data['title'], max_length=200)
            description = sanitize_input(form_data['description'], max_length=5000)
            category = sanitize_input(form_data['category'], max_length=50)
            duration = sanitize_input(form_data['duration'], max_length=50)
            location = sanitize_input(form_data['location'], max_length=100)

            if not title or not description or not category:
                flash('Sila isi semua maklumat yang diperlukan.', 'error')
                return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)

            try:
                budget_min = float(form_data['budget_min']) if form_data['budget_min'] else 0
                budget_max = float(form_data['budget_max']) if form_data['budget_max'] else 0
                approved_budget = float(form_data['approved_budget']) if form_data.get('approved_budget') else None
                if budget_min < 0 or budget_max < 0 or budget_min > budget_max:
                    flash('Nilai budget tidak sah.', 'error')
                    return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)
                if approved_budget is not None and approved_budget < 0:
                    flash('Nilai approved budget tidak sah.', 'error')
                    return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)
            except (ValueError, TypeError):
                flash('Format budget tidak sah.', 'error')
                return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)
            
            skills_json = form_data['skills_required']
            try:
                skills_required = json.loads(skills_json) if skills_json else []
                if not isinstance(skills_required, list):
                    skills_required = []
                skills_required = [sanitize_input(str(skill), max_length=50) for skill in skills_required[:20]]
            except json.JSONDecodeError:
                skills_required = []
            
            deadline = None
            deadline_str = form_data['deadline']
            if deadline_str:
                try:
                    deadline = datetime.fromisoformat(deadline_str)
                except (ValueError, TypeError):
                    flash('Format tarikh tidak sah.', 'error')
                    return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)

            # HALAL COMPLIANCE VALIDATION
            # GigHala enforces strict halal compliance - all gigs must pass validation
            skills_text = ' '.join(skills_required) if skills_required else ''
            is_halal_compliant, halal_result = validate_gig_halal_compliance(
                title=title,
                description=description,
                category=category,
                skills=skills_text
            )

            if not is_halal_compliant:
                # Log the violation for admin review
                from security_logger import log_security_event
                log_security_event(
                    event_type='halal_violation_attempt',
                    user_id=user_id,
                    details={
                        'action': 'edit_gig',
                        'gig_id': gig_id,
                        'violations': halal_result['violations'],
                        'title': title[:100],
                        'category': category
                    },
                    ip_address=request.headers.get('X-Forwarded-For', request.remote_addr)
                )

                # Show detailed error message to user
                error_msg = halal_result['message_ms'] + ' ' + halal_result['message_en']
                if halal_result['errors']:
                    error_msg += '\n\nDetails:\n' + '\n'.join(halal_result['errors'][:3])

                flash(error_msg, 'error')
                return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)

            db.session.refresh(gig)
            if gig.client_id != user_id:
                flash('Anda tidak mempunyai kebenaran untuk mengedit gig ini.', 'error')
                return redirect('/dashboard')
            if gig.status not in ['open', 'in_progress']:
                flash('Gig ini tidak lagi boleh diedit.', 'error')
                return redirect(f'/gig/{gig_id}')
            
            gig.title = title
            gig.description = description
            gig.category = category
            gig.budget_min = budget_min
            gig.budget_max = budget_max
            gig.approved_budget = approved_budget
            gig.duration = duration
            gig.location = location
            gig.is_remote = form_data['is_remote']
            gig.halal_compliant = form_data['halal_compliant']
            gig.is_instant_payout = form_data['is_instant_payout']
            gig.is_brand_partnership = form_data['is_brand_partnership']
            gig.skills_required = json.dumps(skills_required)
            gig.deadline = deadline
            
            db.session.commit()
            
            flash('Gig berjaya dikemaskini!', 'success')
            return redirect(f'/gig/{gig_id}')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Edit gig error: {str(e)}")
            flash('Ralat berlaku. Sila cuba lagi.', 'error')
            return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)
    
    return render_template('post_gig.html', user=user, categories=categories, active_page='edit-gig', lang=get_user_language(), t=t, form_data=form_data, edit_mode=True, gig=gig)

@app.route('/dashboard')
@page_login_required
def dashboard():
    """Personalized user dashboard"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Get wallet information
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.session.add(wallet)
        db.session.commit()

    # Get user's gigs
    if user.user_type in ['client', 'both']:
        posted_gigs = Gig.query.filter_by(client_id=user_id).order_by(Gig.created_at.desc()).limit(5).all()
    else:
        posted_gigs = []

    if user.user_type in ['freelancer', 'both']:
        active_gigs = Gig.query.filter_by(freelancer_id=user_id, status='in_progress').limit(5).all()
        applications_raw = Application.query.filter_by(freelancer_id=user_id).order_by(Application.created_at.desc()).limit(10).all()
        # Enrich applications with gig info
        applications = []
        for app in applications_raw:
            gig = Gig.query.get(app.gig_id)
            if gig:
                app.gig_title = gig.title
                app.gig_budget_min = gig.budget_min
                app.gig_budget_max = gig.budget_max
                applications.append(app)
    else:
        active_gigs = []
        applications = []

    # Get stats
    total_gigs_posted = Gig.query.filter_by(client_id=user_id).count() if user.user_type in ['client', 'both'] else 0
    
    # Count only active applications (pending/shortlisted) for non-completed/cancelled gigs
    total_applications = 0
    if user.user_type in ['freelancer', 'both']:
        total_applications = db.session.query(Application).join(
            Gig, Application.gig_id == Gig.id
        ).filter(
            Application.freelancer_id == user_id,
            Application.status.in_(['pending', 'shortlisted']),
            Gig.status.in_(['open', 'in_progress'])
        ).count()
    
    # Count completed gigs - include both freelancer-side and client-side completed gigs
    total_gigs_completed = 0
    if user.user_type in ['freelancer', 'both']:
        # Gigs where user is freelancer and gig is completed
        total_gigs_completed += Gig.query.filter_by(freelancer_id=user_id, status='completed').count()
    if user.user_type in ['client', 'both']:
        # Gigs where user is client and gig is completed
        total_gigs_completed += Gig.query.filter_by(client_id=user_id, status='completed').count()
    
    # Count accepted gigs - include both freelancer-side and client-side accepted gigs
    total_gigs_accepted = 0
    if user.user_type in ['freelancer', 'both']:
        # Gigs where user is freelancer with accepted application
        total_gigs_accepted += Application.query.filter_by(freelancer_id=user_id, status='accepted').count()
    if user.user_type in ['client', 'both']:
        # Gigs where user is client who accepted an application
        client_accepted = db.session.query(Application).join(
            Gig, Application.gig_id == Gig.id
        ).filter(
            Gig.client_id == user_id,
            Application.status == 'accepted'
        ).count()
        total_gigs_accepted += client_accepted

    # Get recent transactions
    recent_transactions = Transaction.query.filter(
        (Transaction.client_id == user_id) | (Transaction.freelancer_id == user_id)
    ).order_by(Transaction.transaction_date.desc()).limit(5).all()

    # Get gigs that need reviews (completed gigs without user's review)
    gigs_to_review = []
    if user.user_type in ['client', 'both']:
        # Gigs where user is client
        client_gigs = Gig.query.filter_by(client_id=user_id, status='completed').all()
        for gig in client_gigs:
            existing_review = Review.query.filter_by(gig_id=gig.id, reviewer_id=user_id).first()
            if not existing_review and gig.freelancer_id:
                gigs_to_review.append(gig)

    if user.user_type in ['freelancer', 'both']:
        # Gigs where user is freelancer
        freelancer_gigs = Gig.query.filter_by(freelancer_id=user_id, status='completed').all()
        for gig in freelancer_gigs:
            existing_review = Review.query.filter_by(gig_id=gig.id, reviewer_id=user_id).first()
            if not existing_review and gig.client_id:
                gigs_to_review.append(gig)

    # Get recent reviews received
    recent_reviews = Review.query.filter_by(reviewee_id=user_id).order_by(Review.created_at.desc()).limit(5).all()

    # Get recent invoices (as client or freelancer)
    recent_invoices = Invoice.query.filter(
        (Invoice.client_id == user_id) | (Invoice.freelancer_id == user_id)
    ).order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Enrich invoices with gig info
    invoices_with_gigs = []
    for inv in recent_invoices:
        gig = Gig.query.get(inv.gig_id)
        invoices_with_gigs.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'amount': inv.total_amount,
            'status': inv.status,
            'created_at': inv.created_at,
            'gig_title': gig.title if gig else 'N/A',
            'gig_id': inv.gig_id
        })

    # Get SOCSO information for freelancers
    socso_data = {
        'membership_number': user.socso_membership_number if user.user_type in ['freelancer', 'both'] else None,
        'total_contribution': 0.0,
        'contributions_by_gig': []
    }
    
    if user.user_type in ['freelancer', 'both']:
        # Get total SOCSO contributions
        socso_contributions = SocsoContribution.query.filter_by(freelancer_id=user_id).all()
        if socso_contributions:
            socso_data['total_contribution'] = sum(c.socso_amount for c in socso_contributions)
            # Get contributions per gig (last 5)
            for contribution in socso_contributions[-5:]:
                gig = Gig.query.get(contribution.gig_id) if contribution.gig_id else None
                socso_data['contributions_by_gig'].append({
                    'gig_title': gig.title if gig else 'Unknown Gig',
                    'amount': contribution.socso_amount,
                    'date': contribution.created_at
                })

    return render_template('dashboard.html',
                         user=user,
                         wallet=wallet,
                         posted_gigs=posted_gigs,
                         active_gigs=active_gigs,
                         applications=applications,
                         total_gigs_posted=total_gigs_posted,
                         total_gigs_completed=total_gigs_completed,
                         total_applications=total_applications,
                         total_gigs_accepted=total_gigs_accepted,
                         recent_transactions=recent_transactions,
                         gigs_to_review=gigs_to_review,
                         recent_reviews=recent_reviews,
                         recent_invoices=invoices_with_gigs,
                         socso_data=socso_data,
                         lang=get_user_language(),
                         t=t)

@app.route('/accepted-gigs')
@page_login_required
def accepted_gigs():
    """Page showing all accepted gigs for the user"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    accepted_gigs_list = []
    
    # Get gigs where user is the freelancer with accepted applications
    if user.user_type in ['freelancer', 'both']:
        freelancer_apps = Application.query.filter_by(
            freelancer_id=user_id, 
            status='accepted'
        ).order_by(Application.created_at.desc()).all()
        
        for app in freelancer_apps:
            gig = Gig.query.get(app.gig_id)
            if gig:
                client = User.query.get(gig.client_id)
                accepted_gigs_list.append({
                    'gig': gig,
                    'application': app,
                    'role': 'freelancer',
                    'other_party': client,
                    'proposed_price': app.proposed_price
                })
    
    # Get gigs where user is the client and has accepted a freelancer
    if user.user_type in ['client', 'both']:
        # Get all accepted applications for gigs owned by this client
        client_accepted_apps = db.session.query(Application, Gig).join(
            Gig, Application.gig_id == Gig.id
        ).filter(
            Gig.client_id == user_id,
            Application.status == 'accepted'
        ).order_by(Application.created_at.desc()).all()
        
        for accepted_app, gig in client_accepted_apps:
            # Avoid duplicates if user is both client and freelancer on same gig
            if not any(item['gig'].id == gig.id and item['role'] == 'client' for item in accepted_gigs_list):
                freelancer = User.query.get(accepted_app.freelancer_id)
                accepted_gigs_list.append({
                    'gig': gig,
                    'application': accepted_app,
                    'role': 'client',
                    'other_party': freelancer,
                    'proposed_price': accepted_app.proposed_price
                })
    
    return render_template('accepted_gigs.html',
                         user=user,
                         accepted_gigs=accepted_gigs_list,
                         active_page='accepted-gigs',
                         lang=get_user_language(),
                         t=t)

@app.route('/completed-gigs')
@page_login_required
def completed_gigs():
    """Page showing all completed gigs for the user"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    completed_gigs_list = []
    
    # Get gigs where user is the freelancer and gig is completed
    if user.user_type in ['freelancer', 'both']:
        freelancer_completed = Gig.query.filter_by(
            freelancer_id=user_id, 
            status='completed'
        ).order_by(Gig.created_at.desc()).all()
        
        for gig in freelancer_completed:
            client = User.query.get(gig.client_id)
            # Get the accepted application for price
            app = Application.query.filter_by(gig_id=gig.id, freelancer_id=user_id, status='accepted').first()
            # Get escrow status for this gig
            escrow = Escrow.query.filter_by(gig_id=gig.id).first()
            completed_gigs_list.append({
                'gig': gig,
                'application': app,
                'role': 'freelancer',
                'other_party': client,
                'proposed_price': app.proposed_price if app else gig.budget_min,
                'escrow': escrow
            })
    
    # Get gigs where user is the client and gig is completed
    if user.user_type in ['client', 'both']:
        client_completed = Gig.query.filter_by(
            client_id=user_id, 
            status='completed'
        ).order_by(Gig.created_at.desc()).all()
        
        for gig in client_completed:
            # Avoid duplicates if user is both client and freelancer on same gig
            if not any(item['gig'].id == gig.id for item in completed_gigs_list):
                freelancer = User.query.get(gig.freelancer_id) if gig.freelancer_id else None
                # Get the accepted application for price
                app = Application.query.filter_by(gig_id=gig.id, status='accepted').first()
                # Get escrow status for this gig
                escrow = Escrow.query.filter_by(gig_id=gig.id).first()
                completed_gigs_list.append({
                    'gig': gig,
                    'application': app,
                    'role': 'client',
                    'other_party': freelancer,
                    'proposed_price': app.proposed_price if app else gig.budget_min,
                    'escrow': escrow
                })
    
    return render_template('completed_gigs.html',
                         user=user,
                         completed_gigs=completed_gigs_list,
                         active_page='completed-gigs',
                         lang=get_user_language(),
                         t=t)

@app.route('/my-applications')
@page_login_required
def my_applications():
    """Page showing all applications made by the user"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Get all pending applications made by the user
    applications_list = []
    if user.user_type in ['freelancer', 'both']:
        applications_raw = Application.query.filter_by(
            freelancer_id=user_id,
            status='pending'
        ).order_by(Application.created_at.desc()).all()

        for app in applications_raw:
            gig = Gig.query.get(app.gig_id)
            if gig:
                client = User.query.get(gig.client_id)
                applications_list.append({
                    'application': app,
                    'gig': gig,
                    'client': client
                })

    return render_template('my_applications.html',
                         user=user,
                         applications=applications_list,
                         active_page='my-applications',
                         lang=get_user_language(),
                         t=t)

@app.route('/my-gigs')
@page_login_required
def my_gigs():
    """Page showing all gigs posted by the user"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Get all gigs posted by the user
    gigs_list = []
    if user.user_type in ['client', 'both']:
        gigs = Gig.query.filter_by(
            client_id=user_id
        ).order_by(Gig.created_at.desc()).all()

        for gig in gigs:
            # Get application count for each gig
            app_count = Application.query.filter_by(gig_id=gig.id).count()
            # Check escrow status for payment indicator
            escrow = Escrow.query.filter_by(gig_id=gig.id).first()
            payment_status = None
            if gig.status == 'completed':
                if escrow and escrow.status == 'released':
                    payment_status = 'paid'
                elif escrow and escrow.status == 'funded':
                    payment_status = 'pending_release'
            gigs_list.append({
                'gig': gig,
                'application_count': app_count,
                'payment_status': payment_status,
                'escrow': escrow
            })

    return render_template('my_gigs.html',
                         user=user,
                         gigs=gigs_list,
                         active_page='my-gigs',
                         lang=get_user_language(),
                         t=t)

@app.route('/documents')
@page_login_required
def documents_page():
    """Page showing all user's invoices and receipts"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get user's invoices (as client or freelancer)
    invoices = Invoice.query.filter(
        (Invoice.client_id == user_id) | (Invoice.freelancer_id == user_id)
    ).order_by(Invoice.created_at.desc()).all()
    
    # Enrich invoices with gig info
    invoices_list = []
    for inv in invoices:
        gig = Gig.query.get(inv.gig_id)
        invoices_list.append({
            'invoice': inv,
            'gig_title': gig.title if gig else 'Unknown Gig',
            'is_client': inv.client_id == user_id
        })
    
    # Get user's receipts
    receipts = Receipt.query.filter_by(user_id=user_id).order_by(Receipt.created_at.desc()).all()
    
    # Enrich receipts with gig info
    receipts_list = []
    for rcp in receipts:
        gig = Gig.query.get(rcp.gig_id) if rcp.gig_id else None
        receipts_list.append({
            'receipt': rcp,
            'gig_title': gig.title if gig else 'N/A'
        })
    
    return render_template('documents.html',
                         user=user,
                         invoices=invoices_list,
                         receipts=receipts_list,
                         active_page='documents',
                         lang=get_user_language(),
                         t=t)

@app.route('/invoice/<int:invoice_id>')
@page_login_required
def view_invoice(invoice_id):
    """View a specific invoice"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Only client or freelancer can view
    if invoice.client_id != user_id and invoice.freelancer_id != user_id:
        flash('Anda tidak mempunyai akses untuk melihat invois ini.', 'error')
        return redirect('/documents')
    
    gig = Gig.query.get(invoice.gig_id)
    client = User.query.get(invoice.client_id)
    freelancer = User.query.get(invoice.freelancer_id)
    
    return render_template('invoice_view.html',
                         user=user,
                         invoice=invoice,
                         gig=gig,
                         client=client,
                         freelancer=freelancer,
                         active_page='documents',
                         lang=get_user_language(),
                         t=t)

@app.route('/receipt/<int:receipt_id>')
@page_login_required
def view_receipt(receipt_id):
    """View a specific receipt"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    receipt = Receipt.query.get_or_404(receipt_id)

    # Check if user has permission to view this receipt
    # User can view if:
    # 1. They own the receipt, OR
    # 2. They are involved in the gig (as client or freelancer)
    has_permission = receipt.user_id == user_id

    if not has_permission and receipt.gig_id:
        gig = Gig.query.get(receipt.gig_id)
        if gig:
            has_permission = (gig.client_id == user_id or gig.freelancer_id == user_id)

    if not has_permission:
        flash('Anda tidak mempunyai akses untuk melihat resit ini.', 'error')
        return redirect('/documents')

    gig = Gig.query.get(receipt.gig_id) if receipt.gig_id else None
    escrow = Escrow.query.get(receipt.escrow_id) if receipt.escrow_id else None

    return render_template('receipt_view.html',
                         user=user,
                         receipt=receipt,
                         gig=gig,
                         escrow=escrow,
                         active_page='documents',
                         lang=get_user_language(),
                         t=t)

@app.route('/settings')
@page_login_required
def settings():
    """User account settings page"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get user's verification status
    verification = IdentityVerification.query.filter_by(user_id=user_id).order_by(IdentityVerification.created_at.desc()).first()
    
    return render_template('settings.html', user=user, verification=verification, lang=get_user_language(), t=t)

@app.route('/settings/profile', methods=['POST'])
@page_login_required
def update_profile_settings():
    """Update user profile information"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    try:
        user.full_name = request.form.get('full_name', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.location = request.form.get('location', '')
        user.user_type = request.form.get('user_type', 'freelancer')
        user.language = request.form.get('language', 'ms')
        user.bio = request.form.get('bio', '').strip()

        ic_number = request.form.get('ic_number', '').strip()
        if ic_number:
            if not re.match(r'^\d{12}$', ic_number):
                flash('No. IC mestilah 12 digit nombor sahaja.', 'error')
                return redirect('/settings')
            user.ic_number = ic_number

        socso_membership_number = request.form.get('socso_membership_number', '').strip()
        if socso_membership_number:
            user.socso_membership_number = socso_membership_number
        else:
            user.socso_membership_number = None

        socso_consent = request.form.get('socso_consent') == '1'
        if socso_consent and not user.socso_consent:
            user.socso_consent = True
            user.socso_consent_date = datetime.utcnow()
        elif not socso_consent:
            user.socso_consent = False

        db.session.commit()
        flash('Maklumat profil berjaya dikemaskini!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Profile update error: {str(e)}")
        flash('Ralat berlaku. Sila cuba lagi.', 'error')
    
    return redirect('/settings')

@app.route('/settings/password', methods=['POST'])
@page_login_required
def change_password():
    """Change user password"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not user.password_hash:
        flash('Sila hubungi sokongan untuk set kata laluan.', 'error')
        return redirect('/settings')
    
    if not check_password_hash(user.password_hash, current_password):
        flash('Kata laluan semasa tidak tepat.', 'error')
        return redirect('/settings')
    
    if len(new_password) < 8:
        flash('Kata laluan baru mestilah sekurang-kurangnya 8 aksara.', 'error')
        return redirect('/settings')
    
    if new_password != confirm_password:
        flash('Kata laluan baru tidak sepadan.', 'error')
        return redirect('/settings')
    
    try:
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Kata laluan berjaya ditukar!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Password change error: {str(e)}")
        flash('Ralat berlaku. Sila cuba lagi.', 'error')
    
    return redirect('/settings')

@app.route('/settings/email', methods=['POST'])
@page_login_required
def change_email():
    """Change user email with history tracking"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    new_email = request.form.get('new_email', '').strip().lower()
    current_password = request.form.get('current_password', '')
    
    if not user.password_hash:
        flash('Sila hubungi sokongan untuk set kata laluan.', 'error')
        return redirect('/settings')
    
    if not check_password_hash(user.password_hash, current_password):
        flash('Kata laluan tidak tepat.', 'error')
        return redirect('/settings')
    
    try:
        email_info = validate_email(new_email, check_deliverability=False)
        new_email = email_info.normalized
    except EmailNotValidError as e:
        flash(f'Emel tidak sah: {str(e)}', 'error')
        return redirect('/settings')
    
    if new_email == user.email:
        flash('Emel baru sama dengan emel semasa.', 'error')
        return redirect('/settings')
    
    existing_user = User.query.filter_by(email=new_email).first()
    if existing_user:
        flash('Emel ini sudah digunakan.', 'error')
        return redirect('/settings')
    
    try:
        email_history = EmailHistory(
            user_id=user_id,
            old_email=user.email,
            new_email=new_email,
            ip_address=request.remote_addr
        )
        db.session.add(email_history)
        
        user.email = new_email
        db.session.commit()
        flash('Emel berjaya ditukar!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Email change error: {str(e)}")
        flash('Ralat berlaku. Sila cuba lagi.', 'error')
    
    return redirect('/settings')

@app.route('/settings/bank', methods=['POST'])
@page_login_required
def update_bank_details():
    """Update user bank account details"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    bank_name = request.form.get('bank_name', '').strip()
    bank_account_number = request.form.get('bank_account_number', '').strip()
    bank_account_holder = request.form.get('bank_account_holder', '').strip()
    
    # Remove any non-digit characters and validate
    if bank_account_number:
        bank_account_number = re.sub(r'\D', '', bank_account_number)
        if not re.match(r'^\d{8,20}$', bank_account_number):
            flash('Nombor akaun mestilah 8-20 digit nombor sahaja.', 'error')
            return redirect('/settings')
    
    try:
        user.bank_name = bank_name if bank_name else None
        user.bank_account_number = bank_account_number if bank_account_number else None
        user.bank_account_holder = bank_account_holder if bank_account_holder else None
        db.session.commit()
        flash('Maklumat bank berjaya dikemaskini!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Bank update error: {str(e)}")
        flash('Ralat berlaku. Sila cuba lagi.', 'error')
    
    return redirect('/settings')

@app.route('/settings/verification', methods=['POST'])
@page_login_required
def upload_verification_documents():
    """Upload IC/passport documents for verification"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    try:
        ic_front = request.files.get('ic_front')
        ic_back = request.files.get('ic_back')
        
        if not ic_front or not ic_back:
            flash('Sila muat naik kedua-dua gambar IC (depan dan belakang).', 'error')
            return redirect('/settings')
        
        # Validate file types
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
        
        if not allowed_file(ic_front.filename) or not allowed_file(ic_back.filename):
            flash('Format fail tidak sah. Sila muat naik gambar (PNG, JPG, JPEG, GIF, WEBP).', 'error')
            return redirect('/settings')
        
        # Create verification folder if not exists
        verification_folder = os.path.join(UPLOAD_FOLDER, 'verification', str(user_id))
        os.makedirs(verification_folder, exist_ok=True)
        
        # Save files with secure names
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        front_ext = ic_front.filename.rsplit('.', 1)[1].lower()
        back_ext = ic_back.filename.rsplit('.', 1)[1].lower()
        
        front_filename = f"ic_front_{timestamp}.{front_ext}"
        back_filename = f"ic_back_{timestamp}.{back_ext}"
        
        ic_front.save(os.path.join(verification_folder, front_filename))
        ic_back.save(os.path.join(verification_folder, back_filename))
        
        # Check if user already has pending verification
        existing = IdentityVerification.query.filter_by(user_id=user_id, status='pending').first()
        
        if existing:
            # Update existing pending verification
            existing.ic_front_image = f"verification/{user_id}/{front_filename}"
            existing.ic_back_image = f"verification/{user_id}/{back_filename}"
            existing.ic_number = user.ic_number or ''
            existing.full_name = user.full_name or user.username
            existing.updated_at = datetime.utcnow()
        else:
            # Create new verification request
            verification = IdentityVerification(
                user_id=user_id,
                ic_number=user.ic_number or '',
                full_name=user.full_name or user.username,
                ic_front_image=f"verification/{user_id}/{front_filename}",
                ic_back_image=f"verification/{user_id}/{back_filename}",
                status='pending'
            )
            db.session.add(verification)
        
        db.session.commit()
        flash('Dokumen berjaya dimuat naik! Pengesahan sedang diproses.', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Verification upload error: {str(e)}")
        flash('Ralat berlaku semasa memuat naik dokumen. Sila cuba lagi.', 'error')
    
    return redirect('/settings')

@app.route('/api/register', methods=['POST'])
@rate_limit(max_attempts=10, window_minutes=60, lockout_minutes=15)
def register():
    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('email') or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate IC/Passport number (optional for beta test)
        ic_number = data.get('ic_number', '')
        if ic_number is None:
            ic_number = ''
        ic_number = ic_number.strip()
        
        is_valid, error_msg = validate_ic_number(ic_number)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Clean the IC number for storage
        ic_number_clean = re.sub(r'[-\s]', '', ic_number) if ic_number else ""

        # Validate privacy consent (PDPA 2010 requirement)
        if not data.get('privacy_consent'):
            return jsonify({'error': 'You must agree to the Privacy Policy to register'}), 400

        # Validate user_type early to check SOCSO requirements
        user_type = data.get('user_type', 'freelancer')
        if user_type not in ['freelancer', 'client', 'both']:
            user_type = 'freelancer'

        # Validate SOCSO consent (Gig Workers Bill 2025 - mandatory for freelancers)
        socso_consent = data.get('socso_consent', False)
        if user_type in ['freelancer', 'both']:
            if not socso_consent:
                return jsonify({
                    'error': 'You must agree to mandatory SOCSO deductions (1.25%) as required by the Gig Workers Bill 2025',
                    'socso_required': True
                }), 400

        # Validate email format
        try:
            email_info = validate_email(data['email'], check_deliverability=False)
            email = email_info.normalized
        except EmailNotValidError as e:
            return jsonify({'error': f'Invalid email: {str(e)}'}), 400

        # Validate username
        is_valid, message = validate_username(data['username'])
        if not is_valid:
            return jsonify({'error': message}), 400

        # Validate password strength
        is_valid, message = validate_password_strength(data['password'])
        if not is_valid:
            return jsonify({'error': message}), 400

        # Validate phone if provided
        if data.get('phone'):
            is_valid, message = validate_phone(data['phone'])
            if not is_valid:
                return jsonify({'error': message}), 400

        # Check for existing users
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already taken'}), 400

        # Sanitize text inputs
        full_name = sanitize_input(data.get('full_name', ''), max_length=120)
        location = sanitize_input(data.get('location', ''), max_length=100)

        # Generate email verification token
        verification_token = generate_email_verification_token()
        verification_expires = datetime.utcnow() + timedelta(hours=24)

        # user_type already validated above
        # Create new user with SOCSO compliance fields
        new_user = User(
            username=data['username'],
            email=email,
            password_hash=generate_password_hash(data['password']),
            phone=data.get('phone'),
            full_name=full_name,
            user_type=user_type,
            location=location,
            ic_number=ic_number_clean,
            socso_registered=False, # Explicitly set boolean
            socso_consent=bool(socso_consent) if user_type in ['freelancer', 'both'] else False,
            socso_consent_date=datetime.utcnow() if socso_consent else None,
            socso_data_complete=bool(ic_number_clean and socso_consent) if user_type in ['freelancer', 'both'] else False,
            email_verification_token=verification_token,
            email_verification_expires=verification_expires,
            is_verified=False  # User needs to verify email
        )

        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session.permanent = True

        # Send verification email
        try:
            send_verification_email(new_user.email, verification_token, new_user.username)
        except Exception as e:
            # Log the error but don't fail registration
            app.logger.error(f"Failed to send verification email to {new_user.email}: {str(e)}")

        # Reset rate limit on successful registration
        reset_rate_limit(request.remote_addr)

        # Log successful registration
        security_logger.log_authentication(
            event_type='registration_success',
            username=new_user.username,
            status='success',
            message=f'New user {new_user.username} registered successfully',
            user_id=new_user.id,
            details={
                'user_type': user_type,
                'socso_consent': socso_consent,
                'has_ic_number': bool(ic_number_clean)
            }
        )

        return jsonify({
            'message': 'Registration successful. Please check your email to verify your account.',
            'verification_required': True,
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'user_type': new_user.user_type,
                'is_verified': new_user.is_verified
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        # Log the error but don't expose details to user
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@app.route('/verify-email', methods=['GET'])
def verify_email_page():
    """Handle email verification via GET link"""
    token = request.args.get('token')

    if not token:
        return jsonify({'error': 'Verification token is required'}), 400

    success, message, user = verify_email_token(token)

    if success:
        # Automatically log the user in after verification
        if user:
            session['user_id'] = user.id
            session.permanent = True

        # Redirect to a success page or dashboard
        return redirect('/?verified=true')
    else:
        return redirect(f'/?verification_error={message}')

@app.route('/api/verify-email', methods=['POST'])
def verify_email_api():
    """API endpoint for email verification"""
    try:
        data = request.json
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Verification token is required'}), 400

        success, message, user = verify_email_token(token)

        if success:
            return jsonify({
                'message': message,
                'verified': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_verified': user.is_verified
                } if user else None
            }), 200
        else:
            return jsonify({'error': message, 'verified': False}), 400
    except Exception as e:
        app.logger.error(f"Email verification error: {str(e)}")
        return jsonify({'error': 'Verification failed. Please try again.'}), 500

@app.route('/reset-password', methods=['GET'])
def reset_password_page():
    """Display password reset form"""
    token = request.args.get('token')

    if not token:
        return render_template('reset-password.html', error='Password reset token is required')

    # Verify token is valid
    success, message, user = verify_password_reset_token(token)

    if not success:
        return render_template('reset-password.html', error=message)

    # Token is valid, show reset form
    return render_template('reset-password.html', token=token, email=user.email if user else None)

@app.route('/api/resend-verification', methods=['POST'])
@login_required
def resend_verification_email():
    """Resend verification email to user"""
    try:
        user = User.query.get(session['user_id'])

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.is_verified:
            return jsonify({'message': 'Email already verified'}), 200

        # Generate new verification token
        token = generate_email_verification_token()
        user.email_verification_token = token
        user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()

        # Send verification email
        success, message = send_verification_email(user.email, token, user.username)

        if success:
            return jsonify({'message': 'Verification email sent successfully'}), 200
        else:
            return jsonify({'error': message}), 500
    except Exception as e:
        app.logger.error(f"Resend verification error: {str(e)}")
        return jsonify({'error': 'Failed to resend verification email'}), 500

@app.route('/api/login', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=15, lockout_minutes=30)
def login():
    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing email or password'}), 400

        # Validate email format
        try:
            email_info = validate_email(data['email'], check_deliverability=False)
            email = email_info.normalized
        except EmailNotValidError:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Debug logging
        print(f"[LOGIN DEBUG] Original email: '{data['email']}'")
        print(f"[LOGIN DEBUG] Normalized email: '{email}'")
        print(f"[LOGIN DEBUG] Lowercased email: '{data['email'].lower().strip()}'")

        # Try to find user with normalized email first, then try case-insensitive lookup
        user = User.query.filter_by(email=email).first()
        print(f"[LOGIN DEBUG] User found with normalized email: {user is not None}")

        if not user:
            # Try case-insensitive lookup with the original input (lowercased)
            user = User.query.filter(db.func.lower(User.email) == data['email'].lower().strip()).first()
            print(f"[LOGIN DEBUG] User found with case-insensitive lookup: {user is not None}")
            if user:
                print(f"[LOGIN DEBUG] Found user: {user.email} (ID: {user.id})")

        # Check if user exists but is OAuth-only (no password set)
        if user and not user.password_hash:
            # Log failed login attempt (OAuth user trying password login)
            security_logger.log_authentication(
                event_type='login_failure',
                username=email,
                status='failure',
                message='OAuth-only user attempted password login',
                details={'reason': 'oauth_only_user', 'oauth_provider': user.oauth_provider}
            )

            # Provide helpful error message based on OAuth provider
            if user.oauth_provider == 'google':
                return jsonify({
                    'error': 'This account uses Google login. Please click "Continue with Google" to sign in.',
                    'oauth_provider': 'google'
                }), 401
            else:
                return jsonify({
                    'error': f'This account uses {user.oauth_provider} login. Please use the {user.oauth_provider} sign in button.',
                    'oauth_provider': user.oauth_provider
                }), 401

        # Check if user doesn't exist
        if not user:
            # Log failed login attempt (user not found)
            security_logger.log_authentication(
                event_type='login_failure',
                username=email,
                status='failure',
                message='User not found',
                details={'reason': 'user_not_found'}
            )
            return jsonify({'error': 'Invalid credentials'}), 401

        # Use constant-time comparison to prevent timing attacks
        if check_password_hash(user.password_hash, data['password']):
            # Check if 2FA is enabled
            if user.totp_enabled:
                # Store temporary pre-auth session
                session['pre_auth_user_id'] = user.id
                session['pre_auth_timestamp'] = datetime.utcnow().isoformat()
                session.permanent = False  # Don't make pre-auth session permanent

                # Log 2FA challenge issued
                security_logger.log_authentication(
                    event_type='login_2fa_challenge',
                    username=user.username,
                    status='pending',
                    message=f'2FA challenge issued for user {user.username}',
                    user_id=user.id
                )

                return jsonify({
                    'requires_2fa': True,
                    'message': 'Please enter your 2FA code'
                }), 200

            # No 2FA - complete login
            session['user_id'] = user.id
            session.permanent = True

            # Reset rate limit on successful login
            reset_rate_limit(request.remote_addr)

            # Log successful login
            security_logger.log_authentication(
                event_type='login_success',
                username=user.username,
                status='success',
                message=f'User {user.username} logged in successfully',
                user_id=user.id
            )

            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.user_type,
                    'total_earnings': user.total_earnings,
                    'rating': user.rating,
                    'is_admin': user.is_admin,
                    'totp_enabled': user.totp_enabled
                }
            }), 200

        # Log failed login attempt
        security_logger.log_authentication(
            event_type='login_failure',
            username=email,
            status='failure',
            message='Invalid password',
            details={'reason': 'invalid_password'}
        )

        # Generic error message to prevent user enumeration
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        # Log the error but don't expose details to user
        app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed. Please try again.'}), 500

@app.route('/api/logout', methods=['GET', 'POST'])
def logout():
    user_id = session.get('user_id')
    username = None

    # Get username before clearing session
    if user_id:
        user = User.query.get(user_id)
        if user:
            username = user.username

    session.pop('user_id', None)

    # Log logout event
    if username:
        security_logger.log_authentication(
            event_type='logout',
            username=username,
            status='success',
            message=f'User {username} logged out',
            user_id=user_id
        )

    # For GET requests (direct link clicks), redirect to homepage
    if request.method == 'GET':
        return redirect('/')
    # For POST requests (JavaScript calls), return JSON
    return jsonify({'message': 'Logged out successfully'}), 200

# ============================================================================
# PASSWORD RESET ENDPOINTS
# ============================================================================

@app.route('/api/forgot-password', methods=['POST'])
@rate_limit(max_attempts=3, window_minutes=15, lockout_minutes=30)
def forgot_password():
    """Request password reset email"""
    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400

        # Validate email format
        try:
            email_info = validate_email(data['email'], check_deliverability=False)
            email = email_info.normalized
        except EmailNotValidError:
            # Don't reveal whether email exists or not for security
            return jsonify({'message': 'If an account exists with this email, you will receive password reset instructions.'}), 200

        user = User.query.filter_by(email=email).first()

        # Don't reveal whether user exists or not (security best practice)
        if not user:
            app.logger.info(f"Password reset requested for non-existent email: {email}")
            return jsonify({'message': 'If an account exists with this email, you will receive password reset instructions.'}), 200

        # Don't allow password reset for OAuth users
        if user.oauth_provider:
            app.logger.info(f"Password reset attempted for OAuth user: {email}")
            return jsonify({'message': 'If an account exists with this email, you will receive password reset instructions.'}), 200

        # Generate secure token
        reset_token = secrets.token_urlsafe(32)

        # Set token expiration (24 hours)
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()

        # Send password reset email
        success, message = send_password_reset_email(user.email, reset_token, user.username)

        if not success:
            app.logger.error(f"Failed to send password reset email to {email}: {message}")

        # Always return success message (don't reveal if email failed)
        security_logger.log_authentication(
            event_type='password_reset_requested',
            username=user.username,
            status='success',
            message=f'Password reset requested for {email}',
            user_id=user.id
        )

        return jsonify({'message': 'If an account exists with this email, you will receive password reset instructions.'}), 200

    except Exception as e:
        app.logger.error(f"Error in forgot_password: {str(e)}")
        return jsonify({'error': 'An error occurred. Please try again later.'}), 500

@app.route('/api/reset-password', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=15, lockout_minutes=30)
def reset_password():
    """Reset password using token"""
    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('token') or not data.get('password'):
            return jsonify({'error': 'Token and password are required'}), 400

        token = data['token']
        new_password = data['password']

        # Validate password strength
        is_valid, error_message = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        # Verify token
        success, message, user = verify_password_reset_token(token)
        if not success:
            return jsonify({'error': message}), 400

        # Update password
        user.password_hash = generate_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()

        # Log password reset
        security_logger.log_authentication(
            event_type='password_reset_completed',
            username=user.username,
            status='success',
            message=f'Password reset completed for {user.email}',
            user_id=user.id
        )

        app.logger.info(f"Password reset successful for user {user.username}")

        return jsonify({'message': 'Password reset successfully. You can now log in with your new password.'}), 200

    except Exception as e:
        app.logger.error(f"Error in reset_password: {str(e)}")
        return jsonify({'error': 'An error occurred. Please try again later.'}), 500

# ============================================================================
# TWO-FACTOR AUTHENTICATION (2FA) ENDPOINTS
# ============================================================================

@app.route('/api/2fa/verify', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=15, lockout_minutes=30)
def verify_2fa_login():
    """Verify 2FA code during login to complete authentication"""
    try:
        data = request.json
        totp_code = data.get('code', '').strip()

        # Validate that user is in pre-auth state
        pre_auth_user_id = session.get('pre_auth_user_id')
        pre_auth_timestamp = session.get('pre_auth_timestamp')

        if not pre_auth_user_id or not pre_auth_timestamp:
            return jsonify({'error': 'No pending 2FA verification'}), 400

        # Check if pre-auth session has expired (5 minutes)
        pre_auth_time = datetime.fromisoformat(pre_auth_timestamp)
        if datetime.utcnow() - pre_auth_time > timedelta(minutes=5):
            session.pop('pre_auth_user_id', None)
            session.pop('pre_auth_timestamp', None)
            return jsonify({'error': '2FA verification expired. Please login again.'}), 400

        # Get user
        user = User.query.get(pre_auth_user_id)
        if not user or not user.totp_enabled or not user.totp_secret:
            session.pop('pre_auth_user_id', None)
            session.pop('pre_auth_timestamp', None)
            return jsonify({'error': 'Invalid 2FA configuration'}), 400

        # Verify TOTP code
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):  # Allow 1 step before/after for clock skew
            security_logger.log_authentication(
                event_type='login_2fa_failure',
                username=user.username,
                status='failure',
                message=f'Invalid 2FA code for user {user.username}',
                user_id=user.id
            )
            return jsonify({'error': 'Invalid 2FA code'}), 401

        # 2FA verified - complete login
        session.pop('pre_auth_user_id', None)
        session.pop('pre_auth_timestamp', None)
        session['user_id'] = user.id
        session.permanent = True

        # Reset rate limit on successful login
        reset_rate_limit(request.remote_addr)

        # Log successful login with 2FA
        security_logger.log_authentication(
            event_type='login_2fa_success',
            username=user.username,
            status='success',
            message=f'User {user.username} logged in successfully with 2FA',
            user_id=user.id
        )

        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'total_earnings': user.total_earnings,
                'rating': user.rating,
                'is_admin': user.is_admin,
                'totp_enabled': user.totp_enabled
            }
        }), 200

    except Exception as e:
        app.logger.error(f"2FA verification error: {str(e)}")
        return jsonify({'error': 'Verification failed. Please try again.'}), 500


@app.route('/api/2fa/setup/start', methods=['POST'])
@login_required
def setup_2fa_start():
    """Start 2FA setup by generating a new TOTP secret"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.totp_enabled:
            return jsonify({'error': '2FA is already enabled'}), 400

        # Generate new TOTP secret
        totp_secret = pyotp.random_base32()

        # Store secret temporarily (not enabled yet until verified)
        user.totp_secret = totp_secret
        db.session.commit()

        # Generate provisioning URI for QR code
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='GigHala'
        )

        # Generate QR code as base64 image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Log 2FA setup initiated
        security_logger.log_security_event(
            event_type='2fa_setup_initiated',
            username=user.username,
            status='success',
            message=f'User {user.username} initiated 2FA setup',
            user_id=user.id
        )

        return jsonify({
            'message': '2FA setup started. Scan the QR code with your authenticator app.',
            'secret': totp_secret,  # Include for manual entry
            'qr_code': f'data:image/png;base64,{qr_code_base64}',
            'provisioning_uri': provisioning_uri
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"2FA setup start error: {str(e)}")
        return jsonify({'error': 'Failed to start 2FA setup. Please try again.'}), 500


@app.route('/api/2fa/setup/verify', methods=['POST'])
@login_required
def setup_2fa_verify():
    """Verify 2FA setup by checking the TOTP code"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        data = request.json
        totp_code = data.get('code', '').strip()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.totp_enabled:
            return jsonify({'error': '2FA is already enabled'}), 400

        if not user.totp_secret:
            return jsonify({'error': 'No 2FA setup in progress. Please start setup first.'}), 400

        # Verify the code
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            security_logger.log_security_event(
                event_type='2fa_setup_verification_failed',
                username=user.username,
                status='failure',
                message=f'Invalid 2FA code during setup for user {user.username}',
                user_id=user.id
            )
            return jsonify({'error': 'Invalid 2FA code. Please try again.'}), 401

        # Code is valid - enable 2FA
        user.totp_enabled = True
        user.totp_enabled_at = datetime.utcnow()
        db.session.commit()

        # Log 2FA enabled
        security_logger.log_security_event(
            event_type='2fa_enabled',
            username=user.username,
            status='success',
            message=f'2FA enabled for user {user.username}',
            user_id=user.id,
            severity='medium'
        )

        return jsonify({
            'message': '2FA enabled successfully',
            'totp_enabled': True
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"2FA setup verify error: {str(e)}")
        return jsonify({'error': 'Failed to verify 2FA setup. Please try again.'}), 500


@app.route('/api/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for the current user"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        data = request.json
        password = data.get('password', '')
        totp_code = data.get('code', '').strip()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.totp_enabled:
            return jsonify({'error': '2FA is not enabled'}), 400

        # Require password verification for disabling 2FA
        if not password or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid password'}), 401

        # Require valid 2FA code to disable
        if not totp_code:
            return jsonify({'error': '2FA code required'}), 400

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            return jsonify({'error': 'Invalid 2FA code'}), 401

        # Disable 2FA
        user.totp_enabled = False
        user.totp_secret = None
        user.totp_enabled_at = None
        db.session.commit()

        # Log 2FA disabled
        security_logger.log_security_event(
            event_type='2fa_disabled',
            username=user.username,
            status='success',
            message=f'2FA disabled for user {user.username}',
            user_id=user.id,
            severity='high'  # High severity because it's a security downgrade
        )

        return jsonify({
            'message': '2FA disabled successfully',
            'totp_enabled': False
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"2FA disable error: {str(e)}")
        return jsonify({'error': 'Failed to disable 2FA. Please try again.'}), 500


@app.route('/api/2fa/status', methods=['GET'])
@login_required
def get_2fa_status():
    """Get 2FA status for the current user"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'totp_enabled': user.totp_enabled,
            'totp_enabled_at': user.totp_enabled_at.isoformat() if user.totp_enabled_at else None
        }), 200

    except Exception as e:
        app.logger.error(f"2FA status error: {str(e)}")
        return jsonify({'error': 'Failed to get 2FA status'}), 500

# ============================================================================
# END TWO-FACTOR AUTHENTICATION (2FA) ENDPOINTS
# ============================================================================

# ============================================================================
# PHONE VERIFICATION ENDPOINTS
# ============================================================================

@app.route('/api/phone/send-verification', methods=['POST'])
@login_required
@rate_limit(max_attempts=3, window_minutes=60, lockout_minutes=30)
def send_phone_verification():
    """Send OTP verification code to user's phone number"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.json
        phone = data.get('phone')

        # If no phone provided, use user's existing phone
        if not phone:
            phone = user.phone

        if not phone:
            return jsonify({'error': 'Phone number is required'}), 400

        # Validate phone number format
        is_valid, message = validate_phone(phone)
        if not is_valid:
            return jsonify({'error': message}), 400

        # Generate OTP code
        otp_code = generate_phone_otp()

        # Send SMS
        success, sms_message = send_phone_verification_sms(phone, otp_code)
        if not success:
            return jsonify({'error': sms_message}), 500

        # Save verification code to database
        user.phone = phone  # Update phone if it was provided
        user.phone_verification_code = otp_code
        user.phone_verification_expires = datetime.utcnow() + timedelta(minutes=10)
        user.phone_verified = False  # Reset verification status
        db.session.commit()

        # Log the event
        app.logger.info(f"Phone verification SMS sent to user {user.username} ({user.id})")

        return jsonify({
            'message': 'Verification code sent successfully',
            'expires_in_minutes': 10
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Phone verification send error: {str(e)}")
        return jsonify({'error': 'Failed to send verification code'}), 500

@app.route('/api/phone/verify', methods=['POST'])
@login_required
def verify_phone():
    """Verify phone number with OTP code"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.json
        submitted_code = data.get('code', '').strip()

        if not submitted_code:
            return jsonify({'error': 'Verification code is required'}), 400

        # Verify the OTP
        success, message = verify_phone_otp(user, submitted_code)

        if not success:
            return jsonify({'error': message}), 400

        # Save to database
        db.session.commit()

        # Log the event
        app.logger.info(f"Phone verified successfully for user {user.username} ({user.id})")

        return jsonify({
            'message': 'Phone number verified successfully',
            'phone_verified': True,
            'phone': user.phone
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Phone verification error: {str(e)}")
        return jsonify({'error': 'Failed to verify phone number'}), 500

@app.route('/api/phone/status', methods=['GET'])
@login_required
def get_phone_status():
    """Get phone verification status for current user"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'phone': user.phone,
            'phone_verified': user.phone_verified,
            'phone_verified_at': user.phone_verified_at.isoformat() if user.phone_verified_at else None
        }), 200

    except Exception as e:
        app.logger.error(f"Phone status error: {str(e)}")
        return jsonify({'error': 'Failed to get phone status'}), 500

# ============================================================================
# END PHONE VERIFICATION ENDPOINTS
# ============================================================================

@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """Get CSRF token for JavaScript requests"""
    token = generate_csrf()
    return jsonify({'csrf_token': token}), 200

@app.route('/api/language', methods=['POST'])
def set_language():
    """Set user's language preference"""
    try:
        data = request.json
        language = data.get('language', 'ms')
        
        # Validate language (only allow 'ms' and 'en')
        if language not in ['ms', 'en']:
            return jsonify({'error': 'Invalid language'}), 400
        
        # Store in session
        session['language'] = language
        
        # If user is logged in, also update database
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                user.language = language
                db.session.commit()
        
        return jsonify({'message': 'Language updated successfully', 'language': language}), 200
    except Exception as e:
        app.logger.error(f"Error setting language: {str(e)}")
        return jsonify({'error': 'Failed to set language'}), 500

# OAuth Login Routes
@app.route('/api/auth/google')
def google_login():
    # Explicitly set redirect URI for Railway and Replit compatibility
    # ProxyFix middleware ensures request.host_url has correct scheme and host
    redirect_uri = request.host_url.rstrip('/') + '/api/auth/google/callback'
    return google.authorize_redirect(redirect_uri)

@app.route('/api/auth/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            return redirect('/?error=google_auth_failed')

        # Get user data from Google
        oauth_id = user_info.get('sub')
        email = user_info.get('email')
        full_name = user_info.get('name')

        if not oauth_id or not email:
            return redirect('/?error=missing_google_data')

        # Check if user exists with this OAuth provider
        user = User.query.filter_by(oauth_provider='google', oauth_id=oauth_id).first()

        if not user:
            # Check if email already exists (link accounts)
            user = User.query.filter_by(email=email).first()
            if user:
                # Update existing account with OAuth info
                user.oauth_provider = 'google'
                user.oauth_id = oauth_id
                db.session.commit()
            else:
                # Create new user
                username = email.split('@')[0] + '_' + secrets.token_hex(4)
                new_user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    oauth_provider='google',
                    oauth_id=oauth_id,
                    user_type='both',
                    is_verified=True  # Email is verified by Google
                )
                db.session.add(new_user)
                db.session.commit()
                user = new_user

        # Log user in
        session['user_id'] = user.id
        session.permanent = True

        # Check if user needs phone setup (Phase 1: Optional but encouraged)
        if not user.phone or not user.phone_verified:
            # Redirect OAuth users to dashboard with phone prompt
            return redirect('/dashboard?show_phone_prompt=true')

        return redirect('/dashboard')
    except Exception as e:
        app.logger.error(f"Google OAuth error: {str(e)}")
        return redirect('/?error=google_auth_failed')

@app.route('/api/auth/microsoft')
def microsoft_login():
    redirect_uri = request.host_url.rstrip('/') + '/api/auth/microsoft/callback'
    return microsoft.authorize_redirect(redirect_uri)

@app.route('/api/auth/microsoft/callback')
def microsoft_callback():
    try:
        token = microsoft.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            return redirect('/?error=microsoft_auth_failed')

        # Get user data from Microsoft
        oauth_id = user_info.get('sub') or user_info.get('oid')
        email = user_info.get('email') or user_info.get('preferred_username')
        full_name = user_info.get('name')

        if not oauth_id or not email:
            return redirect('/?error=missing_microsoft_data')

        # Check if user exists with this OAuth provider
        user = User.query.filter_by(oauth_provider='microsoft', oauth_id=oauth_id).first()

        if not user:
            # Check if email already exists (link accounts)
            user = User.query.filter_by(email=email).first()
            if user:
                # Update existing account with OAuth info
                user.oauth_provider = 'microsoft'
                user.oauth_id = oauth_id
                db.session.commit()
            else:
                # Create new user
                username = email.split('@')[0] + '_' + secrets.token_hex(4)
                new_user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    oauth_provider='microsoft',
                    oauth_id=oauth_id,
                    user_type='both',
                    is_verified=True  # Email is verified by Microsoft
                )
                db.session.add(new_user)
                db.session.commit()
                user = new_user

        # Log user in
        session['user_id'] = user.id
        session.permanent = True

        # Check if user needs phone setup (Phase 1: Optional but encouraged)
        if not user.phone or not user.phone_verified:
            # Redirect OAuth users to dashboard with phone prompt
            return redirect('/dashboard?show_phone_prompt=true')

        return redirect('/dashboard')
    except Exception as e:
        app.logger.error(f"Microsoft OAuth error: {str(e)}")
        return redirect('/?error=microsoft_auth_failed')

@app.route('/api/auth/apple')
def apple_login():
    redirect_uri = request.host_url.rstrip('/') + '/api/auth/apple/callback'
    return apple.authorize_redirect(redirect_uri)

@app.route('/api/auth/apple/callback')
def apple_callback():
    try:
        token = apple.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            return redirect('/?error=apple_auth_failed')

        # Get user data from Apple
        oauth_id = user_info.get('sub')
        email = user_info.get('email')

        # Apple might not always provide the name after first login
        full_name = None
        if 'name' in user_info:
            name_obj = user_info.get('name', {})
            first_name = name_obj.get('firstName', '')
            last_name = name_obj.get('lastName', '')
            full_name = f"{first_name} {last_name}".strip()

        if not oauth_id or not email:
            return redirect('/?error=missing_apple_data')

        # Check if user exists with this OAuth provider
        user = User.query.filter_by(oauth_provider='apple', oauth_id=oauth_id).first()

        if not user:
            # Check if email already exists (link accounts)
            user = User.query.filter_by(email=email).first()
            if user:
                # Update existing account with OAuth info
                user.oauth_provider = 'apple'
                user.oauth_id = oauth_id
                db.session.commit()
            else:
                # Create new user
                username = email.split('@')[0] + '_' + secrets.token_hex(4)
                new_user = User(
                    username=username,
                    email=email,
                    full_name=full_name or email.split('@')[0],
                    oauth_provider='apple',
                    oauth_id=oauth_id,
                    user_type='both',
                    is_verified=True  # Email is verified by Apple
                )
                db.session.add(new_user)
                db.session.commit()
                user = new_user

        # Log user in
        session['user_id'] = user.id
        session.permanent = True

        # Check if user needs phone setup (Phase 1: Optional but encouraged)
        if not user.phone or not user.phone_verified:
            # Redirect OAuth users to dashboard with phone prompt
            return redirect('/dashboard?show_phone_prompt=true')

        return redirect('/dashboard')
    except Exception as e:
        app.logger.error(f"Apple OAuth error: {str(e)}")
        return redirect('/?error=apple_auth_failed')

@app.route('/api/billing/stats')
@login_required
def get_billing_stats():
    """Get billing statistics for the current user"""
    try:
        from models import PaymentHistory, Wallet, Payout, Invoice

        # Get wallet
        wallet = Wallet.query.filter_by(user_id=current_user.id).first()
        available_balance = wallet.balance if wallet else 0.0

        # Total earned: Sum of positive payment types (payment, deposit, release)
        total_earned = db.session.query(db.func.sum(PaymentHistory.amount)).filter(
            PaymentHistory.user_id == current_user.id,
            PaymentHistory.type.in_(['payment', 'deposit', 'release'])
        ).scalar() or 0.0

        # Held balance: Sum of all 'pending' payouts
        held_balance = db.session.query(db.func.sum(Payout.amount)).filter(
            Payout.freelancer_id == current_user.id,
            Payout.status == 'pending'
        ).scalar() or 0.0

        # Total spent: Sum of negative payment types (withdrawal, commission, hold, payout, socso)
        total_spent = db.session.query(db.func.sum(PaymentHistory.amount)).filter(
            PaymentHistory.user_id == current_user.id,
            PaymentHistory.type.in_(['withdrawal', 'payout', 'hold'])
        ).scalar() or 0.0

        # SOCSO total: Sum of socso_amount from payment history
        total_socso = db.session.query(db.func.sum(PaymentHistory.socso_amount)).filter(
            PaymentHistory.user_id == current_user.id
        ).scalar() or 0.0

        return jsonify({
            'available_balance': float(available_balance),
            'total_earned': float(total_earned),
            'held_balance': float(held_balance),
            'total_spent': float(total_spent),
            'total_socso': float(total_socso)
        })
    except Exception as e:
        app.logger.error(f"Error fetching billing stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gigs', methods=['GET'])
@api_rate_limit(requests_per_minute=120)
def get_gigs():
    try:
        category = sanitize_input(request.args.get('category', ''), max_length=50)
        location = sanitize_input(request.args.get('location', ''), max_length=100)
        halal_only = request.args.get('halal_only', 'false').lower() == 'true'
        search = sanitize_input(request.args.get('search', ''), max_length=200)

        # Exclude blocked gigs from public view
        query = Gig.query.filter(Gig.status == 'open')

        if category:
            query = query.filter_by(category=category)
        if location:
            query = query.filter_by(location=location)
        if halal_only:
            query = query.filter_by(halal_compliant=True)
        if search:
            # Use proper parameterized query to prevent SQL injection
            search_pattern = f'%{search}%'
            query = query.filter(
                (Gig.title.ilike(search_pattern)) | (Gig.description.ilike(search_pattern))
            )

        gigs = query.order_by(Gig.created_at.desc()).limit(50).all()

        result = []
        for g in gigs:
            # Get client information
            client = User.query.get(g.client_id)
            client_name = client.full_name if (client and client.full_name) else 'Client'

            result.append({
                'id': g.id,
                'title': g.title,
                'description': g.description,
                'category': g.category,
                'budget_min': g.budget_min,
                'budget_max': g.budget_max,
                'approved_budget': g.approved_budget,
                'location': g.location,
                'is_remote': g.is_remote,
                'status': g.status,
                'halal_compliant': g.halal_compliant,
                'halal_verified': g.halal_verified,
                'is_instant_payout': g.is_instant_payout,
                'is_brand_partnership': g.is_brand_partnership,
                'duration': g.duration,
                'views': g.views,
                'applications': g.applications,
                'client_name': client_name,
                'created_at': g.created_at.isoformat()
            })

        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Get gigs error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve gigs'}), 500

@app.route('/api/gigs/nearby', methods=['GET'])
@api_rate_limit(requests_per_minute=120)
def get_nearby_gigs():
    """
    Get gigs sorted by distance from user's location.
    Query params:
    - lat: user's latitude (required)
    - lng: user's longitude (required)
    - max_distance: maximum distance in km (optional, default: no limit)
    - category: filter by category (optional)
    - halal_only: filter halal-compliant gigs only (optional)
    - search: search in title/description (optional)
    """
    try:
        # Get user's location
        try:
            user_lat = float(request.args.get('lat'))
            user_lng = float(request.args.get('lng'))
        except (TypeError, ValueError):
            return jsonify({'error': 'Valid latitude and longitude are required'}), 400

        # Optional filters
        max_distance = request.args.get('max_distance', type=float)  # in km
        category = sanitize_input(request.args.get('category', ''), max_length=50)
        halal_only = request.args.get('halal_only', 'false').lower() == 'true'
        search = sanitize_input(request.args.get('search', ''), max_length=200)

        # Base query for open gigs (exclude blocked)
        query = Gig.query.filter(Gig.status == 'open')

        # Apply filters
        if category:
            query = query.filter_by(category=category)
        if halal_only:
            query = query.filter_by(halal_compliant=True)
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                (Gig.title.ilike(search_pattern)) | (Gig.description.ilike(search_pattern))
            )

        # Get all matching gigs
        gigs = query.all()

        # Calculate distance for each gig and filter by max_distance
        gigs_with_distance = []
        for g in gigs:
            # Get client information
            client = User.query.get(g.client_id)
            client_name = client.full_name if (client and client.full_name) else 'Client'

            # Calculate distance if gig has coordinates
            distance = None
            if g.latitude is not None and g.longitude is not None:
                distance = calculate_distance(user_lat, user_lng, g.latitude, g.longitude)

            # Apply max_distance filter if specified
            if max_distance is not None:
                if distance is None or distance > max_distance:
                    continue

            gig_data = {
                'id': g.id,
                'title': g.title,
                'description': g.description,
                'category': g.category,
                'budget_min': g.budget_min,
                'budget_max': g.budget_max,
                'approved_budget': g.approved_budget,
                'location': g.location,
                'latitude': g.latitude,
                'longitude': g.longitude,
                'is_remote': g.is_remote,
                'status': g.status,
                'halal_compliant': g.halal_compliant,
                'halal_verified': g.halal_verified,
                'is_instant_payout': g.is_instant_payout,
                'is_brand_partnership': g.is_brand_partnership,
                'duration': g.duration,
                'views': g.views,
                'applications': g.applications,
                'client_name': client_name,
                'created_at': g.created_at.isoformat(),
                'distance': distance  # Distance in km
            }

            gigs_with_distance.append(gig_data)

        # Sort by distance (gigs without coordinates at the end)
        gigs_with_distance.sort(key=lambda x: (x['distance'] is None, x['distance'] or float('inf')))

        # Limit results
        result = gigs_with_distance[:50]

        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Get nearby gigs error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve nearby gigs'}), 500

@app.route('/api/gigs', methods=['POST'])
@api_rate_limit(requests_per_minute=30)
def create_gig():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('title') or not data.get('description'):
            return jsonify({'error': 'Missing required fields'}), 400

        if not data.get('category') or not data.get('budget_min') or not data.get('budget_max'):
            return jsonify({'error': 'Missing required fields'}), 400

        # Sanitize text inputs
        title = sanitize_input(data['title'], max_length=200)
        description = sanitize_input(data['description'], max_length=5000)
        category = sanitize_input(data['category'], max_length=50)
        duration = sanitize_input(data.get('duration', ''), max_length=50)
        location = sanitize_input(data.get('location', ''), max_length=100)

        # Validate budget values
        try:
            budget_min = float(data['budget_min'])
            budget_max = float(data['budget_max'])
            approved_budget = float(data['approved_budget']) if data.get('approved_budget') else None
            if budget_min < 0 or budget_max < 0 or budget_min > budget_max:
                return jsonify({'error': 'Invalid budget values'}), 400
            if budget_min > 1000000 or budget_max > 1000000:
                return jsonify({'error': 'Budget values too high'}), 400
            if approved_budget is not None and (approved_budget < 0 or approved_budget > 1000000):
                return jsonify({'error': 'Invalid approved budget value'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid budget format'}), 400

        # Validate and sanitize skills_required
        skills_required = data.get('skills_required', [])
        if not isinstance(skills_required, list):
            skills_required = []
        skills_required = [sanitize_input(str(skill), max_length=50) for skill in skills_required[:20]]

        # Validate deadline if provided
        deadline = None
        if data.get('deadline'):
            try:
                deadline = datetime.fromisoformat(data['deadline'])
                if deadline < datetime.utcnow():
                    return jsonify({'error': 'Deadline must be in the future'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid deadline format'}), 400

        # HALAL COMPLIANCE VALIDATION
        # GigHala enforces strict halal compliance - all gigs must pass validation
        skills_text = ' '.join(skills_required) if skills_required else ''
        is_halal_compliant, halal_result = validate_gig_halal_compliance(
            title=title,
            description=description,
            category=category,
            skills=skills_text
        )

        if not is_halal_compliant:
            # Log the violation for admin review
            from security_logger import log_security_event
            log_security_event(
                event_type='halal_violation_attempt',
                user_id=session['user_id'],
                details={
                    'action': 'create_gig_api',
                    'violations': halal_result['violations'],
                    'title': title[:100],
                    'category': category
                },
                ip_address=request.headers.get('X-Forwarded-For', request.remote_addr)
            )

            # Return detailed error response
            return jsonify({
                'error': 'Halal compliance violation',
                'message_en': halal_result['message_en'],
                'message_ms': halal_result['message_ms'],
                'violations': halal_result['violations']
            }), 400

        # Geocode location to get coordinates
        latitude, longitude = None, None
        if location and not data.get('is_remote', True):
            latitude, longitude = get_coordinates(location)

        new_gig = Gig(
            title=title,
            description=description,
            category=category,
            budget_min=budget_min,
            budget_max=budget_max,
            approved_budget=approved_budget,
            duration=duration,
            location=location,
            latitude=latitude,
            longitude=longitude,
            is_remote=bool(data.get('is_remote', True)),
            client_id=session['user_id'],
            halal_compliant=bool(data.get('halal_compliant', True)),
            is_instant_payout=bool(data.get('is_instant_payout', False)),
            is_brand_partnership=bool(data.get('is_brand_partnership', False)),
            skills_required=json.dumps(skills_required),
            deadline=deadline
        )

        db.session.add(new_gig)
        db.session.commit()

        return jsonify({
            'message': 'Gig created successfully',
            'gig_id': new_gig.id
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Create gig error: {str(e)}")
        return jsonify({'error': 'Failed to create gig. Please try again.'}), 500

@app.route('/api/gigs/<int:gig_id>', methods=['GET'])
def get_gig(gig_id):
    gig = Gig.query.get_or_404(gig_id)
    # Handle None case for views count (existing gigs may have None)
    gig.views = (gig.views or 0) + 1
    db.session.commit()
    
    client = User.query.get(gig.client_id)
    
    return jsonify({
        'id': gig.id,
        'title': gig.title,
        'description': gig.description,
        'category': gig.category,
        'budget_min': gig.budget_min,
        'budget_max': gig.budget_max,
        'approved_budget': gig.approved_budget,
        'location': gig.location,
        'is_remote': gig.is_remote,
        'status': gig.status,
        'halal_compliant': gig.halal_compliant,
        'halal_verified': gig.halal_verified,
        'duration': gig.duration,
        'views': gig.views,
        'applications': gig.applications,
        'created_at': gig.created_at.isoformat(),
        'deadline': gig.deadline.isoformat() if gig.deadline else None,
        'client': {
            'id': client.id,
            'username': client.username,
            'rating': client.rating,
            'is_verified': client.is_verified
        }
    })

@app.route('/api/gigs/<int:gig_id>/apply', methods=['POST'])
@api_rate_limit(requests_per_minute=20)
def apply_to_gig(gig_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json
        gig = Gig.query.get_or_404(gig_id)

        # Check if gig is still open
        if gig.status != 'open':
            return jsonify({'error': 'This gig is no longer accepting applications'}), 400

        # Prevent clients from applying to their own gigs
        if gig.client_id == session['user_id']:
            return jsonify({'error': 'Cannot apply to your own gig'}), 400

        # Check if already applied
        existing = Application.query.filter_by(gig_id=gig_id, freelancer_id=session['user_id']).first()
        if existing:
            return jsonify({'error': 'Already applied to this gig'}), 400

        # Sanitize and validate inputs
        cover_letter = sanitize_input(data.get('cover_letter', ''), max_length=2000)

        # Validate proposed price
        proposed_price = None
        if data.get('proposed_price'):
            try:
                proposed_price = float(data['proposed_price'])
                if proposed_price < 0 or proposed_price > 1000000:
                    return jsonify({'error': 'Invalid proposed price'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid price format'}), 400

        # Sanitize video pitch URL (basic validation)
        video_pitch = sanitize_input(data.get('video_pitch', ''), max_length=255)
        if video_pitch and not re.match(r'^https?://', video_pitch):
            return jsonify({'error': 'Video pitch must be a valid URL'}), 400

        application = Application(
            gig_id=gig_id,
            freelancer_id=session['user_id'],
            cover_letter=cover_letter,
            proposed_price=proposed_price,
            video_pitch=video_pitch
        )

        # Handle None case for applications count (existing gigs may have None)
        gig.applications = (gig.applications or 0) + 1

        db.session.add(application)
        db.session.commit()

        # Send email notification to client
        try:
            # Get client and worker information
            client = User.query.get(gig.client_id)
            worker = User.query.get(session['user_id'])

            if client and client.email and worker:
                # Get base URL for links
                base_url = os.environ.get('BASE_URL', 'https://gighala.com')

                # Render email template
                html_content = render_template(
                    'email_new_bid.html',
                    client_name=client.full_name or client.username,
                    worker_name=worker.full_name or worker.username,
                    worker_id=worker.id,
                    worker_username=worker.username,
                    worker_rating=worker.rating or 0,
                    worker_review_count=worker.review_count or 0,
                    gig_id=gig.id,
                    gig_code=gig.gig_code,
                    gig_title=gig.title,
                    gig_category=gig.category,
                    gig_budget_min=gig.budget_min,
                    gig_budget_max=gig.budget_max,
                    gig_location=gig.location,
                    proposed_price=proposed_price,
                    cover_letter=cover_letter,
                    base_url=base_url
                )

                # Prepare plain text version
                text_content = f"""
New Bid Received!

Hi {client.full_name or client.username},

{worker.full_name or worker.username} has submitted a bid for your gig.

Gig: {gig.title} ({gig.gig_code})
Category: {gig.category}
Your Budget: RM {gig.budget_min} - RM {gig.budget_max}
Proposed Price: RM {proposed_price if proposed_price else 'Not specified'}

Cover Letter:
{cover_letter if cover_letter else 'No cover letter provided'}

View all bids: {base_url}/gig/{gig.id}
View worker profile: {base_url}/profile/{worker.id}

---
GigHala - Your Trusted Gig Platform
                """.strip()

                # Send the email
                email_service.send_single_email(
                    to_email=client.email,
                    to_name=client.full_name or client.username,
                    subject=f"New bid received for {gig.title}",
                    html_content=html_content,
                    text_content=text_content
                )

                app.logger.info(f"Sent new bid notification email to client {client.id} for gig {gig.id}")

                # Send SMS notification to client
                if client.phone and client.phone_verified:
                    sms_text = f"GigHala: New bid received from {worker.full_name or worker.username} for '{gig.title}'. Proposed price: RM {proposed_price if proposed_price else 'Not specified'}. View details on your dashboard."
                    send_transaction_sms_notification(client.phone, sms_text)
                    app.logger.info(f"Sent new bid SMS to client {client.id} for gig {gig.id}")

        except Exception as e:
            # Log error but don't fail the application submission
            app.logger.error(f"Failed to send bid notification email: {str(e)}")

        return jsonify({'message': 'Application submitted successfully'}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Apply to gig error: {str(e)}")
        return jsonify({'error': 'Failed to submit application. Please try again.'}), 500

# ============================================================================
# GIG REFERENCE PHOTOS (Client uploads when posting gig)
# ============================================================================

@app.route('/api/gigs/<int:gig_id>/gig-photos', methods=['POST'])
def upload_gig_photo(gig_id):
    """Upload reference photos for a gig (client only, when posting/editing gig)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Verify gig exists
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client (gig owner) can upload reference photos
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the gig owner can upload reference photos'}), 403

        # Check if file is present
        if 'photo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['photo']

        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, 'gig_photos', unique_filename)
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Get optional caption and photo type from form data
        caption = request.form.get('caption', '')
        photo_type = request.form.get('photo_type', 'reference')

        # Validate photo_type
        valid_types = ['reference', 'example', 'inspiration']
        if photo_type not in valid_types:
            photo_type = 'reference'

        # Create GigPhoto record
        gig_photo = GigPhoto(
            gig_id=gig_id,
            uploader_id=user_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            caption=caption[:500] if caption else None,  # Limit caption length
            photo_type=photo_type,
            mime_type=get_mime_type(original_filename)
        )

        db.session.add(gig_photo)
        db.session.commit()

        return jsonify({
            'message': 'Reference photo uploaded successfully',
            'photo': gig_photo.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Upload gig photo error: {str(e)}")
        # Clean up file if it was saved but DB insert failed
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': 'Failed to upload photo. Please try again.'}), 500

@app.route('/api/gigs/<int:gig_id>/gig-photos', methods=['GET'])
def get_gig_photos(gig_id):
    """Get all reference photos for a gig"""
    try:
        # Verify gig exists
        gig = Gig.query.get_or_404(gig_id)

        # Get all gig photos
        gig_photos = GigPhoto.query.filter_by(gig_id=gig_id).order_by(GigPhoto.created_at.asc()).all()

        return jsonify({
            'gig_id': gig_id,
            'photos': [photo.to_dict() for photo in gig_photos],
            'total_photos': len(gig_photos)
        }), 200

    except Exception as e:
        app.logger.error(f"Get gig photos error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve photos. Please try again.'}), 500

@app.route('/api/gig-photos/<int:photo_id>', methods=['DELETE'])
def delete_gig_photo(photo_id):
    """Delete a gig reference photo (client only)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig_photo = GigPhoto.query.get_or_404(photo_id)
        user_id = session['user_id']

        # Get the gig to check ownership
        gig = Gig.query.get(gig_photo.gig_id)

        # Only gig owner (client) can delete
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the gig owner can delete reference photos'}), 403

        # Delete file from filesystem
        if os.path.exists(gig_photo.file_path):
            os.remove(gig_photo.file_path)

        # Delete database record
        db.session.delete(gig_photo)
        db.session.commit()

        return jsonify({'message': 'Reference photo deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete gig photo error: {str(e)}")
        return jsonify({'error': 'Failed to delete photo. Please try again.'}), 500

@app.route('/uploads/gig_photos/<filename>')
def serve_gig_photo(filename):
    """Serve gig reference photos (public access)"""
    try:
        photo_dir = os.path.join(UPLOAD_FOLDER, 'gig_photos')
        file_path = os.path.join(photo_dir, filename)

        # Check if file exists
        if not os.path.exists(file_path):
            app.logger.warning(f"Gig photo not found: {filename}")
            # Return a 404 response that the frontend can handle
            return "Photo not found", 404

        # Gig photos are public, anyone can view them
        return send_from_directory(photo_dir, filename)
    except Exception as e:
        app.logger.error(f"Serve gig photo error: {str(e)}")
        return jsonify({'error': 'Failed to load photo'}), 500

# ============================================================================
# WORK PHOTOS (Freelancer uploads during work execution)
# ============================================================================

@app.route('/api/gigs/<int:gig_id>/work-photos', methods=['POST'])
def upload_work_photo(gig_id):
    """Upload work photos for a gig (freelancer or client)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Verify gig exists
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Determine uploader type (freelancer or client)
        uploader_type = None
        if gig.freelancer_id == user_id:
            uploader_type = 'freelancer'
        elif gig.client_id == user_id:
            uploader_type = 'client'
        else:
            return jsonify({'error': 'You are not authorized to upload photos for this gig'}), 403

        # Check if file is present
        if 'photo' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['photo']

        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, 'work_photos', unique_filename)
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Get optional caption and upload stage from form data
        caption = request.form.get('caption', '')
        upload_stage = request.form.get('upload_stage', 'work_in_progress')

        # Validate upload_stage
        valid_stages = ['work_in_progress', 'completed', 'revision']
        if upload_stage not in valid_stages:
            upload_stage = 'work_in_progress'

        # Create WorkPhoto record
        work_photo = WorkPhoto(
            gig_id=gig_id,
            uploader_id=user_id,
            uploader_type=uploader_type,
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            caption=caption[:500] if caption else None,  # Limit caption length
            upload_stage=upload_stage
        )

        db.session.add(work_photo)
        db.session.commit()

        return jsonify({
            'message': 'Photo uploaded successfully',
            'photo': work_photo.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Upload work photo error: {str(e)}")
        # Clean up file if it was saved but DB insert failed
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({'error': 'Failed to upload photo. Please try again.'}), 500

@app.route('/api/gigs/<int:gig_id>/work-photos', methods=['GET'])
def get_work_photos(gig_id):
    """Get all work photos for a gig"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Verify gig exists
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Check if user is authorized to view photos (freelancer, client, or admin)
        user = User.query.get(user_id)
        if not (gig.freelancer_id == user_id or gig.client_id == user_id or user.is_admin):
            return jsonify({'error': 'You are not authorized to view photos for this gig'}), 403

        # Get all work photos for this gig
        work_photos = WorkPhoto.query.filter_by(gig_id=gig_id).order_by(WorkPhoto.created_at.desc()).all()

        return jsonify({
            'gig_id': gig_id,
            'photos': [photo.to_dict() for photo in work_photos],
            'total_photos': len(work_photos)
        }), 200

    except Exception as e:
        app.logger.error(f"Get work photos error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve photos. Please try again.'}), 500

@app.route('/api/work-photos/<int:photo_id>', methods=['DELETE'])
def delete_work_photo(photo_id):
    """Delete a work photo"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        work_photo = WorkPhoto.query.get_or_404(photo_id)
        user_id = session['user_id']
        user = User.query.get(user_id)

        # Check if user is authorized to delete (uploader or admin)
        if not (work_photo.uploader_id == user_id or user.is_admin):
            return jsonify({'error': 'You are not authorized to delete this photo'}), 403

        # Delete file from filesystem
        if os.path.exists(work_photo.file_path):
            os.remove(work_photo.file_path)

        # Delete database record
        db.session.delete(work_photo)
        db.session.commit()

        return jsonify({'message': 'Photo deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete work photo error: {str(e)}")
        return jsonify({'error': 'Failed to delete photo. Please try again.'}), 500

@app.route('/uploads/work_photos/<filename>')
def serve_work_photo(filename):
    """Serve uploaded work photos"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get the work photo record to verify access
        work_photo = WorkPhoto.query.filter_by(filename=filename).first_or_404()
        user_id = session['user_id']
        user = User.query.get(user_id)

        # Get the gig to check authorization
        gig = Gig.query.get(work_photo.gig_id)

        # Check if user is authorized to view (freelancer, client, or admin)
        if not (gig.freelancer_id == user_id or gig.client_id == user_id or user.is_admin):
            return jsonify({'error': 'You are not authorized to view this photo'}), 403

        # Check if file exists
        photo_dir = os.path.join(UPLOAD_FOLDER, 'work_photos')
        file_path = os.path.join(photo_dir, filename)

        if not os.path.exists(file_path):
            app.logger.warning(f"Work photo not found: {filename}")
            return "Photo not found", 404

        # Serve the file
        return send_from_directory(photo_dir, filename)

    except Exception as e:
        app.logger.error(f"Serve work photo error: {str(e)}")
        return jsonify({'error': 'Failed to load photo'}), 500

@app.route('/uploads/portfolio/<filename>')
def serve_portfolio_photo(filename):
    """Serve uploaded portfolio photos (public)"""
    try:
        # Validate filename to prevent path traversal
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        file_path = os.path.join(UPLOAD_FOLDER, 'portfolio', safe_filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Portfolio images are public for profile viewing
        return send_from_directory(os.path.join(UPLOAD_FOLDER, 'portfolio'), safe_filename)
    except Exception as e:
        app.logger.error(f"Serve portfolio photo error: {str(e)}")
        return jsonify({'error': 'Failed to load photo'}), 500

@app.route('/uploads/verification/<filename>')
def serve_verification_photo(filename):
    """Serve verification photos (admin and owner only)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Validate filename to prevent path traversal
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Extract user_id from filename (format: {user_id}_{field}_{uuid}_{original})
        try:
            file_user_id = int(filename.split('_')[0])
        except (ValueError, IndexError):
            return jsonify({'error': 'Invalid filename format'}), 400
        
        # Only allow admin or the owner to view verification files
        if not user.is_admin and user_id != file_user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        file_path = os.path.join(UPLOAD_FOLDER, 'verification', safe_filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_from_directory(os.path.join(UPLOAD_FOLDER, 'verification'), safe_filename)
    except Exception as e:
        app.logger.error(f"Serve verification photo error: {str(e)}")
        return jsonify({'error': 'Failed to load photo'}), 500

# ============================================================================
# GIG WORKFLOW: CLIENT TO WORKER COMPLETE PROCESS
# ============================================================================

@app.route('/api/gigs/<int:gig_id>/applications', methods=['GET'])
def get_gig_applications(gig_id):
    """Get all applications for a gig (client only)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can view applications for their gig
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the gig owner can view applications'}), 403

        # Get all applications with freelancer details
        applications = Application.query.filter_by(gig_id=gig_id).all()

        result = []
        for app in applications:
            freelancer = User.query.get(app.freelancer_id)
            result.append({
                'id': app.id,
                'gig_id': app.gig_id,
                'freelancer': {
                    'id': freelancer.id,
                    'username': freelancer.username,
                    'full_name': freelancer.full_name,
                    'rating': freelancer.rating,
                    'review_count': freelancer.review_count,
                    'completed_gigs': freelancer.completed_gigs,
                    'bio': freelancer.bio,
                    'location': freelancer.location,
                    'skills': json.loads(freelancer.skills) if freelancer.skills else [],
                    'is_verified': freelancer.is_verified,
                    'halal_verified': freelancer.halal_verified
                },
                'cover_letter': app.cover_letter,
                'proposed_price': app.proposed_price,
                'video_pitch': app.video_pitch,
                'status': app.status,
                'created_at': app.created_at.isoformat()
            })

        return jsonify({
            'gig_id': gig_id,
            'applications': result,
            'total_applications': len(result)
        }), 200

    except Exception as e:
        app.logger.error(f"Get applications error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve applications'}), 500

@app.route('/api/applications/<int:application_id>/accept', methods=['POST'])
def accept_application(application_id):
    """Client accepts a freelancer's application"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        application = Application.query.get_or_404(application_id)
        gig = Gig.query.get(application.gig_id)
        user_id = session['user_id']

        # Only client can accept applications
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the gig owner can accept applications'}), 403

        # Check if gig is still open
        if gig.status != 'open':
            return jsonify({'error': 'This gig is no longer accepting applications'}), 400

        # Accept this application
        application.status = 'accepted'

        # Assign freelancer to gig and set agreed amount
        gig.freelancer_id = application.freelancer_id
        gig.status = 'in_progress'
        # Store the freelancer's proposed price as the agreed amount
        gig.agreed_amount = application.proposed_price if application.proposed_price else gig.budget_min

        # Reject all other pending applications for this gig
        other_applications = Application.query.filter(
            Application.gig_id == gig.id,
            Application.id != application_id,
            Application.status == 'pending'
        ).all()

        for other_app in other_applications:
            other_app.status = 'rejected'

        # Auto-create conversation between client and freelancer
        existing_conv = Conversation.query.filter(
            ((Conversation.participant_1_id == user_id) & (Conversation.participant_2_id == application.freelancer_id)) |
            ((Conversation.participant_1_id == application.freelancer_id) & (Conversation.participant_2_id == user_id))
        ).first()

        if not existing_conv:
            conversation = Conversation(
                participant_1_id=user_id,
                participant_2_id=application.freelancer_id,
                gig_id=gig.id
            )
            db.session.add(conversation)
            db.session.flush()  # Flush to get the conversation ID

            # Add a system message to notify about the acceptance
            system_message = Message(
                conversation_id=conversation.id,
                sender_id=user_id,
                content=f"Application accepted! Let's discuss the details of '{gig.title}'.",
                message_type='text'
            )
            conversation.last_message_at = datetime.utcnow()
            db.session.add(system_message)
        elif existing_conv and existing_conv.gig_id != gig.id:
            # Update the existing conversation to link it to this gig
            existing_conv.gig_id = gig.id

        db.session.commit()

        # Send email and SMS notification to freelancer
        freelancer = User.query.get(application.freelancer_id)
        if freelancer:
            # Send email notification
            try:
                subject = "Application Accepted!"
                message = f"Congratulations! Your application for '{gig.title}' has been accepted by the client. You can now start working on the project."

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #2ecc71; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🎉 Application Accepted!</h2>
                        </div>
                        <div class="content">
                            <p>Hi {freelancer.full_name or freelancer.username},</p>
                            <p>Great news! Your application for <strong>"{gig.title}"</strong> has been accepted.</p>
                            <p><strong>Agreed Amount:</strong> RM {gig.agreed_amount if gig.agreed_amount else gig.budget_min}</p>
                            <p>You can now start working on the project. Check your dashboard for more details and to communicate with the client.</p>
                            <p>Good luck with your project!</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Application Accepted!

Hi {freelancer.full_name or freelancer.username},

Great news! Your application for "{gig.title}" has been accepted.

Agreed Amount: RM {gig.agreed_amount if gig.agreed_amount else gig.budget_min}

You can now start working on the project. Check your dashboard for more details.

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=freelancer.email,
                    to_name=freelancer.full_name or freelancer.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent application accepted email to freelancer {freelancer.id}")

            except Exception as e:
                app.logger.error(f"Failed to send application accepted email: {str(e)}")

            # Send SMS notification if phone is verified
            if freelancer.phone and freelancer.phone_verified:
                sms_message = f"GigHala: Congratulations! Your application for '{gig.title}' has been accepted. Check your dashboard to start working!"
                send_transaction_sms_notification(freelancer.phone, sms_message)

        return jsonify({
            'message': 'Application accepted successfully',
            'gig': {
                'id': gig.id,
                'status': gig.status,
                'freelancer_id': gig.freelancer_id
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Accept application error: {str(e)}")
        return jsonify({'error': 'Failed to accept application'}), 500

@app.route('/api/applications/<int:application_id>/reject', methods=['POST'])
def reject_application(application_id):
    """Client rejects a freelancer's application"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        application = Application.query.get_or_404(application_id)
        gig = Gig.query.get(application.gig_id)
        user_id = session['user_id']

        # Only client can reject applications
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the gig owner can reject applications'}), 403

        # Can only reject pending applications
        if application.status != 'pending':
            return jsonify({'error': 'Can only reject pending applications'}), 400

        application.status = 'rejected'
        db.session.commit()

        # Send email and SMS notification to freelancer about rejection
        freelancer = User.query.get(application.freelancer_id)
        if freelancer:
            try:
                subject = "Application Not Selected"
                message = f"Thank you for your interest in '{gig.title}'. Unfortunately, your application was not selected this time. Keep applying to other gigs!"

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Application Update</h2>
                        </div>
                        <div class="content">
                            <p>Hi {freelancer.full_name or freelancer.username},</p>
                            <p>Thank you for your interest in <strong>"{gig.title}"</strong>.</p>
                            <p>Unfortunately, your application was not selected for this project. Don't be discouraged! There are many other opportunities available on GigHala.</p>
                            <p>Keep applying and showcasing your skills. Your next great project is just around the corner!</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Application Update

Hi {freelancer.full_name or freelancer.username},

Thank you for your interest in "{gig.title}".

Unfortunately, your application was not selected for this project. Don't be discouraged! There are many other opportunities available on GigHala.

Keep applying and showcasing your skills!

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=freelancer.email,
                    to_name=freelancer.full_name or freelancer.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent application rejection email to freelancer {freelancer.id}")

            except Exception as e:
                app.logger.error(f"Failed to send application rejection email: {str(e)}")

            # Send SMS notification if phone is verified
            if freelancer.phone and freelancer.phone_verified:
                sms_text = f"GigHala: Your application for '{gig.title}' was not selected. Keep applying to other opportunities!"
                send_transaction_sms_notification(freelancer.phone, sms_text)
                app.logger.info(f"Sent application rejection SMS to freelancer {freelancer.id}")

        return jsonify({'message': 'Application rejected successfully'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Reject application error: {str(e)}")
        return jsonify({'error': 'Failed to reject application'}), 500

@app.route('/api/gigs/<int:gig_id>', methods=['GET'])
def get_gig_details(gig_id):
    """Get gig details with client information and photos"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Check if user has access to this gig
        if gig.client_id != user_id and gig.freelancer_id != user_id:
            # Check if user has an application for this gig
            application = Application.query.filter_by(gig_id=gig_id, freelancer_id=user_id).first()
            if not application:
                return jsonify({'error': 'Unauthorized'}), 403

        # Get client information
        client = User.query.get(gig.client_id)

        # Get gig photos
        photos = WorkPhoto.query.filter_by(gig_id=gig_id).all()

        return jsonify({
            'id': gig.id,
            'title': gig.title,
            'description': gig.description,
            'category': gig.category,
            'budget_min': gig.budget_min,
            'budget_max': gig.budget_max,
            'status': gig.status,
            'client': {
                'id': client.id,
                'username': client.username,
                'full_name': client.full_name
            } if client else None,
            'photos': [photo.to_dict() for photo in photos]
        }), 200

    except Exception as e:
        app.logger.error(f"Get gig details error: {str(e)}")
        return jsonify({'error': 'Failed to fetch gig details'}), 500

@app.route('/api/gigs/<int:gig_id>/mark-completed', methods=['POST'])
def mark_gig_completed(gig_id):
    """Freelancer marks work as completed (ready for client to release payment)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only assigned freelancer can mark work as completed
        if gig.freelancer_id != user_id:
            return jsonify({'error': 'Only the assigned freelancer can mark work as completed'}), 403

        # Gig must be in progress
        if gig.status != 'in_progress':
            return jsonify({'error': 'Gig must be in progress to mark as completed'}), 400

        # Check if escrow is funded
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        if not escrow or escrow.status != 'funded':
            return jsonify({'error': 'Escrow must be funded before completing work'}), 400

        # Get completion notes from form data
        completion_notes = request.form.get('completion_notes', '')

        # Update application status with completion notes
        application = Application.query.filter_by(
            gig_id=gig_id,
            freelancer_id=user_id,
            status='accepted'
        ).first()

        if application:
            application.work_submitted = True
            application.work_submission_date = datetime.utcnow()
            application.completion_notes = completion_notes

        # Handle completion photo uploads
        completion_photos = request.files.getlist('completion_photos')
        if completion_photos:
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads/work_photos')
            os.makedirs(upload_folder, exist_ok=True)

            for photo in completion_photos:
                if photo and photo.filename:
                    # Secure filename and save
                    filename = secure_filename(photo.filename)
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{gig_id}_{user_id}_{timestamp}_{filename}"
                    file_path = os.path.join(upload_folder, unique_filename)
                    photo.save(file_path)

                    # Create WorkPhoto record
                    work_photo = WorkPhoto(
                        gig_id=gig_id,
                        uploader_id=user_id,
                        uploader_type='freelancer',
                        filename=unique_filename,
                        original_filename=filename,
                        file_path=f'/uploads/work_photos/{unique_filename}',
                        file_size=os.path.getsize(file_path),
                        caption='Completion proof',
                        upload_stage='completed'
                    )
                    db.session.add(work_photo)

        # Mark gig as completed
        gig.status = 'completed'

        # Auto-generate invoice when work is completed
        # Check if invoice already exists
        existing_invoice = Invoice.query.filter_by(gig_id=gig_id).first()

        if not existing_invoice:
            # Generate invoice number
            import random
            invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

            # Calculate commission using tiered structure
            commission = calculate_commission(escrow.amount)
            net_amount = escrow.amount - commission

            # Create invoice with 'issued' status and auto-submit
            current_time = datetime.utcnow()
            invoice = Invoice(
                invoice_number=invoice_number,
                transaction_id=None,  # Transaction will be created when payment is released
                gig_id=gig_id,
                client_id=gig.client_id,
                freelancer_id=gig.freelancer_id,
                amount=escrow.amount,
                platform_fee=commission,
                tax_amount=0.0,
                total_amount=escrow.amount,
                status='issued',  # Invoice is issued but not yet paid
                payment_method='escrow',
                payment_reference=escrow.payment_reference,
                notes=f'Invoice for completed work: {gig.title}',
                # Auto-submit invoice fields
                invoice_submitted=True,
                freelancer_invoice_number=invoice_number,
                freelancer_invoice_date=current_time,
                freelancer_submitted_at=current_time,
                freelancer_invoice_notes='Automatically generated invoice'
            )
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID

            invoice_created = True
            invoice_info = {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'amount': invoice.amount,
                'platform_fee': commission,
                'net_amount': net_amount
            }
        else:
            invoice_created = False
            invoice_info = {
                'id': existing_invoice.id,
                'invoice_number': existing_invoice.invoice_number,
                'status': 'already_exists'
            }

        db.session.commit()

        # Create notification for client
        notification = Notification(
            user_id=gig.client_id,
            notification_type='work_completed',
            title='Work Completed - Invoice Ready',
            message=f'Freelancer has completed work for: {gig.title}. Invoice #{invoice_info["invoice_number"]} has been automatically generated. You can now release payment.',
            link=f'/gig/{gig.id}'
        )
        db.session.add(notification)
        db.session.commit()

        return jsonify({
            'message': 'Work marked as completed! Invoice automatically generated and submitted. Client can now release payment.',
            'gig': {
                'id': gig.id,
                'status': gig.status
            },
            'invoice': invoice_info,
            'invoice_created': invoice_created
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Mark gig completed error: {str(e)}")
        return jsonify({'error': 'Failed to mark gig as completed'}), 500

@app.route('/api/gigs/<int:gig_id>/submit-invoice', methods=['POST'])
def submit_freelancer_invoice(gig_id):
    """Freelancer submits their invoice for a completed gig"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only assigned freelancer can submit invoice
        if gig.freelancer_id != user_id:
            return jsonify({'error': 'Only the assigned freelancer can submit invoice'}), 403

        # Gig must be completed
        if gig.status != 'completed':
            return jsonify({'error': 'Work must be marked as completed before submitting invoice'}), 400

        # Get the invoice for this gig
        invoice = Invoice.query.filter_by(gig_id=gig_id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found. Please mark work as completed first.'}), 404

        # Check if invoice already submitted
        if invoice.invoice_submitted:
            return jsonify({'error': 'Invoice has already been submitted'}), 400

        # Get invoice details from request
        freelancer_invoice_number = request.form.get('invoice_number', '').strip()
        invoice_date_str = request.form.get('invoice_date', '')
        invoice_notes = request.form.get('notes', '')

        # Validate required fields
        if not freelancer_invoice_number:
            return jsonify({'error': 'Invoice number is required'}), 400

        # Parse invoice date
        freelancer_invoice_date = None
        if invoice_date_str:
            try:
                freelancer_invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid invoice date format. Use YYYY-MM-DD'}), 400

        # Handle invoice file upload (optional)
        invoice_file_path = None
        invoice_file = request.files.get('invoice_file')
        if invoice_file and invoice_file.filename:
            # Create upload directory
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads/invoices')
            os.makedirs(upload_folder, exist_ok=True)

            # Secure filename and save
            filename = secure_filename(invoice_file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"invoice_{gig_id}_{user_id}_{timestamp}_{filename}"
            file_path = os.path.join(upload_folder, unique_filename)
            invoice_file.save(file_path)

            invoice_file_path = f'/uploads/invoices/{unique_filename}'

        # Update invoice with freelancer submission details
        invoice.invoice_submitted = True
        invoice.freelancer_invoice_number = freelancer_invoice_number
        invoice.freelancer_invoice_date = freelancer_invoice_date or datetime.utcnow()
        invoice.freelancer_submitted_at = datetime.utcnow()
        invoice.freelancer_invoice_file = invoice_file_path
        invoice.freelancer_invoice_notes = invoice_notes

        db.session.commit()

        # Create notification for client
        notification = Notification(
            user_id=gig.client_id,
            notification_type='invoice_submitted',
            title='Invoice Submitted',
            message=f'Freelancer has submitted invoice #{freelancer_invoice_number} for: {gig.title}. You can now release payment.',
            link=f'/gig/{gig.id}'
        )
        db.session.add(notification)
        db.session.commit()

        return jsonify({
            'message': 'Invoice submitted successfully! Client can now release payment.',
            'invoice': {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'freelancer_invoice_number': freelancer_invoice_number,
                'invoice_submitted': True,
                'submitted_at': invoice.freelancer_submitted_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Submit invoice error: {str(e)}")
        return jsonify({'error': 'Failed to submit invoice'}), 500

@app.route('/api/gigs/<int:gig_id>/submit-work', methods=['POST'])
def submit_work(gig_id):
    """Freelancer submits work for client review"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only assigned freelancer can submit work
        if gig.freelancer_id != user_id:
            return jsonify({'error': 'Only the assigned freelancer can submit work'}), 403

        # Gig must be in progress
        if gig.status != 'in_progress':
            return jsonify({'error': 'Gig must be in progress to submit work'}), 400

        # Check if work photos were uploaded
        work_photos = WorkPhoto.query.filter_by(
            gig_id=gig_id,
            uploader_id=user_id,
            uploader_type='freelancer'
        ).count()

        if work_photos == 0:
            return jsonify({'error': 'Please upload at least one work photo before submitting'}), 400

        # Update application status
        application = Application.query.filter_by(
            gig_id=gig_id,
            freelancer_id=user_id,
            status='accepted'
        ).first()

        if application:
            application.work_submitted = True
            application.work_submission_date = datetime.utcnow()

        # Update gig status to pending review
        gig.status = 'pending_review'

        # Create invoice for the client
        # Check if invoice already exists for this gig
        existing_invoice = Invoice.query.filter_by(gig_id=gig_id).first()

        if not existing_invoice:
            # Get the agreed amount from the gig
            amount = gig.agreed_amount if gig.agreed_amount else gig.budget

            # Calculate commission using tiered structure
            commission = calculate_commission(amount)

            # Generate invoice number
            import random
            invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

            # Create invoice with status 'issued' (not yet paid)
            invoice = Invoice(
                invoice_number=invoice_number,
                gig_id=gig_id,
                client_id=gig.client_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=commission,
                tax_amount=0.0,
                total_amount=amount,
                status='issued',  # Will be marked as 'paid' when client pays
                due_date=datetime.utcnow() + timedelta(days=7),  # 7 days to pay
                notes=f'Invoice for completed work: {gig.title}'
            )
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID

            # Create notification for client about the invoice
            client_notification = Notification(
                user_id=gig.client_id,
                notification_type='payment',
                title='Invoice Created',
                message=f'Invoice {invoice_number} created for gig: {gig.title}. Amount: MYR {amount:.2f}',
                link=f'/invoice/{invoice.id}',
                related_id=invoice.id
            )
            db.session.add(client_notification)

            # Create notification for worker about the invoice
            worker_notification = Notification(
                user_id=gig.freelancer_id,
                notification_type='payment',
                title='Invoice Issued',
                message=f'Invoice {invoice_number} issued to client for gig: {gig.title}. You will receive MYR {amount - commission:.2f} after payment.',
                link=f'/invoice/{invoice.id}',
                related_id=invoice.id
            )
            db.session.add(worker_notification)

        db.session.commit()

        # Send email and SMS notifications to client about work submission
        client = User.query.get(gig.client_id)
        freelancer = User.query.get(gig.freelancer_id)

        if client and freelancer:
            try:
                subject = "Work Submitted for Review"
                message = f"{freelancer.full_name or freelancer.username} has submitted work for '{gig.title}'. Please review and approve or request revisions."

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #2ecc71; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Work Submitted for Review</h2>
                        </div>
                        <div class="content">
                            <p>Hi {client.full_name or client.username},</p>
                            <p><strong>{freelancer.full_name or freelancer.username}</strong> has submitted completed work for your gig: <strong>"{gig.title}"</strong></p>
                            <p><strong>Invoice:</strong> {invoice_number if not existing_invoice else existing_invoice.invoice_number}</p>
                            <p><strong>Amount:</strong> MYR {amount:.2f}</p>
                            <p>Please review the submitted work and either approve it or request revisions.</p>
                            <p>Login to your dashboard to review the work.</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Work Submitted for Review

Hi {client.full_name or client.username},

{freelancer.full_name or freelancer.username} has submitted completed work for "{gig.title}".

Invoice: {invoice_number if not existing_invoice else existing_invoice.invoice_number}
Amount: MYR {amount:.2f}

Please review the submitted work and either approve it or request revisions.

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=client.email,
                    to_name=client.full_name or client.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent work submission email to client {client.id}")

            except Exception as e:
                app.logger.error(f"Failed to send work submission email: {str(e)}")

            # Send SMS notification to client if phone is verified
            if client.phone and client.phone_verified:
                sms_text = f"GigHala: {freelancer.full_name or freelancer.username} submitted work for '{gig.title}'. Please review. Invoice: MYR {amount:.2f}"
                send_transaction_sms_notification(client.phone, sms_text)
                app.logger.info(f"Sent work submission SMS to client {client.id}")

        return jsonify({
            'message': 'Work submitted successfully. Invoice created and shared. Waiting for client review.',
            'gig': {
                'id': gig.id,
                'status': gig.status,
                'work_photos_count': work_photos
            },
            'invoice': {
                'id': invoice.id if not existing_invoice else existing_invoice.id,
                'invoice_number': invoice.invoice_number if not existing_invoice else existing_invoice.invoice_number
            } if not existing_invoice or invoice else None
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Submit work error: {str(e)}")
        return jsonify({'error': 'Failed to submit work'}), 500

@app.route('/api/gigs/<int:gig_id>/approve-work', methods=['POST'])
def approve_work(gig_id):
    """Client approves completed work"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can approve work
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can approve work'}), 403

        # Gig must be pending review
        if gig.status != 'pending_review':
            return jsonify({'error': 'No work submitted for review'}), 400

        # Mark gig as completed
        gig.status = 'completed'

        # Update freelancer stats
        freelancer = User.query.get(gig.freelancer_id)
        freelancer.completed_gigs += 1

        # Check if escrow exists and send reminder notification
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        invoice = Invoice.query.filter_by(gig_id=gig_id).first()

        if escrow and escrow.status == 'funded':
            # Notify client to release payment
            client_notification = Notification(
                user_id=gig.client_id,
                notification_type='payment',
                title='Release Payment',
                message=f'Work approved for "{gig.title}". Please release the escrow payment to complete the transaction.',
                link=f'/escrow',
                related_id=gig.id
            )
            db.session.add(client_notification)

        # Notify freelancer that work was approved
        freelancer_notification = Notification(
            user_id=gig.freelancer_id,
            notification_type='work_completed',
            title='Work Approved',
            message=f'Your work for "{gig.title}" has been approved by the client. Awaiting payment release.',
            link=f'/gig/{gig.id}',
            related_id=gig.id
        )
        db.session.add(freelancer_notification)

        db.session.commit()

        # Send email and SMS notifications to freelancer about work approval
        client = User.query.get(gig.client_id)

        if freelancer and client:
            try:
                subject = "Work Approved!"
                message = f"Great news! Your work for '{gig.title}' has been approved by {client.full_name or client.username}. Payment will be released soon."

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #2ecc71; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🎉 Work Approved!</h2>
                        </div>
                        <div class="content">
                            <p>Hi {freelancer.full_name or freelancer.username},</p>
                            <p>Congratulations! Your work for <strong>"{gig.title}"</strong> has been approved by the client.</p>
                            <p><strong>Project:</strong> {gig.title}</p>
                            <p><strong>Status:</strong> Completed</p>
                            {f'<p><strong>Amount:</strong> MYR {invoice.amount:.2f}</p>' if invoice else ''}
                            <p>The client will release payment soon. You will be notified when the payment is processed.</p>
                            <p>Thank you for your excellent work!</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Work Approved!

Hi {freelancer.full_name or freelancer.username},

Congratulations! Your work for "{gig.title}" has been approved by the client.

Project: {gig.title}
Status: Completed
{f'Amount: MYR {invoice.amount:.2f}' if invoice else ''}

The client will release payment soon. You will be notified when the payment is processed.

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=freelancer.email,
                    to_name=freelancer.full_name or freelancer.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent work approval email to freelancer {freelancer.id}")

            except Exception as e:
                app.logger.error(f"Failed to send work approval email: {str(e)}")

            # Send SMS notification to freelancer if phone is verified
            if freelancer.phone and freelancer.phone_verified:
                sms_text = f"GigHala: Great news! Your work for '{gig.title}' has been approved. Payment will be released soon!"
                send_transaction_sms_notification(freelancer.phone, sms_text)
                app.logger.info(f"Sent work approval SMS to freelancer {freelancer.id}")

        return jsonify({
            'message': 'Work approved! Gig marked as completed. Please release payment if escrow is funded.',
            'gig': {
                'id': gig.id,
                'status': gig.status
            },
            'invoice': {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'status': invoice.status
            } if invoice else None,
            'has_escrow': escrow is not None and escrow.status == 'funded'
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Approve work error: {str(e)}")
        return jsonify({'error': 'Failed to approve work'}), 500

@app.route('/api/gigs/<int:gig_id>/request-revision', methods=['POST'])
def request_revision(gig_id):
    """Client requests revisions to submitted work"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can request revisions
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can request revisions'}), 403

        # Gig must be pending review
        if gig.status != 'pending_review':
            return jsonify({'error': 'No work submitted for review'}), 400

        # Get revision notes
        revision_notes = data.get('notes', '')

        # Change status back to in_progress
        gig.status = 'in_progress'

        # Update application
        application = Application.query.filter_by(
            gig_id=gig_id,
            freelancer_id=gig.freelancer_id,
            status='accepted'
        ).first()

        if application:
            application.work_submitted = False
            application.work_submission_date = None

        # Create in-app notification for freelancer
        revision_notification = Notification(
            user_id=gig.freelancer_id,
            notification_type='revision_request',
            title='Revision Requested',
            message=f'The client has requested revisions for "{gig.title}". Please review the feedback and resubmit.',
            link=f'/gig/{gig.id}',
            related_id=gig.id
        )
        db.session.add(revision_notification)

        db.session.commit()

        # Send email and SMS notifications to freelancer about revision request
        freelancer = User.query.get(gig.freelancer_id)
        client = User.query.get(gig.client_id)

        if freelancer and client:
            try:
                subject = "Revision Requested"
                message = f"The client has requested revisions for '{gig.title}'. Please review the feedback and make the necessary changes."

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #f39c12; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .revision-notes {{ background-color: #fff; border-left: 4px solid #f39c12; padding: 15px; margin: 15px 0; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Revision Requested</h2>
                        </div>
                        <div class="content">
                            <p>Hi {freelancer.full_name or freelancer.username},</p>
                            <p>The client <strong>{client.full_name or client.username}</strong> has requested revisions for your work on <strong>"{gig.title}"</strong>.</p>
                            {f'<div class="revision-notes"><strong>Client Feedback:</strong><br>{revision_notes}</div>' if revision_notes else '<p>No specific notes provided. Please contact the client for clarification.</p>'}
                            <p>Please review the feedback carefully, make the necessary changes, and resubmit your work.</p>
                            <p>Login to your dashboard to view the details and communicate with the client.</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Revision Requested

Hi {freelancer.full_name or freelancer.username},

The client {client.full_name or client.username} has requested revisions for your work on "{gig.title}".

{f'Client Feedback: {revision_notes}' if revision_notes else 'No specific notes provided. Please contact the client for clarification.'}

Please review the feedback carefully, make the necessary changes, and resubmit your work.

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=freelancer.email,
                    to_name=freelancer.full_name or freelancer.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent revision request email to freelancer {freelancer.id}")

            except Exception as e:
                app.logger.error(f"Failed to send revision request email: {str(e)}")

            # Send SMS notification to freelancer if phone is verified
            if freelancer.phone and freelancer.phone_verified:
                sms_text = f"GigHala: Revision requested for '{gig.title}'. Please review client feedback and resubmit your work."
                send_transaction_sms_notification(freelancer.phone, sms_text)
                app.logger.info(f"Sent revision request SMS to freelancer {freelancer.id}")

        return jsonify({
            'message': 'Revision requested. Freelancer has been notified.',
            'gig': {
                'id': gig.id,
                'status': gig.status
            },
            'revision_notes': revision_notes
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Request revision error: {str(e)}")
        return jsonify({'error': 'Failed to request revision'}), 500

@app.route('/api/gigs/<int:gig_id>/cancel', methods=['POST'])
def cancel_gig(gig_id):
    """Cancel a gig with automatic escrow refund and notifications"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json or {}
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can cancel
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can cancel the gig'}), 403

        # Cannot cancel completed gigs
        if gig.status == 'completed':
            return jsonify({'error': 'Cannot cancel completed gigs'}), 400

        # Cannot cancel already cancelled gigs
        if gig.status == 'cancelled':
            return jsonify({'error': 'Gig is already cancelled'}), 400

        cancellation_reason = data.get('reason', 'No reason provided')

        # Store cancellation details
        gig.cancellation_reason = cancellation_reason
        gig.cancelled_at = datetime.utcnow()
        old_status = gig.status
        gig.status = 'cancelled'

        # Handle escrow refund if gig was funded
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        refund_processed = False
        refund_amount = 0

        if escrow and escrow.status in ['funded', 'in_progress']:
            # Calculate remaining refund amount
            remaining_amount = escrow.amount - (escrow.refunded_amount or 0.0)

            if remaining_amount > 0:
                # Process Stripe refund if payment was made via Stripe
                stripe_refund_id = None
                if escrow.payment_gateway == 'stripe' and escrow.payment_reference:
                    try:
                        if stripe.api_key:
                            refund = stripe.Refund.create(
                                payment_intent=escrow.payment_reference,
                                amount=int(remaining_amount * 100),
                                reason='requested_by_customer',
                                metadata={
                                    'gig_id': str(gig_id),
                                    'escrow_id': str(escrow.id),
                                    'reason': cancellation_reason
                                }
                            )
                            stripe_refund_id = refund.id
                            app.logger.info(f"Stripe refund created: {stripe_refund_id} for RM{remaining_amount:.2f}")
                    except Exception as stripe_error:
                        app.logger.error(f"Stripe refund error: {str(stripe_error)}")
                        # Continue with cancellation even if Stripe refund fails

                # Update escrow status
                escrow.refunded_amount = escrow.amount
                escrow.status = 'refunded'
                escrow.refunded_at = datetime.utcnow()
                if escrow.admin_notes:
                    escrow.admin_notes += f"\nGig cancelled: {cancellation_reason}"
                else:
                    escrow.admin_notes = f"Gig cancelled: {cancellation_reason}"

                # Update client wallet
                client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
                if client_wallet:
                    client_wallet.held_balance -= remaining_amount
                    # For non-Stripe payments, add to balance
                    if escrow.payment_gateway != 'stripe':
                        client_wallet.balance += remaining_amount

                # Record payment history
                payment_history = PaymentHistory(
                    user_id=gig.client_id,
                    type='refund',
                    amount=remaining_amount,
                    balance_before=client_wallet.balance if client_wallet else 0,
                    balance_after=client_wallet.balance if client_wallet else 0,
                    description=f"Refund for cancelled gig: {gig.title}",
                    reference_number=stripe_refund_id or escrow.payment_reference,
                    payment_gateway=escrow.payment_gateway,
                    status='completed'
                )
                db.session.add(payment_history)

                refund_processed = True
                refund_amount = remaining_amount

        # Reject all pending applications
        pending_applications = Application.query.filter_by(
            gig_id=gig_id,
            status='pending'
        ).all()

        for app in pending_applications:
            app.status = 'rejected'
            # Notify applicants
            notification = Notification(
                user_id=app.freelancer_id,
                notification_type='application',
                title='Gig Cancelled',
                message=f'The gig "{gig.title}" has been cancelled by the client.',
                link=f'/gig/{gig_id}',
                related_id=gig_id
            )
            db.session.add(notification)

        # Notify assigned freelancer if any
        if gig.freelancer_id and old_status in ['in_progress', 'pending_review']:
            freelancer_notification = Notification(
                user_id=gig.freelancer_id,
                notification_type='payment',
                title='Gig Cancelled',
                message=f'The client has cancelled the gig "{gig.title}". Reason: {cancellation_reason}',
                link=f'/gig/{gig_id}',
                related_id=gig_id
            )
            db.session.add(freelancer_notification)

        db.session.commit()

        response_data = {
            'message': 'Gig cancelled successfully',
            'gig': {
                'id': gig.id,
                'status': gig.status,
                'cancellation_reason': cancellation_reason
            }
        }

        if refund_processed:
            response_data['refund'] = {
                'processed': True,
                'amount': refund_amount,
                'method': escrow.payment_gateway if escrow else None
            }

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Cancel gig error: {str(e)}")
        return jsonify({'error': 'Failed to cancel gig'}), 500

@app.route('/api/gigs/<int:gig_id>/report', methods=['POST'])
@api_rate_limit(requests_per_minute=10)
def report_gig(gig_id):
    """User reports a gig for inappropriate or haram content"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json or {}
        user_id = session['user_id']

        # Validate gig exists
        gig = Gig.query.get_or_404(gig_id)

        # Don't allow reporting own gigs
        if gig.client_id == user_id:
            return jsonify({'error': 'You cannot report your own gig'}), 400

        # Check if user already reported this gig
        existing_report = GigReport.query.filter_by(
            gig_id=gig_id,
            reporter_id=user_id
        ).first()

        if existing_report:
            return jsonify({'error': 'You have already reported this gig'}), 400

        # Validate reason
        reason = data.get('reason', '').strip()
        valid_reasons = ['haram_content', 'inappropriate', 'spam', 'fraud', 'other']
        if reason not in valid_reasons:
            return jsonify({'error': 'Invalid report reason'}), 400

        description = sanitize_input(data.get('description', ''), max_length=1000)

        # Create report
        report = GigReport(
            gig_id=gig_id,
            reporter_id=user_id,
            reason=reason,
            description=description,
            status='pending'
        )
        db.session.add(report)

        # Increment report count on gig
        gig.report_count = (gig.report_count or 0) + 1

        # Auto-block if reports reach threshold (e.g., 3 reports)
        AUTO_BLOCK_THRESHOLD = 3
        if gig.report_count >= AUTO_BLOCK_THRESHOLD and gig.status != 'blocked':
            gig.status = 'blocked'
            gig.blocked_at = datetime.utcnow()
            gig.block_reason = f'Automatically blocked after receiving {gig.report_count} user reports'

            # Notify gig owner
            owner_notification = Notification(
                user_id=gig.client_id,
                notification_type='admin',
                title='Gig Blocked Due to Reports',
                message=f'Your gig "{gig.title}" has been temporarily blocked due to multiple user reports. An admin will review it soon.',
                link=f'/gig/{gig_id}',
                related_id=gig_id
            )
            db.session.add(owner_notification)

            # Log security event
            from security_logger import log_security_event
            log_security_event(
                event_category='content_moderation',
                event_type='auto_block_gig',
                severity='medium',
                user_id=user_id,
                action='auto_block',
                resource_type='gig',
                resource_id=gig_id,
                status='success',
                details={
                    'gig_id': gig_id,
                    'report_count': gig.report_count,
                    'threshold': AUTO_BLOCK_THRESHOLD
                }
            )

        db.session.commit()

        return jsonify({
            'message': 'Report submitted successfully',
            'report_id': report.id,
            'auto_blocked': gig.status == 'blocked'
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Report gig error: {str(e)}")
        return jsonify({'error': 'Failed to submit report'}), 500

# ============================================================================
# END GIG WORKFLOW
# ============================================================================

# ============================================================================
# ESCROW ENDPOINTS
# ============================================================================

@app.route('/api/escrow/create', methods=['POST'])
def create_escrow():
    """Create an escrow when client funds a gig"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        gig_id = data.get('gig_id')
        amount = float(data.get('amount', 0))
        
        if not gig_id:
            return jsonify({'error': 'Invalid gig_id'}), 400
        
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        
        # Only client can create escrow
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can fund the escrow'}), 403
        
        # Gig must have an assigned freelancer
        if not gig.freelancer_id:
            return jsonify({'error': 'Gig must have an assigned freelancer'}), 400
        
        # If no amount provided, use the agreed amount from the accepted application
        if amount <= 0:
            if gig.agreed_amount and gig.agreed_amount > 0:
                amount = gig.agreed_amount
            elif gig.budget_min and gig.budget_min > 0:
                amount = gig.budget_min
            else:
                return jsonify({'error': 'No valid amount found for escrow. Please specify an amount.'}), 400
        
        # Check if escrow already exists
        existing = Escrow.query.filter_by(gig_id=gig_id).first()
        if existing and existing.status in ['funded', 'released']:
            return jsonify({'error': 'Escrow already exists for this gig'}), 400
        
        # Calculate platform fee (tiered commission)
        platform_fee = calculate_commission(amount)
        net_amount = amount - platform_fee
        
        # Create or update escrow
        if existing:
            escrow = existing
            escrow.amount = amount
            escrow.platform_fee = platform_fee
            escrow.net_amount = net_amount
            escrow.status = 'funded'
            escrow.funded_at = datetime.utcnow()
        else:
            escrow = Escrow(
                escrow_number=generate_escrow_number(),
                gig_id=gig_id,
                client_id=user_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=platform_fee,
                net_amount=net_amount,
                status='funded',
                funded_at=datetime.utcnow(),
                payment_reference=f"ESC-{uuid.uuid4().hex[:8].upper()}"
            )
            db.session.add(escrow)
        
        # Update client wallet (deduct held_balance)
        client_wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not client_wallet:
            client_wallet = Wallet(user_id=user_id)
            db.session.add(client_wallet)
        client_wallet.held_balance += amount
        
        # Create receipt for escrow funding
        db.session.flush()  # Get escrow ID
        receipt = create_escrow_receipt(escrow, gig, 'direct')
        
        db.session.commit()
        
        return jsonify({
            'message': 'Escrow funded successfully',
            'escrow': escrow.to_dict(),
            'receipt_number': receipt.receipt_number
        }), 201
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Create escrow error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to create escrow', 'details': str(e) if app.debug else None}), 500

@app.route('/api/escrow/<int:gig_id>', methods=['GET'])
def get_escrow(gig_id):
    """Get escrow status for a gig"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        
        # Only client or freelancer can view escrow
        if gig.client_id != user_id and gig.freelancer_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        
        if not escrow:
            return jsonify({
                'escrow': None,
                'message': 'No escrow found for this gig'
            }), 200
        
        return jsonify({
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get escrow error: {str(e)}")
        return jsonify({'error': 'Failed to get escrow'}), 500

@app.route('/api/escrow/<int:gig_id>/release', methods=['POST'])
def release_escrow(gig_id):
    """Release escrow funds to freelancer (client action after work approval)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can release escrow
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can release escrow'}), 403

        # Check if work is completed
        if gig.status != 'completed':
            return jsonify({'error': 'Work must be marked as completed by the freelancer before releasing payment'}), 400

        escrow = Escrow.query.filter_by(gig_id=gig_id).first()

        if not escrow:
            return jsonify({'error': 'No escrow found'}), 404

        if escrow.status != 'funded':
            return jsonify({'error': f'Escrow cannot be released (status: {escrow.status})'}), 400

        # Check if freelancer has submitted their invoice
        invoice = Invoice.query.filter_by(gig_id=gig_id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found. Freelancer must complete work first.'}), 400

        if not invoice.invoice_submitted:
            return jsonify({'error': 'Freelancer must submit their invoice before payment can be released'}), 400

        # Release escrow
        escrow.status = 'released'
        escrow.released_at = datetime.utcnow()

        # Calculate SOCSO contribution (1.25% of net amount after platform commission)
        # Per Gig Workers Bill 2025: SOCSO is calculated on net earnings
        freelancer = User.query.get(gig.freelancer_id)
        socso_amount = 0.0

        if freelancer and freelancer.user_type in ['freelancer', 'both']:
            socso_amount = calculate_socso(escrow.net_amount)

        # Final amount to freelancer after SOCSO deduction
        final_payout_amount = round(escrow.net_amount - socso_amount, 2)

        # Create or update transaction record to track commission and SOCSO
        transaction = Transaction.query.filter_by(gig_id=gig_id).first()
        if not transaction:
            transaction = Transaction(
                gig_id=gig_id,
                freelancer_id=gig.freelancer_id,
                client_id=gig.client_id,
                amount=escrow.amount,
                commission=escrow.platform_fee,
                net_amount=escrow.net_amount,
                socso_amount=socso_amount,
                payment_method='escrow',
                status='completed'
            )
            db.session.add(transaction)
        else:
            # Update existing transaction
            transaction.commission = escrow.platform_fee
            transaction.socso_amount = socso_amount
            transaction.status = 'completed'

        db.session.flush()  # Get transaction ID

        # Create SOCSO contribution record
        if socso_amount > 0:
            create_socso_contribution(
                freelancer_id=gig.freelancer_id,
                gross_amount=escrow.amount,
                platform_commission=escrow.platform_fee,
                net_earnings=escrow.net_amount,
                contribution_type='escrow_release',
                gig_id=gig_id,
                transaction_id=transaction.id
            )

        # Update wallets
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        freelancer_wallet = Wallet.query.filter_by(user_id=gig.freelancer_id).first()

        if client_wallet:
            client_wallet.held_balance -= escrow.amount
            client_wallet.total_spent += escrow.amount

        if not freelancer_wallet:
            freelancer_wallet = Wallet(user_id=gig.freelancer_id)
            db.session.add(freelancer_wallet)

        # Credit freelancer wallet with final amount after SOCSO deduction
        freelancer_wallet.balance += final_payout_amount
        freelancer_wallet.total_earned += final_payout_amount

        # Record payment history with SOCSO details
        payment_history = PaymentHistory(
            user_id=gig.freelancer_id,
            type='release',
            amount=final_payout_amount,
            socso_amount=socso_amount,
            balance_before=freelancer_wallet.balance - final_payout_amount,
            balance_after=freelancer_wallet.balance,
            description=f"Escrow released for gig: {gig.title} (SOCSO: MYR {socso_amount:.2f})",
            reference_number=escrow.payment_reference
        )
        db.session.add(payment_history)

        # Mark invoice as paid and link to transaction
        db.session.flush()  # Ensure transaction has an ID
        # Invoice already fetched above for validation
        if invoice:
            if invoice.status != 'paid':
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcnow()
                invoice.payment_method = 'escrow'
                invoice.payment_reference = escrow.payment_reference
            # Link invoice to transaction if not already linked
            if not invoice.transaction_id:
                invoice.transaction_id = transaction.id

        # Create payment receipts for both client and freelancer
        # Check if receipts already exist for this payment
        existing_client_receipt = Receipt.query.filter_by(
            gig_id=gig_id,
            receipt_type='payment',
            user_id=gig.client_id
        ).first()

        client_receipt = None
        freelancer_receipt = None

        if not existing_client_receipt:
            # Create receipt for client (payer)
            client_receipt = Receipt(
                receipt_number=generate_receipt_number('payment'),
                receipt_type='payment',
                user_id=gig.client_id,
                gig_id=gig_id,
                escrow_id=escrow.id,
                invoice_id=invoice.id if invoice else None,
                amount=escrow.amount,
                platform_fee=escrow.platform_fee,
                total_amount=escrow.amount,
                payment_method='escrow',
                payment_reference=escrow.payment_reference,
                description=f"Payment receipt for gig: {gig.title}"
            )
            db.session.add(client_receipt)
            db.session.flush()  # Get receipt ID

            # Create receipt for freelancer (recipient)
            freelancer_receipt = Receipt(
                receipt_number=generate_receipt_number('payment'),
                receipt_type='payment',
                user_id=gig.freelancer_id,
                gig_id=gig_id,
                escrow_id=escrow.id,
                invoice_id=invoice.id if invoice else None,
                amount=escrow.net_amount,  # Net amount after platform fee
                platform_fee=escrow.platform_fee,
                total_amount=escrow.amount,
                payment_method='escrow',
                payment_reference=escrow.payment_reference,
                description=f"Payment received for gig: {gig.title}"
            )
            db.session.add(freelancer_receipt)
            db.session.flush()  # Get receipt ID

            # Create notification for client about the receipt
            client_notification = Notification(
                user_id=gig.client_id,
                notification_type='payment',
                title='Payment Receipt',
                message=f'Payment of MYR {escrow.amount:.2f} processed for gig: {gig.title}. Receipt #{client_receipt.receipt_number}',
                link=f'/receipt/{client_receipt.id}',
                related_id=client_receipt.id
            )
            db.session.add(client_notification)

            # Create notification for worker about payment received
            worker_notification = Notification(
                user_id=gig.freelancer_id,
                notification_type='payment',
                title='Payment Received',
                message=f'Payment of MYR {escrow.net_amount:.2f} received for gig: {gig.title}. Receipt #{freelancer_receipt.receipt_number}',
                link=f'/receipt/{freelancer_receipt.id}',
                related_id=freelancer_receipt.id
            )
            db.session.add(worker_notification)

        db.session.commit()

        # Send email notifications to both parties about payment release
        client = User.query.get(gig.client_id)

        # Email to freelancer about payment received
        if freelancer:
            try:
                subject = "Payment Received!"
                message = f"Great news! You've received payment for '{gig.title}'. MYR {final_payout_amount:.2f} has been credited to your wallet."

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #27ae60; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .amount {{ font-size: 24px; color: #27ae60; font-weight: bold; margin: 10px 0; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>💰 Payment Received!</h2>
                        </div>
                        <div class="content">
                            <p>Hi {freelancer.full_name or freelancer.username},</p>
                            <p>Congratulations! Payment for <strong>"{gig.title}"</strong> has been successfully released.</p>
                            <div class="amount">MYR {final_payout_amount:.2f}</div>
                            <p><strong>Breakdown:</strong></p>
                            <ul>
                                <li>Gross Amount: MYR {escrow.amount:.2f}</li>
                                <li>Platform Fee: MYR {escrow.platform_fee:.2f}</li>
                                {f'<li>SOCSO Contribution: MYR {socso_amount:.2f}</li>' if socso_amount > 0 else ''}
                                <li><strong>Net Payment: MYR {final_payout_amount:.2f}</strong></li>
                            </ul>
                            {f'<p><strong>Receipt Number:</strong> {freelancer_receipt.receipt_number if freelancer_receipt else existing_client_receipt.receipt_number}</p>' if freelancer_receipt or existing_client_receipt else ''}
                            <p>The amount has been credited to your GigHala wallet. You can withdraw it anytime.</p>
                            <p>Thank you for your excellent work!</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Payment Received!

Hi {freelancer.full_name or freelancer.username},

Congratulations! Payment for "{gig.title}" has been successfully released.

Amount: MYR {final_payout_amount:.2f}

Breakdown:
- Gross Amount: MYR {escrow.amount:.2f}
- Platform Fee: MYR {escrow.platform_fee:.2f}
{f'- SOCSO Contribution: MYR {socso_amount:.2f}' if socso_amount > 0 else ''}
- Net Payment: MYR {final_payout_amount:.2f}

{f'Receipt Number: {freelancer_receipt.receipt_number if freelancer_receipt else existing_client_receipt.receipt_number}' if freelancer_receipt or existing_client_receipt else ''}

The amount has been credited to your GigHala wallet.

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=freelancer.email,
                    to_name=freelancer.full_name or freelancer.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent payment received email to freelancer {freelancer.id}")

            except Exception as e:
                app.logger.error(f"Failed to send payment received email to freelancer: {str(e)}")

        # Email to client about payment completion
        if client:
            try:
                subject = "Payment Completed"
                message = f"Payment for '{gig.title}' has been successfully processed. Thank you for using GigHala!"

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .amount {{ font-size: 24px; color: #3498db; font-weight: bold; margin: 10px 0; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>✅ Payment Completed</h2>
                        </div>
                        <div class="content">
                            <p>Hi {client.full_name or client.username},</p>
                            <p>Payment for <strong>"{gig.title}"</strong> has been successfully released to {freelancer.full_name or freelancer.username}.</p>
                            <div class="amount">MYR {escrow.amount:.2f}</div>
                            {f'<p><strong>Receipt Number:</strong> {client_receipt.receipt_number if client_receipt else existing_client_receipt.receipt_number}</p>' if client_receipt or existing_client_receipt else ''}
                            <p>Thank you for using GigHala! We hope you had a great experience.</p>
                            <p>Feel free to post more gigs or leave a review for the freelancer.</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
Payment Completed

Hi {client.full_name or client.username},

Payment for "{gig.title}" has been successfully released to {freelancer.full_name or freelancer.username}.

Amount: MYR {escrow.amount:.2f}

{f'Receipt Number: {client_receipt.receipt_number if client_receipt else existing_client_receipt.receipt_number}' if client_receipt or existing_client_receipt else ''}

Thank you for using GigHala!

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=client.email,
                    to_name=client.full_name or client.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent payment completed email to client {client.id}")

            except Exception as e:
                app.logger.error(f"Failed to send payment completed email to client: {str(e)}")

        # Send SMS notifications if users have verified phone numbers (Phase 1)
        # Notify freelancer about payment received
        if freelancer and freelancer.phone and freelancer.phone_verified:
            sms_message = f"GigHala: Payment received! MYR {final_payout_amount:.2f} for '{gig.title}'. Check your dashboard for details."
            send_transaction_sms_notification(freelancer.phone, sms_message)

        # Notify client about payment completion
        if client and client.phone and client.phone_verified:
            sms_message = f"GigHala: Payment of MYR {escrow.amount:.2f} processed for '{gig.title}'. Thank you!"
            send_transaction_sms_notification(client.phone, sms_message)

        return jsonify({
            'message': 'Payment completed! Invoice marked as paid and receipt created.',
            'escrow': escrow.to_dict(),
            'invoice': {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'status': invoice.status
            } if invoice else None,
            'receipt': {
                'id': client_receipt.id if client_receipt else existing_client_receipt.id,
                'receipt_number': client_receipt.receipt_number if client_receipt else existing_client_receipt.receipt_number
            } if client_receipt or existing_client_receipt else None
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Release escrow error: {str(e)}")
        return jsonify({'error': 'Failed to release escrow'}), 500

@app.route('/api/escrow/<int:gig_id>/refund', methods=['POST'])
def refund_escrow(gig_id):
    """Refund escrow funds to client"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json or {}
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        user = User.query.get(user_id)

        # Only client or admin can refund
        if gig.client_id != user_id and not user.is_admin:
            return jsonify({'error': 'Only the client or admin can refund escrow'}), 403

        escrow = Escrow.query.filter_by(gig_id=gig_id).first()

        if not escrow:
            return jsonify({'error': 'No escrow found'}), 404

        if escrow.status not in ['funded', 'disputed', 'partial_refund']:
            return jsonify({'error': f'Escrow cannot be refunded (status: {escrow.status})'}), 400

        # Get refund amount (support partial refunds)
        refund_amount = float(data.get('refund_amount', 0))
        if refund_amount <= 0:
            refund_amount = escrow.amount - (escrow.refunded_amount or 0.0)  # Full refund of remaining

        # Validate refund amount
        remaining_amount = escrow.amount - (escrow.refunded_amount or 0.0)
        if refund_amount > remaining_amount:
            return jsonify({'error': f'Refund amount (RM{refund_amount:.2f}) exceeds remaining balance (RM{remaining_amount:.2f})'}), 400

        is_partial = refund_amount < remaining_amount

        # Process Stripe refund if payment was made via Stripe
        stripe_refund_id = None
        if escrow.payment_gateway == 'stripe' and escrow.payment_reference:
            try:
                if not stripe.api_key:
                    app.logger.error("Stripe not configured for refund")
                    return jsonify({'error': 'Stripe is not configured'}), 500

                # Create refund in Stripe (amount in cents)
                refund = stripe.Refund.create(
                    payment_intent=escrow.payment_reference,
                    amount=int(refund_amount * 100),  # Convert to cents
                    reason='requested_by_customer',
                    metadata={
                        'gig_id': str(gig_id),
                        'escrow_id': str(escrow.id),
                        'reason': data.get('reason', 'Client requested refund'),
                        'is_partial': str(is_partial)
                    }
                )
                stripe_refund_id = refund.id
                app.logger.info(f"Stripe {'partial ' if is_partial else ''}refund created: {stripe_refund_id} for RM{refund_amount:.2f}")

            except stripe.error.InvalidRequestError as e:
                app.logger.error(f"Stripe refund error: {str(e)}")
                return jsonify({'error': f'Stripe refund failed: {str(e)}'}), 400
            except stripe.error.StripeError as e:
                app.logger.error(f"Stripe API error: {str(e)}")
                return jsonify({'error': 'Payment gateway error. Please try again.'}), 500

        # Update escrow with refund tracking
        escrow.refunded_amount = (escrow.refunded_amount or 0.0) + refund_amount

        # Update status based on whether it's full or partial refund
        if is_partial:
            escrow.status = 'partial_refund'
        else:
            escrow.status = 'refunded'
            escrow.refunded_at = datetime.utcnow()

        if escrow.admin_notes:
            escrow.admin_notes += f"\n{data.get('reason', '')}"
        else:
            escrow.admin_notes = data.get('reason', '')

        # Update client wallet
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        if client_wallet:
            client_wallet.held_balance -= refund_amount
            # For Stripe refunds, don't add to balance as money goes back to card
            if escrow.payment_gateway != 'stripe':
                client_wallet.balance += refund_amount

        # Record payment history
        payment_history = PaymentHistory(
            user_id=gig.client_id,
            type='refund',
            amount=refund_amount,
            balance_before=client_wallet.balance if client_wallet else 0,
            balance_after=client_wallet.balance if client_wallet else 0,
            description=f"{'Partial ' if is_partial else ''}Escrow refund for gig: {gig.title}",
            reference_number=stripe_refund_id or escrow.payment_reference,
            payment_gateway=escrow.payment_gateway,
            gateway_response=f"Stripe refund: {stripe_refund_id}" if stripe_refund_id else None
        )
        db.session.add(payment_history)

        # Create notification for client
        notification = Notification(
            user_id=gig.client_id,
            notification_type='payment',
            title='Escrow Refunded',
            message=f'{"Partial " if is_partial else ""}Refund of RM{refund_amount:.2f} processed for gig: {gig.title}',
            link=f'/gig/{gig_id}'
        )
        db.session.add(notification)

        db.session.commit()

        return jsonify({
            'message': f'{"Partial " if is_partial else ""}Escrow refund successful' + (' via Stripe' if stripe_refund_id else ''),
            'escrow': escrow.to_dict(),
            'refund_id': stripe_refund_id,
            'refund_amount': refund_amount,
            'is_partial': is_partial
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Refund escrow error: {str(e)}")
        return jsonify({'error': 'Failed to refund escrow'}), 500

@app.route('/api/escrow/<int:gig_id>/dispute', methods=['POST'])
def dispute_escrow(gig_id):
    """Raise a dispute on escrow"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json or {}
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        
        # Only client or freelancer can dispute
        if gig.client_id != user_id and gig.freelancer_id != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        
        if not escrow:
            return jsonify({'error': 'No escrow found'}), 404
        
        if escrow.status != 'funded':
            return jsonify({'error': f'Cannot dispute escrow (status: {escrow.status})'}), 400
        
        reason = data.get('reason', '')
        if not reason:
            return jsonify({'error': 'Dispute reason is required'}), 400
        
        escrow.status = 'disputed'
        escrow.dispute_reason = reason
        
        db.session.commit()
        
        return jsonify({
            'message': 'Dispute raised successfully. Admin will review.',
            'escrow': escrow.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Dispute escrow error: {str(e)}")
        return jsonify({'error': 'Failed to raise dispute'}), 500

# ============================================================================
# PAYHALAL ESCROW INTEGRATION
# ============================================================================

@app.route('/api/escrow/<int:gig_id>/pay', methods=['POST'])
def initiate_escrow_payment(gig_id):
    """Initiate PayHalal payment to fund an escrow"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from payhalal import get_payhalal_client, calculate_payhalal_processing_fee
        
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Only client can initiate payment
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can fund the escrow'}), 403
        
        # Gig must have an assigned freelancer
        if not gig.freelancer_id:
            return jsonify({'error': 'Gig must have an assigned freelancer before funding'}), 400
        
        # Check if escrow already funded
        existing = Escrow.query.filter_by(gig_id=gig_id).first()
        if existing and existing.status in ['funded', 'released']:
            return jsonify({'error': 'Escrow already funded for this gig'}), 400
        
        # Get amount from request or use gig budget_max
        data = request.json or {}
        amount = float(data.get('amount', gig.budget_max or 0))
        
        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        # Calculate fees
        platform_fee = calculate_commission(amount)
        processing_fee = calculate_payhalal_processing_fee(amount)
        total_amount = amount + processing_fee
        net_amount = amount - platform_fee
        
        # Generate unique order ID
        order_id = f"ESC-{gig_id}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create or update escrow as pending
        if existing:
            escrow = existing
            escrow.amount = amount
            escrow.platform_fee = platform_fee
            escrow.net_amount = net_amount
            escrow.status = 'pending'
            escrow.payment_reference = order_id
        else:
            escrow = Escrow(
                escrow_number=generate_escrow_number(),
                gig_id=gig_id,
                client_id=user_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=platform_fee,
                net_amount=net_amount,
                status='pending',
                payment_reference=order_id
            )
            db.session.add(escrow)
        
        db.session.commit()
        
        # Get PayHalal client
        client = get_payhalal_client()
        
        if not client.is_available():
            # PayHalal not configured - return manual payment instructions
            return jsonify({
                'success': True,
                'payment_method': 'manual',
                'escrow': escrow.to_dict(),
                'message': 'PayHalal is not configured. Please use manual bank transfer.',
                'manual_instructions': {
                    'bank_name': 'Maybank',
                    'account_number': '512345678901',
                    'account_name': 'GigHala Sdn Bhd',
                    'reference': order_id,
                    'amount': total_amount
                }
            }), 200
        
        # Build callback URLs - use request.host_url for absolute URLs
        base_url = request.host_url.rstrip('/')
        if not base_url:
            # Fallback to REPLIT_DEV_DOMAIN if request.host_url is not available
            domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
            if domain:
                base_url = f"https://{domain}" if not domain.startswith('http') else domain
            else:
                # Last resort: use REPLIT_DOMAINS
                domains = os.environ.get('REPLIT_DOMAINS', '')
                if domains:
                    first_domain = domains.split(',')[0].strip()
                    base_url = f"https://{first_domain}"
        
        if not base_url:
            return jsonify({
                'success': False,
                'error': 'Unable to determine application URL for payment callback'
            }), 500
        
        return_url = f"{base_url}/escrow?payment=success&gig_id={gig_id}"
        callback_url = f"{base_url}/api/payhalal/escrow-webhook"
        
        # Create PayHalal payment
        result = client.create_payment(
            amount=total_amount,
            order_id=order_id,
            description=f"Escrow payment for gig: {gig.title[:50]}",
            customer_email=user.email,
            customer_name=user.full_name or user.username,
            return_url=return_url,
            callback_url=callback_url,
            customer_phone=user.phone
        )
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'payment_method': 'payhalal',
                'payment_url': result.get('payment_url'),
                'payment_id': result.get('payment_id'),
                'order_id': order_id,
                'escrow': escrow.to_dict(),
                'fee_breakdown': {
                    'gig_amount': amount,
                    'platform_fee': platform_fee,
                    'processing_fee': processing_fee,
                    'total_charge': total_amount,
                    'freelancer_receives': net_amount
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to create payment'),
                'escrow': escrow.to_dict()
            }), 400
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Initiate escrow payment error: {str(e)}")
        return jsonify({'error': 'Failed to initiate payment'}), 500

@app.route('/api/escrow/<int:gig_id>/test-fund', methods=['POST'])
def test_fund_escrow(gig_id):
    """TEST ONLY: Simulate successful escrow funding without payment gateway"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can fund escrow
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can fund the escrow'}), 403

        # Gig must have an assigned freelancer
        if not gig.freelancer_id:
            return jsonify({'error': 'Gig must have an assigned freelancer'}), 400

        # Get amount from request or use gig budget_max
        data = request.json or {}
        amount = float(data.get('amount', gig.budget_max or 1500))

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        # Check if escrow already exists
        existing = Escrow.query.filter_by(gig_id=gig_id).first()
        if existing and existing.status in ['funded', 'released']:
            return jsonify({'error': 'Escrow already funded for this gig'}), 400

        # Calculate platform fee
        platform_fee = calculate_commission(amount)
        net_amount = amount - platform_fee

        # Create or update escrow
        if existing:
            escrow = existing
            escrow.amount = amount
            escrow.platform_fee = platform_fee
            escrow.net_amount = net_amount
            escrow.status = 'funded'
            escrow.funded_at = datetime.utcnow()
            escrow.payment_reference = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        else:
            escrow = Escrow(
                escrow_number=generate_escrow_number(),
                gig_id=gig_id,
                client_id=user_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=platform_fee,
                net_amount=net_amount,
                status='funded',
                funded_at=datetime.utcnow(),
                payment_reference=f"TEST-{uuid.uuid4().hex[:8].upper()}"
            )
            db.session.add(escrow)

        # Update client wallet (deduct held_balance)
        client_wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not client_wallet:
            client_wallet = Wallet(user_id=user_id)
            db.session.add(client_wallet)
        client_wallet.held_balance += amount

        # Create receipt for escrow funding
        db.session.flush()  # Get escrow ID
        receipt = create_escrow_receipt(escrow, gig, 'test')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '✓ TEST: Escrow funded successfully (no real payment)',
            'escrow': escrow.to_dict(),
            'receipt_number': receipt.receipt_number
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Test fund escrow error: {str(e)}")
        return jsonify({'error': 'Failed to fund escrow', 'details': str(e)}), 500


@app.route('/api/payhalal/escrow-webhook', methods=['POST'])
@csrf.exempt
def payhalal_escrow_webhook():
    """Handle PayHalal payment webhook for escrow funding"""
    try:
        from payhalal import get_payhalal_client

        data = request.json or {}
        signature = request.headers.get('X-PayHalal-Signature', '')

        # SECURITY FIX: Mandatory webhook signature verification
        if not signature:
            app.logger.warning("Missing PayHalal webhook signature")
            return jsonify({'error': 'Missing signature'}), 401

        client = get_payhalal_client()

        # Always verify webhook signature
        if not client.verify_webhook_signature(data, signature):
            app.logger.warning("Invalid PayHalal webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        
        order_id = data.get('order_id')
        payment_status = data.get('status')
        payment_id = data.get('payment_id')
        
        if not order_id:
            return jsonify({'error': 'Missing order_id'}), 400
        
        # Find escrow by payment reference
        escrow = Escrow.query.filter_by(payment_reference=order_id).first()
        
        if not escrow:
            app.logger.warning(f"Escrow not found for order_id: {order_id}")
            return jsonify({'error': 'Escrow not found'}), 404
        
        if payment_status == 'paid' or payment_status == 'success':
            # Idempotency: Skip if already funded
            if escrow.status == 'funded':
                app.logger.info(f"Escrow {escrow.id} already funded, skipping duplicate webhook")
                return jsonify({
                    'success': True,
                    'message': 'Escrow already funded (duplicate webhook)'
                }), 200
            
            # Mark escrow as funded
            escrow.status = 'funded'
            escrow.funded_at = datetime.utcnow()
            
            # Update client wallet (add to held_balance)
            client_wallet = Wallet.query.filter_by(user_id=escrow.client_id).first()
            if not client_wallet:
                client_wallet = Wallet(user_id=escrow.client_id)
                db.session.add(client_wallet)
            
            client_wallet.held_balance += escrow.amount
            
            # Record payment history
            payment_history = PaymentHistory(
                user_id=escrow.client_id,
                type='escrow_fund',
                amount=escrow.amount,
                balance_before=client_wallet.balance,
                balance_after=client_wallet.balance,
                description=f"Escrow funded via PayHalal for gig ID: {escrow.gig_id}",
                reference_number=order_id
            )
            db.session.add(payment_history)
            
            # Create receipt for escrow funding
            gig = Gig.query.get(escrow.gig_id)
            if gig:
                receipt = create_escrow_receipt(escrow, gig, 'payhalal')
            
            db.session.commit()
            
            app.logger.info(f"Escrow {escrow.id} funded successfully via PayHalal")
            
            return jsonify({
                'success': True,
                'message': 'Escrow funded successfully'
            }), 200
            
        elif payment_status == 'failed' or payment_status == 'cancelled':
            escrow.status = 'cancelled'
            escrow.admin_notes = f"Payment {payment_status}: {data.get('error', 'Unknown error')}"
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Payment {payment_status}'
            }), 200
        
        return jsonify({'success': True, 'message': 'Webhook received'}), 200
        
    except Exception as e:
        app.logger.error(f"PayHalal escrow webhook error: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500


@app.route('/api/escrow/<int:gig_id>/confirm-manual', methods=['POST'])
def confirm_manual_escrow_payment(gig_id):
    """Confirm manual bank transfer for escrow (admin only or with receipt upload)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        gig = Gig.query.get_or_404(gig_id)
        
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        
        if not escrow:
            return jsonify({'error': 'No pending escrow found'}), 404
        
        if escrow.status != 'pending':
            return jsonify({'error': f'Escrow is not pending (status: {escrow.status})'}), 400
        
        # Only client or admin can confirm
        if gig.client_id != user_id and not user.is_admin:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.json or {}
        transfer_reference = data.get('transfer_reference', '')
        
        if user.is_admin:
            # Admin can directly confirm
            escrow.status = 'funded'
            escrow.funded_at = datetime.utcnow()
            escrow.admin_notes = f"Confirmed by admin. Transfer ref: {transfer_reference}"
            
            # Update wallet
            client_wallet = Wallet.query.filter_by(user_id=escrow.client_id).first()
            if not client_wallet:
                client_wallet = Wallet(user_id=escrow.client_id)
                db.session.add(client_wallet)
            
            client_wallet.held_balance += escrow.amount
            
            # Create receipt for escrow funding
            receipt = create_escrow_receipt(escrow, gig, 'bank_transfer')
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Escrow confirmed and funded',
                'escrow': escrow.to_dict(),
                'receipt_number': receipt.receipt_number
            }), 200
        else:
            # Client submits transfer reference for admin review
            escrow.admin_notes = f"Client submitted transfer ref: {transfer_reference}. Awaiting admin confirmation."
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Transfer reference submitted. Admin will verify and confirm your payment.',
                'escrow': escrow.to_dict()
            }), 200
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Confirm manual escrow error: {str(e)}")
        return jsonify({'error': 'Failed to confirm payment'}), 500


@app.route('/api/escrow/my-escrows', methods=['GET'])
def get_my_escrows():
    """Get all escrows for the current user (as client or freelancer)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        
        # Get escrows where user is client or freelancer
        escrows = Escrow.query.filter(
            (Escrow.client_id == user_id) | (Escrow.freelancer_id == user_id)
        ).order_by(Escrow.created_at.desc()).all()
        
        result = []
        for escrow in escrows:
            gig = Gig.query.get(escrow.gig_id)
            client = User.query.get(escrow.client_id)
            freelancer = User.query.get(escrow.freelancer_id)
            
            result.append({
                **escrow.to_dict(),
                'gig_title': gig.title if gig else 'Unknown Gig',
                'client_name': client.full_name or client.username if client else 'Unknown',
                'freelancer_name': freelancer.full_name or freelancer.username if freelancer else 'Unknown',
                'is_client': escrow.client_id == user_id,
                'is_freelancer': escrow.freelancer_id == user_id
            })
        
        return jsonify({
            'success': True,
            'escrows': result
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get my escrows error: {str(e)}")
        return jsonify({'error': 'Failed to get escrows'}), 500


@app.route('/escrow')
@login_required
def escrow_page():
    """Escrow management page"""
    user = User.query.get(session['user_id'])
    return render_template('escrow.html', user=user, active_page='escrow')


# ============================================================================
# END ESCROW ENDPOINTS
# ============================================================================

# ============================================================================
# STRIPE CHECKOUT FOR ESCROW
# ============================================================================

@app.route('/api/stripe/create-checkout-session', methods=['POST'])
@login_required
def create_stripe_checkout_session():
    """Create a Stripe Checkout session for escrow funding"""
    try:
        # Initialize Stripe with the correct mode keys
        init_stripe()

        if not stripe.api_key:
            return jsonify({'error': 'Stripe is not configured'}), 500
        
        data = request.json or {}
        gig_id = data.get('gig_id')
        
        if not gig_id:
            return jsonify({'error': 'gig_id is required'}), 400
        
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        # Only client can fund escrow
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can fund the escrow'}), 403
        
        # Gig must have an assigned freelancer
        if not gig.freelancer_id:
            return jsonify({'error': 'Gig must have an assigned freelancer before funding'}), 400
        
        # Check if escrow already funded
        existing = Escrow.query.filter_by(gig_id=gig_id).first()
        if existing and existing.status in ['funded', 'released']:
            return jsonify({'error': 'Escrow already funded for this gig'}), 400
        
        # Get amount from request or use gig budget_max
        amount = float(data.get('amount', gig.budget_max or 0))
        
        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        # Calculate fees
        platform_fee = calculate_commission(amount)
        processing_fee = (amount * PROCESSING_FEE_PERCENT) + PROCESSING_FEE_FIXED
        total_amount = amount + processing_fee
        net_amount = amount - platform_fee
        
        # Generate unique order ID
        order_id = f"ESC-{gig_id}-{uuid.uuid4().hex[:8].upper()}"

        # Create or update escrow as pending
        if existing:
            escrow = existing
            escrow.amount = amount
            escrow.platform_fee = platform_fee
            escrow.net_amount = net_amount
            escrow.status = 'pending'
            escrow.payment_reference = order_id
            escrow.payment_gateway = 'stripe'
        else:
            escrow = Escrow(
                escrow_number=generate_escrow_number(),
                gig_id=gig_id,
                client_id=user_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=platform_fee,
                net_amount=net_amount,
                status='pending',
                payment_reference=order_id,
                payment_gateway='stripe'
            )
            db.session.add(escrow)

        db.session.commit()

        # Build callback URLs
        base_url = request.host_url.rstrip('/')
        if not base_url or 'localhost' in base_url:
            domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
            if domain:
                base_url = f"https://{domain}"

        success_url = f"{base_url}/api/stripe/checkout-success?session_id={{CHECKOUT_SESSION_ID}}&gig_id={gig_id}"
        cancel_url = f"{base_url}/escrow?payment=cancelled&gig_id={gig_id}"

        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'myr',
                    'product_data': {
                        'name': f'Escrow for: {gig.title[:50]}',
                        'description': f'Gig Amount: RM{amount:.2f} | Platform Fee: RM{platform_fee:.2f} | Processing Fee: RM{processing_fee:.2f} | Total: RM{total_amount:.2f} | Worker Receives: RM{net_amount:.2f}'
                    },
                    'unit_amount': int(total_amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=user.email,
            metadata={
                'gig_id': str(gig_id),
                'escrow_id': str(escrow.id),
                'order_id': order_id,
                'amount': str(amount),
                'platform_fee': str(platform_fee),
                'net_amount': str(net_amount)
            }
        )
        
        # Update escrow with Stripe session ID
        escrow.payment_reference = checkout_session.id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id,
            'fee_breakdown': {
                'gig_amount': amount,
                'platform_fee': platform_fee,
                'processing_fee': processing_fee,
                'total_charge': total_amount,
                'freelancer_receives': net_amount
            }
        }), 200
        
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': f'Payment error: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Create checkout session error: {str(e)}")
        return jsonify({'error': 'Failed to create payment session'}), 500


@app.route('/api/stripe/checkout-success')
def stripe_checkout_success():
    """Handle successful Stripe checkout redirect"""
    session_id = request.args.get('session_id')
    gig_id = request.args.get('gig_id')

    if not session_id:
        flash('Payment session not found', 'error')
        return redirect('/escrow')

    try:
        # Initialize Stripe with the correct mode keys
        init_stripe()

        # Retrieve the session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        if checkout_session.payment_status == 'paid':
            # Find escrow by session ID
            escrow = Escrow.query.filter_by(payment_reference=session_id).first()
            
            if escrow and escrow.status == 'pending':
                # Update escrow to funded
                escrow.status = 'funded'
                escrow.funded_at = datetime.utcnow()
                escrow.payment_reference = checkout_session.payment_intent
                
                # Update client wallet
                client_wallet = Wallet.query.filter_by(user_id=escrow.client_id).first()
                if not client_wallet:
                    client_wallet = Wallet(user_id=escrow.client_id)
                    db.session.add(client_wallet)
                client_wallet.held_balance += escrow.amount
                
                # Create receipt
                gig = Gig.query.get(escrow.gig_id)
                if gig:
                    create_escrow_receipt(escrow, gig, 'stripe')
                
                # Create payment history
                payment_history = PaymentHistory(
                    user_id=escrow.client_id,
                    type='escrow_fund',
                    amount=escrow.amount,
                    balance_before=client_wallet.balance,
                    balance_after=client_wallet.balance,
                    description=f"Escrow funded for gig: {gig.title if gig else 'Unknown'}",
                    reference_number=checkout_session.payment_intent,
                    payment_gateway='stripe'
                )
                db.session.add(payment_history)
                
                # Create notification for freelancer
                notification = Notification(
                    user_id=escrow.freelancer_id,
                    notification_type='payment',
                    title='Escrow Funded',
                    message=f'Client has funded RM{escrow.amount:.2f} for gig: {gig.title if gig else "Unknown"}',
                    link=f'/gig/{escrow.gig_id}'
                )
                db.session.add(notification)
                
                db.session.commit()
                
                flash('Payment successful! Escrow has been funded.', 'success')
            else:
                flash('Payment already processed.', 'info')
        else:
            flash('Payment not completed. Please try again.', 'warning')
            
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe verification error: {str(e)}")
        flash('Could not verify payment. Please check your escrow status.', 'error')
    except Exception as e:
        app.logger.error(f"Checkout success error: {str(e)}")
        flash('Error processing payment. Please contact support.', 'error')
    
    return redirect(f'/escrow?gig_id={gig_id}' if gig_id else '/escrow')


@app.route('/api/stripe/webhook', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    """Handle Stripe webhook events with enhanced logging and error handling"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # SECURITY FIX: Mandatory webhook signature verification
    if not webhook_secret:
        app.logger.error("STRIPE_WEBHOOK_SECRET not configured - webhook rejected")
        return jsonify({'error': 'Webhook verification not configured'}), 500

    if not sig_header:
        app.logger.warning("Missing Stripe-Signature header")
        return jsonify({'error': 'Missing signature'}), 401

    event = None
    webhook_log = None

    try:
        # Always verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )

        # Create webhook log for auditing
        webhook_log = StripeWebhookLog(
            event_id=event['id'],
            event_type=event['type'],
            payload=payload
        )
        db.session.add(webhook_log)
        db.session.commit()

        app.logger.info(f"Stripe webhook received: {event['type']} (ID: {event['id']})")

        # Handle checkout.session.completed event
        if event['type'] == 'checkout.session.completed':
            session_data = event['data']['object']

            # Find escrow by session ID
            escrow = Escrow.query.filter_by(payment_reference=session_data['id']).first()

            if escrow and escrow.status == 'pending':
                try:
                    escrow.status = 'funded'
                    escrow.funded_at = datetime.utcnow()
                    escrow.payment_reference = session_data.get('payment_intent', session_data['id'])

                    # Update client wallet
                    client_wallet = Wallet.query.filter_by(user_id=escrow.client_id).first()
                    if not client_wallet:
                        client_wallet = Wallet(user_id=escrow.client_id)
                        db.session.add(client_wallet)
                    client_wallet.held_balance += escrow.amount

                    # Create receipt
                    gig = Gig.query.get(escrow.gig_id)
                    if gig:
                        create_escrow_receipt(escrow, gig, 'stripe')

                    db.session.commit()
                    app.logger.info(f"Escrow {escrow.id} funded successfully via webhook (amount: RM{escrow.amount})")

                    # Mark webhook as processed
                    webhook_log.processed = True
                    webhook_log.processed_at = datetime.utcnow()
                    db.session.commit()

                except Exception as e:
                    db.session.rollback()
                    error_msg = f"Failed to process escrow funding: {str(e)}"
                    app.logger.error(error_msg)
                    webhook_log.error_message = error_msg
                    db.session.commit()
                    raise
            else:
                if not escrow:
                    app.logger.warning(f"Escrow not found for session {session_data['id']}")
                else:
                    app.logger.info(f"Escrow {escrow.id} already processed (status: {escrow.status})")
                webhook_log.processed = True
                webhook_log.processed_at = datetime.utcnow()
                db.session.commit()

        # Handle payment_intent.payment_failed event
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            error_message = payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')
            app.logger.error(f"Payment failed - Intent: {payment_intent.get('id')}, Error: {error_message}")

            webhook_log.processed = True
            webhook_log.processed_at = datetime.utcnow()
            webhook_log.error_message = f"Payment failed: {error_message}"
            db.session.commit()

        # Handle refund events
        elif event['type'] == 'charge.refunded':
            charge = event['data']['object']
            app.logger.info(f"Charge refunded - ID: {charge.get('id')}, Amount: {charge.get('amount_refunded') / 100}")

            webhook_log.processed = True
            webhook_log.processed_at = datetime.utcnow()
            db.session.commit()

        else:
            # Log other events but mark as processed
            app.logger.info(f"Unhandled Stripe event type: {event['type']}")
            webhook_log.processed = True
            webhook_log.processed_at = datetime.utcnow()
            db.session.commit()

        return jsonify({'status': 'success', 'received': True}), 200

    except ValueError as e:
        error_msg = f"Invalid webhook payload: {str(e)}"
        app.logger.error(error_msg)
        return jsonify({'error': 'Invalid payload'}), 400

    except stripe.error.SignatureVerificationError as e:
        error_msg = f"Invalid webhook signature: {str(e)}"
        app.logger.error(error_msg)
        return jsonify({'error': 'Invalid signature'}), 400

    except Exception as e:
        error_msg = f"Webhook processing error: {str(e)}"
        app.logger.error(error_msg, exc_info=True)

        # Update webhook log with error
        if webhook_log and webhook_log.id:
            try:
                webhook_log.error_message = error_msg
                db.session.commit()
            except:
                db.session.rollback()

        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/stripe/config')
def stripe_config():
    """Return Stripe publishable key for frontend"""
    # Initialize Stripe with the correct mode keys
    keys = init_stripe()

    if keys:
        publishable_key = keys['publishable_key']
        mode = keys['mode']
    else:
        # Fallback to legacy key
        publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')
        mode = 'unknown'

    return jsonify({
        'publishable_key': publishable_key,
        'configured': bool(publishable_key and stripe.api_key),
        'mode': mode
    })


# ============================================================================
# STRIPE PAYMENT METHODS (Saved Cards)
# ============================================================================

@app.route('/api/stripe/payment-methods', methods=['GET'])
@login_required
def get_payment_methods():
    """Get user's saved payment methods"""
    try:
        if not stripe.api_key:
            return jsonify({'error': 'Stripe is not configured'}), 500

        user_id = session['user_id']
        user = User.query.get(user_id)

        # Create Stripe customer if doesn't exist
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.username,
                metadata={'user_id': str(user_id)}
            )
            user.stripe_customer_id = customer.id
            db.session.commit()

        # List payment methods
        payment_methods = stripe.PaymentMethod.list(
            customer=user.stripe_customer_id,
            type='card'
        )

        return jsonify({
            'payment_methods': [{
                'id': pm.id,
                'card': {
                    'brand': pm.card.brand,
                    'last4': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year
                }
            } for pm in payment_methods.data]
        }), 200

    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': 'Failed to fetch payment methods'}), 500
    except Exception as e:
        app.logger.error(f"Get payment methods error: {str(e)}")
        return jsonify({'error': 'Failed to fetch payment methods'}), 500


@app.route('/api/stripe/setup-intent', methods=['POST'])
@login_required
def create_setup_intent():
    """Create a SetupIntent for adding a new payment method"""
    try:
        if not stripe.api_key:
            return jsonify({'error': 'Stripe is not configured'}), 500

        user_id = session['user_id']
        user = User.query.get(user_id)

        # Create Stripe customer if doesn't exist
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.username,
                metadata={'user_id': str(user_id)}
            )
            user.stripe_customer_id = customer.id
            db.session.commit()

        # Create SetupIntent
        setup_intent = stripe.SetupIntent.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            metadata={'user_id': str(user_id)}
        )

        return jsonify({
            'client_secret': setup_intent.client_secret
        }), 200

    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': 'Failed to create setup intent'}), 500
    except Exception as e:
        app.logger.error(f"Create setup intent error: {str(e)}")
        return jsonify({'error': 'Failed to create setup intent'}), 500


@app.route('/api/stripe/payment-methods/<payment_method_id>', methods=['DELETE'])
@login_required
def delete_payment_method(payment_method_id):
    """Delete a saved payment method"""
    try:
        if not stripe.api_key:
            return jsonify({'error': 'Stripe is not configured'}), 500

        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user.stripe_customer_id:
            return jsonify({'error': 'No saved payment methods'}), 404

        # Detach payment method from customer
        stripe.PaymentMethod.detach(payment_method_id)

        return jsonify({'message': 'Payment method deleted successfully'}), 200

    except stripe.error.InvalidRequestError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': 'Payment method not found'}), 404
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({'error': 'Failed to delete payment method'}), 500
    except Exception as e:
        app.logger.error(f"Delete payment method error: {str(e)}")
        return jsonify({'error': 'Failed to delete payment method'}), 500


# ============================================================================
# END STRIPE CHECKOUT
# ============================================================================

# Helper function to recalculate user rating
def recalculate_user_rating(user_id):
    """Recalculate and update user's average rating based on all reviews"""
    reviews = Review.query.filter_by(reviewee_id=user_id).all()
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        user = User.query.get(user_id)
        user.rating = round(avg_rating, 2)
        user.review_count = len(reviews)
        db.session.commit()
    else:
        user = User.query.get(user_id)
        user.rating = 0.0
        user.review_count = 0
        db.session.commit()

# Review Endpoints
@app.route('/api/gigs/<int:gig_id>/reviews', methods=['POST'])
@login_required
def create_review(gig_id):
    """Submit a review for a completed gig"""
    try:
        data = request.json
        gig = Gig.query.get_or_404(gig_id)

        # Validate gig is completed
        if gig.status != 'completed':
            return jsonify({'error': 'Can only review completed gigs'}), 400

        # Determine reviewer and reviewee based on user role in gig
        user_id = session['user_id']
        if gig.client_id == user_id:
            # Client reviewing freelancer
            reviewee_id = gig.freelancer_id
        elif gig.freelancer_id == user_id:
            # Freelancer reviewing client
            reviewee_id = gig.client_id
        else:
            return jsonify({'error': 'You are not part of this gig'}), 403

        # Validate rating
        rating = data.get('rating')
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400

        # Prevent self-review
        if user_id == reviewee_id:
            return jsonify({'error': 'Cannot review yourself'}), 400

        # Check if review already exists
        existing_review = Review.query.filter_by(gig_id=gig_id, reviewer_id=user_id).first()
        if existing_review:
            return jsonify({'error': 'You have already reviewed this gig'}), 400

        # Sanitize comment
        comment = sanitize_input(data.get('comment', ''), max_length=1000)

        # Create review
        review = Review(
            gig_id=gig_id,
            reviewer_id=user_id,
            reviewee_id=reviewee_id,
            rating=rating,
            comment=comment
        )

        db.session.add(review)
        db.session.commit()

        # Recalculate reviewee's rating
        recalculate_user_rating(reviewee_id)

        return jsonify({
            'message': 'Review submitted successfully',
            'review': {
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Create review error: {str(e)}")
        return jsonify({'error': 'Failed to submit review. Please try again.'}), 500

@app.route('/api/users/<int:user_id>/reviews', methods=['GET'])
def get_user_reviews(user_id):
    """Get all reviews for a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Limit per_page to prevent abuse
        per_page = min(per_page, 50)

        # Get reviews where user is the reviewee
        reviews_query = Review.query.filter_by(reviewee_id=user_id).order_by(Review.created_at.desc())
        paginated_reviews = reviews_query.paginate(page=page, per_page=per_page, error_out=False)

        reviews_data = []
        for review in paginated_reviews.items:
            reviewer = User.query.get(review.reviewer_id)
            gig = Gig.query.get(review.gig_id)
            reviews_data.append({
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat(),
                'updated_at': review.updated_at.isoformat(),
                'reviewer': {
                    'id': reviewer.id,
                    'username': reviewer.username,
                    'full_name': reviewer.full_name
                },
                'gig': {
                    'id': gig.id,
                    'title': gig.title
                }
            })

        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'rating': user.rating,
                'review_count': user.review_count
            },
            'reviews': reviews_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_reviews.total,
                'pages': paginated_reviews.pages
            }
        }), 200

    except Exception as e:
        app.logger.error(f"Get user reviews error: {str(e)}")
        return jsonify({'error': 'Failed to fetch reviews'}), 500

@app.route('/api/reviews/<int:review_id>', methods=['GET'])
def get_review(review_id):
    """Get a specific review"""
    try:
        review = Review.query.get_or_404(review_id)
        reviewer = User.query.get(review.reviewer_id)
        reviewee = User.query.get(review.reviewee_id)
        gig = Gig.query.get(review.gig_id)

        return jsonify({
            'id': review.id,
            'rating': review.rating,
            'comment': review.comment,
            'created_at': review.created_at.isoformat(),
            'updated_at': review.updated_at.isoformat(),
            'reviewer': {
                'id': reviewer.id,
                'username': reviewer.username,
                'full_name': reviewer.full_name
            },
            'reviewee': {
                'id': reviewee.id,
                'username': reviewee.username,
                'full_name': reviewee.full_name
            },
            'gig': {
                'id': gig.id,
                'title': gig.title
            }
        }), 200

    except Exception as e:
        app.logger.error(f"Get review error: {str(e)}")
        return jsonify({'error': 'Review not found'}), 404

@app.route('/api/reviews/<int:review_id>', methods=['PUT'])
@login_required
def update_review(review_id):
    """Update a review (only by the reviewer)"""
    try:
        review = Review.query.get_or_404(review_id)

        # Check if user is the reviewer
        if review.reviewer_id != session['user_id']:
            return jsonify({'error': 'You can only update your own reviews'}), 403

        data = request.json

        # Update rating if provided
        if 'rating' in data:
            rating = data['rating']
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400
            review.rating = rating

        # Update comment if provided
        if 'comment' in data:
            review.comment = sanitize_input(data['comment'], max_length=1000)

        db.session.commit()

        # Recalculate reviewee's rating if rating changed
        if 'rating' in data:
            recalculate_user_rating(review.reviewee_id)

        return jsonify({
            'message': 'Review updated successfully',
            'review': {
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment,
                'updated_at': review.updated_at.isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Update review error: {str(e)}")
        return jsonify({'error': 'Failed to update review'}), 500

@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@login_required
def delete_review(review_id):
    """Delete a review (only by the reviewer or admin)"""
    try:
        review = Review.query.get_or_404(review_id)
        user = User.query.get(session['user_id'])

        # Check if user is the reviewer or admin
        if review.reviewer_id != session['user_id'] and not user.is_admin:
            return jsonify({'error': 'You can only delete your own reviews'}), 403

        reviewee_id = review.reviewee_id

        db.session.delete(review)
        db.session.commit()

        # Recalculate reviewee's rating
        recalculate_user_rating(reviewee_id)

        return jsonify({'message': 'Review deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete review error: {str(e)}")
        return jsonify({'error': 'Failed to delete review'}), 500

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'phone': user.phone,
        'user_type': user.user_type,
        'location': user.location,
        'bio': user.bio,
        'skills': json.loads(user.skills) if user.skills else [],
        'rating': user.rating,
        'review_count': user.review_count,
        'total_earnings': user.total_earnings,
        'completed_gigs': user.completed_gigs,
        'is_verified': user.is_verified,
        'halal_verified': user.halal_verified,
        'language': user.language,
        'created_at': user.created_at.isoformat()
    })

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Sanitize and validate inputs
        if 'full_name' in data:
            user.full_name = sanitize_input(data['full_name'], max_length=120)

        if 'phone' in data:
            is_valid, message = validate_phone(data['phone'])
            if not is_valid:
                return jsonify({'error': message}), 400
            user.phone = data['phone']

        if 'location' in data:
            user.location = sanitize_input(data['location'], max_length=100)

        if 'bio' in data:
            user.bio = sanitize_input(data['bio'], max_length=2000)

        if 'skills' in data:
            skills = data['skills']
            if not isinstance(skills, list):
                return jsonify({'error': 'Skills must be an array'}), 400
            # Limit to 20 skills, each max 50 chars
            skills = [sanitize_input(str(skill), max_length=50) for skill in skills[:20]]
            user.skills = json.dumps(skills)

        db.session.commit()

        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Update profile error: {str(e)}")
        return jsonify({'error': 'Failed to update profile. Please try again.'}), 500

@app.route('/api/language', methods=['POST'])
def switch_language():
    """Switch user's language preference"""
    try:
        data = request.json
        language = data.get('language', 'ms')

        # Validate language
        if language not in ['ms', 'en']:
            return jsonify({'error': 'Invalid language. Choose "ms" or "en"'}), 400

        # Update user's language if logged in
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                user.language = language
                db.session.commit()
        else:
            # Store in session for non-logged in users
            session['language'] = language

        return jsonify({
            'message': 'Language updated successfully',
            'language': language
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Language switch error: {str(e)}")
        return jsonify({'error': 'Failed to update language'}), 500

@app.route('/api/microtasks', methods=['GET'])
def get_microtasks():
    tasks = MicroTask.query.filter_by(status='available').limit(20).all()
    
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'reward': t.reward,
        'task_type': t.task_type
    } for t in tasks])

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total_gigs = Gig.query.count()
    active_gigs = Gig.query.filter_by(status='open').count()
    total_users = User.query.count()
    total_earnings = db.session.query(db.func.sum(Transaction.amount)).scalar() or 0
    
    return jsonify({
        'total_gigs': total_gigs,
        'active_gigs': active_gigs,
        'total_users': total_users,
        'total_earnings': total_earnings
    })

@app.route('/api/categories', methods=['GET'])
def get_categories():
    # Emoji mapping for categories - comprehensive map for all 41 categories
    emoji_map = {
        # Design & Creative
        'graphic-design': '🎨',
        'ui-ux': '🎨',
        'illustration': '🖌️',
        'logo-design': '🏷️',
        'fashion': '👗',
        'interior-design': '🏠',
        
        # Writing & Content
        'content-writing': '✍️',
        'translation': '🌐',
        'proofreading': '✏️',
        'resume': '📄',
        'email-marketing': '📧',
        'social-copy': '📱',
        
        # Video & Media
        'video-editing': '🎬',
        'animation': '🎞️',
        'voiceover': '🎙️',
        'podcast': '🎧',
        'photography': '📸',
        
        # Web & App Development
        'web-development': '💻',
        'app-development': '📱',
        'ecommerce': '🛒',
        
        # Marketing & Business
        'digital-marketing': '📈',
        'social-media': '📲',
        'business-consulting': '💼',
        'data-analysis': '📊',
        
        # Education & Tutoring
        'tutoring': '📚',
        'language-teaching': '🗣️',
        
        # Technical & Engineering
        'programming': '🖥️',
        'engineering': '🛠️',
        
        # Admin & Support
        'virtual-assistant': '📋',
        'transcription': '🎤',
        'data-entry': '💾',
        
        # Finance & Legal
        'bookkeeping': '💰',
        'legal': '⚖️',
        
        # Lifestyle & Personal
        'wellness-coaching': '💪',
        'personal-styling': '👔',
        'pet-services': '🐾',
        
        # Home & Handyman
        'home-repair': '🔧',
        'cleaning': '🧹',
        'gardening': '🌱',
        
        # Specialized Services
        'crafts': '✨',
        'music-production': '🎵',
        'event-planning': '🎉',
        'tours': '✈️',
        
        # General
        'general': '📦',
        'design': '🎨',
        'writing': '✍️',
        'video': '🎬',
        'content': '📱',
        'web': '💻',
        'marketing': '📈',
        'admin': '📋',
        'consulting': '💼',
        'music': '🎵',
        'finance': '💰',
        'crafts': '✨',
        'garden': '🌱',
        'coaching': '💪',
        'data': '📊',
        'pets': '🐾',
        'handyman': '🔧',
        'events': '🎉',
        'online-selling': '🛍️'
    }

    # Get user's language preference
    lang = get_user_language()

    # Get main categories only (exclude detailed subcategories) and sort alphabetically
    categories = Category.query.filter(Category.slug.in_(MAIN_CATEGORY_SLUGS)).order_by(Category.name).all()
    result = [{
        'id': cat.slug,
        'name': cat.name,  # Use actual category name, not translation key
        'icon': emoji_map.get(cat.slug, '📋')
    } for cat in categories]

    response = jsonify(result)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/about')
def about():
    """Serve the About Us page"""
    return render_template('about.html', lang=get_user_language(), t=t)

@app.route('/api/admin/analytics')
def get_admin_analytics():
    """Get visitor analytics for admin panel"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Last 30 days analytics
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Total visits
        total_visits = VisitorLog.query.count()
        recent_visits = VisitorLog.query.filter(VisitorLog.timestamp >= thirty_days_ago).count()
        
        # Unique visitors (by IP)
        unique_visitors = db.session.query(VisitorLog.ip_address).distinct().count()
        
        # Visits by path
        path_stats = db.session.query(
            VisitorLog.path, db.func.count(VisitorLog.id)
        ).group_by(VisitorLog.path).order_by(db.func.count(VisitorLog.id).desc()).limit(10).all()
        
        # Visits by day (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        daily_stats = db.session.query(
            db.func.date(VisitorLog.timestamp), db.func.count(VisitorLog.id)
        ).filter(VisitorLog.timestamp >= seven_days_ago).group_by(db.func.date(VisitorLog.timestamp)).all()

        return jsonify({
            'total_visits': total_visits,
            'recent_visits': recent_visits,
            'unique_visitors': unique_visitors,
            'top_pages': [{'path': p[0], 'count': p[1]} for p in path_stats],
            'daily_visits': [{'date': str(d[0]), 'count': d[1]} for d in daily_stats]
        }), 200
    except Exception as e:
        app.logger.error(f"Analytics error: {str(e)}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500

# Admin Routes
@app.route('/admin')
def admin_page():
    """Serve admin dashboard page"""
    if 'user_id' not in session:
        return render_template('index.html', lang=get_user_language(), t=t)

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return render_template('index.html', lang=get_user_language(), t=t)

    return render_template('admin.html', user=user, lang=get_user_language(), t=t)

@app.route('/admin/security-logs')
@page_login_required
def admin_security_logs_page():
    """Serve admin security logs page"""
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect('/')

    return render_template('admin_security_logs.html', user=user, lang=get_user_language(), t=t)

@app.route('/admin/socso-registration')
@page_login_required
def admin_socso_registration_page():
    """Serve admin SOCSO registration page"""
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect('/')

    return render_template('admin_socso_registration.html', user=user, lang=get_user_language(), t=t, active_page='admin')

@app.route('/api/admin/freelancers/search', methods=['GET'])
@admin_required
def search_freelancers():
    """Search for freelancers by name, email, IC, or phone"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'freelancers': []}), 200

        # Search in multiple fields
        users = User.query.filter(
            db.or_(
                User.full_name.ilike(f'%{query}%'),
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                User.ic_number.ilike(f'%{query}%'),
                User.phone.ilike(f'%{query}%')
            ),
            db.or_(
                User.user_type == 'freelancer',
                User.user_type == 'both'
            )
        ).limit(20).all()

        freelancers = [{
            'id': u.id,
            'username': u.username,
            'full_name': u.full_name,
            'email': u.email,
            'phone': u.phone,
            'ic_number': u.ic_number,
            'socso_registered': u.socso_registered,
            'socso_data_complete': u.socso_data_complete,
            'socso_membership_number': u.socso_membership_number,
            'socso_submitted_to_portal': u.socso_submitted_to_portal,
            'socso_portal_submission_date': u.socso_portal_submission_date.isoformat() if u.socso_portal_submission_date else None,
            'socso_portal_reference_number': u.socso_portal_reference_number
        } for u in users]

        return jsonify({'freelancers': freelancers}), 200
    except Exception as e:
        app.logger.error(f"Error searching freelancers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/user/<int:user_id>', methods=['GET'])
@admin_required
def get_user_for_admin(user_id):
    """Get user details for admin"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'phone': user.phone,
            'ic_number': user.ic_number,
            'date_of_birth': user.date_of_birth.isoformat() if user.date_of_birth else None,
            'gender': user.gender,
            'marital_status': user.marital_status,
            'nationality': user.nationality,
            'race': user.race,
            'address_line1': user.address_line1,
            'address_line2': user.address_line2,
            'postcode': user.postcode,
            'city': user.city,
            'state': user.state,
            'country': user.country,
            'self_employment_start_date': user.self_employment_start_date.isoformat() if user.self_employment_start_date else None,
            'monthly_income_range': user.monthly_income_range,
            'bank_name': user.bank_name,
            'bank_account_number': user.bank_account_number,
            'bank_account_holder': user.bank_account_holder,
            'socso_registered': user.socso_registered,
            'socso_consent': user.socso_consent,
            'socso_data_complete': user.socso_data_complete,
            'socso_membership_number': user.socso_membership_number,
            'socso_submitted_to_portal': user.socso_submitted_to_portal,
            'socso_portal_submission_date': user.socso_portal_submission_date.isoformat() if user.socso_portal_submission_date else None,
            'socso_portal_reference_number': user.socso_portal_reference_number
        }), 200
    except Exception as e:
        app.logger.error(f"Error getting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/socso/register', methods=['POST'])
@admin_required
def register_user_for_socso():
    """Register or update user's SOCSO information"""
    try:
        data = request.json
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update personal information
        if data.get('full_name'):
            user.full_name = data['full_name']
        if data.get('ic_number'):
            user.ic_number = data['ic_number']
        if data.get('date_of_birth'):
            user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        if data.get('gender'):
            user.gender = data['gender']
        if data.get('marital_status'):
            user.marital_status = data['marital_status']
        if data.get('nationality'):
            user.nationality = data['nationality']
        if data.get('race'):
            user.race = data['race']

        # Update contact information
        if data.get('email'):
            user.email = data['email']
        if data.get('phone'):
            user.phone = data['phone']
        if data.get('address_line1'):
            user.address_line1 = data['address_line1']
        if data.get('address_line2') is not None:
            user.address_line2 = data['address_line2']
        if data.get('postcode'):
            user.postcode = data['postcode']
        if data.get('city'):
            user.city = data['city']
        if data.get('state'):
            user.state = data['state']
        if data.get('country'):
            user.country = data['country']

        # Update employment information
        if data.get('self_employment_start_date'):
            user.self_employment_start_date = datetime.strptime(data['self_employment_start_date'], '%Y-%m-%d').date()
        if data.get('monthly_income_range'):
            user.monthly_income_range = data['monthly_income_range']

        # Update bank information
        if data.get('bank_name'):
            user.bank_name = data['bank_name']
        if data.get('bank_account_number'):
            user.bank_account_number = data['bank_account_number']
        if data.get('bank_account_holder'):
            user.bank_account_holder = data['bank_account_holder']

        # Update SOCSO information
        if data.get('socso_membership_number'):
            user.socso_membership_number = data['socso_membership_number']
        if data.get('socso_consent'):
            user.socso_consent = True
            if not user.socso_consent_date:
                user.socso_consent_date = datetime.utcnow()

        # Set SOCSO registration flags
        user.socso_registered = True
        user.socso_registration_date = datetime.utcnow()

        # Check if all required data is complete
        required_fields = [
            user.full_name, user.ic_number, user.date_of_birth, user.gender,
            user.marital_status, user.nationality, user.race, user.email,
            user.phone, user.address_line1, user.postcode, user.city,
            user.state, user.country, user.self_employment_start_date,
            user.monthly_income_range, user.bank_name, user.bank_account_number,
            user.bank_account_holder, user.socso_consent
        ]
        user.socso_data_complete = all(field is not None and field != '' for field in required_fields)

        db.session.commit()

        # Log the security event
        log_security_event(
            user_id=session['user_id'],
            action='socso_registration',
            resource_type='user',
            resource_id=user.id,
            status='success',
            message=f'Admin registered user {user.username} for SOCSO',
            severity='low'
        )

        return jsonify({
            'success': True,
            'message': 'User registered for SOCSO successfully',
            'socso_data_complete': user.socso_data_complete
        }), 200

    except ValueError as e:
        app.logger.error(f"Invalid date format: {str(e)}")
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error registering user for SOCSO: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/socso/mark-submitted', methods=['POST'])
@admin_required
def mark_socso_submitted():
    """Mark user as submitted to SOCSO portal"""
    try:
        data = request.json
        user_id = data.get('user_id')
        reference_number = data.get('reference_number', '')

        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update submission status
        user.socso_submitted_to_portal = True
        user.socso_portal_submission_date = datetime.utcnow()
        if reference_number:
            user.socso_portal_reference_number = reference_number

        db.session.commit()

        # Log the security event
        log_security_event(
            user_id=session['user_id'],
            action='socso_portal_submission',
            resource_type='user',
            resource_id=user.id,
            status='success',
            message=f'Admin marked user {user.username} as submitted to SOCSO portal',
            severity='low'
        )

        return jsonify({
            'success': True,
            'message': 'User marked as submitted to SOCSO portal',
            'submission_date': user.socso_portal_submission_date.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error marking SOCSO submission: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/socso/unmark-submitted', methods=['POST'])
@admin_required
def unmark_socso_submitted():
    """Unmark user as submitted to SOCSO portal (undo submission)"""
    try:
        data = request.json
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Reset submission status
        user.socso_submitted_to_portal = False
        user.socso_portal_submission_date = None
        user.socso_portal_reference_number = None

        db.session.commit()

        # Log the security event
        log_security_event(
            user_id=session['user_id'],
            action='socso_portal_submission_undo',
            resource_type='user',
            resource_id=user.id,
            status='success',
            message=f'Admin unmarked user {user.username} as submitted to SOCSO portal',
            severity='low'
        )

        return jsonify({
            'success': True,
            'message': 'User unmarked from SOCSO portal submission'
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error unmarking SOCSO submission: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/check', methods=['GET'])
def check_admin():
    """Check if current user is admin"""
    if 'user_id' not in session:
        return jsonify({'is_admin': False}), 200

    user = User.query.get(session['user_id'])
    return jsonify({
        'is_admin': user.is_admin if user else False,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        } if user and user.is_admin else None
    }), 200

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    """Get admin dashboard statistics"""
    try:
        total_users = User.query.count()
        total_freelancers = User.query.filter_by(user_type='freelancer').count()
        total_clients = User.query.filter_by(user_type='client').count()
        verified_users = User.query.filter_by(is_verified=True).count()
        halal_verified_users = User.query.filter_by(halal_verified=True).count()

        total_gigs = Gig.query.count()
        open_gigs = Gig.query.filter_by(status='open').count()
        in_progress_gigs = Gig.query.filter_by(status='in_progress').count()
        completed_gigs = Gig.query.filter_by(status='completed').count()
        halal_gigs = Gig.query.filter_by(halal_compliant=True).count()

        total_applications = Application.query.count()
        pending_applications = Application.query.filter_by(status='pending').count()

        # Financial statistics
        # Total payout: Sum of all released escrows (amount paid to workers)
        total_payout = db.session.query(db.func.sum(Escrow.amount)).filter(
            Escrow.status == 'released'
        ).scalar() or 0

        # Commission: Sum of all commission amounts charged
        total_commission = db.session.query(db.func.sum(Transaction.commission)).scalar() or 0

        # Escrow: Sum of all funded escrows (money currently held)
        total_escrow = db.session.query(db.func.sum(Escrow.amount)).filter(
            Escrow.status == 'funded'
        ).scalar() or 0

        # SOCSO statistics (Gig Workers Bill 2025 compliance)
        total_socso_collected = db.session.query(
            db.func.sum(SocsoContribution.socso_amount)
        ).scalar() or 0

        total_socso_remitted = db.session.query(
            db.func.sum(SocsoContribution.socso_amount)
        ).filter(SocsoContribution.remitted_to_socso == True).scalar() or 0

        total_socso_pending = float(total_socso_collected) - float(total_socso_remitted)

        # SOCSO registered freelancers
        socso_registered_freelancers = User.query.filter(
            User.socso_consent == True,
            User.user_type.in_(['freelancer', 'both'])
        ).count()

        # Current month SOCSO
        current_month = datetime.utcnow().strftime('%Y-%m')
        current_month_socso = db.session.query(
            db.func.sum(SocsoContribution.socso_amount)
        ).filter(SocsoContribution.contribution_month == current_month).scalar() or 0

        # Recent users (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = User.query.filter(User.created_at >= week_ago).count()

        # Recent gigs (last 7 days)
        recent_gigs = Gig.query.filter(Gig.created_at >= week_ago).count()

        return jsonify({
            'users': {
                'total': total_users,
                'freelancers': total_freelancers,
                'clients': total_clients,
                'verified': verified_users,
                'halal_verified': halal_verified_users,
                'recent_week': recent_users,
                'recent': recent_users
            },
            'gigs': {
                'total': total_gigs,
                'open': open_gigs,
                'in_progress': in_progress_gigs,
                'completed': completed_gigs,
                'halal_compliant': halal_gigs,
                'recent_week': recent_gigs,
                'recent': recent_gigs
            },
            'applications': {
                'total': total_applications,
                'pending': pending_applications
            },
            'financial': {
                'total_payout': float(total_payout),
                'commission': float(total_commission),
                'escrow': float(total_escrow)
            },
            'socso': {
                'total_collected': float(total_socso_collected),
                'total_remitted': float(total_socso_remitted),
                'pending_remittance': float(total_socso_pending),
                'current_month_collection': float(current_month_socso),
                'registered_freelancers': socso_registered_freelancers,
                'compliance_rate': round((socso_registered_freelancers / total_freelancers * 100), 2) if total_freelancers > 0 else 0
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Admin stats error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

# ==================== SECURITY AUDIT LOG ROUTES ====================

@app.route('/api/admin/audit-logs', methods=['GET'])
@admin_required
def admin_get_audit_logs():
    """Get security audit logs with filtering options"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        # Filters
        category = request.args.get('category')  # authentication, authorization, admin, financial, data_access, system
        severity = request.args.get('severity')  # low, medium, high, critical
        user_id = request.args.get('user_id', type=int)
        event_type = request.args.get('event_type')
        status = request.args.get('status')  # success, failure, blocked
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')

        query = AuditLog.query

        # Apply filters
        if category:
            query = query.filter(AuditLog.event_category == category)
        if severity:
            query = query.filter(AuditLog.severity == severity)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if status:
            query = query.filter(AuditLog.status == status)
        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.created_at <= end_dt)
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                (AuditLog.username.ilike(search_pattern)) |
                (AuditLog.action.ilike(search_pattern)) |
                (AuditLog.message.ilike(search_pattern))
            )

        logs = query.order_by(AuditLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': logs.page
        }), 200
    except Exception as e:
        app.logger.error(f"Admin get audit logs error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve audit logs'}), 500

@app.route('/api/admin/audit-logs/<int:log_id>', methods=['GET'])
@admin_required
def admin_get_audit_log_detail(log_id):
    """Get detailed information about a specific audit log entry"""
    try:
        log = AuditLog.query.get_or_404(log_id)

        log_detail = log.to_dict()

        # Parse JSON fields
        if log.details:
            try:
                log_detail['details'] = json.loads(log.details)
            except:
                log_detail['details'] = log.details

        if log.old_value:
            try:
                log_detail['old_value'] = json.loads(log.old_value)
            except:
                log_detail['old_value'] = log.old_value

        if log.new_value:
            try:
                log_detail['new_value'] = json.loads(log.new_value)
            except:
                log_detail['new_value'] = log.new_value

        return jsonify(log_detail), 200
    except Exception as e:
        app.logger.error(f"Admin get audit log detail error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve audit log detail'}), 500

@app.route('/api/admin/audit-logs/stats', methods=['GET'])
@admin_required
def admin_audit_log_stats():
    """Get statistics about audit logs"""
    try:
        # Total logs
        total_logs = AuditLog.query.count()

        # Logs by category
        category_stats = db.session.query(
            AuditLog.event_category,
            db.func.count(AuditLog.id)
        ).group_by(AuditLog.event_category).all()

        # Logs by severity
        severity_stats = db.session.query(
            AuditLog.severity,
            db.func.count(AuditLog.id)
        ).group_by(AuditLog.severity).all()

        # Failed authentication attempts (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        failed_auth_24h = AuditLog.query.filter(
            AuditLog.event_category == 'authentication',
            AuditLog.status == 'failure',
            AuditLog.created_at >= day_ago
        ).count()

        # Permission denials (last 24 hours)
        permission_denied_24h = AuditLog.query.filter(
            AuditLog.event_category == 'authorization',
            AuditLog.status == 'blocked',
            AuditLog.created_at >= day_ago
        ).count()

        # Critical events (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        critical_events_7d = AuditLog.query.filter(
            AuditLog.severity == 'critical',
            AuditLog.created_at >= week_ago
        ).count()

        # Top users by activity (last 7 days)
        top_users = db.session.query(
            AuditLog.username,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= week_ago,
            AuditLog.username.isnot(None)
        ).group_by(AuditLog.username).order_by(db.desc('count')).limit(10).all()

        return jsonify({
            'total_logs': total_logs,
            'by_category': {cat: count for cat, count in category_stats},
            'by_severity': {sev: count for sev, count in severity_stats},
            'failed_auth_24h': failed_auth_24h,
            'permission_denied_24h': permission_denied_24h,
            'critical_events_7d': critical_events_7d,
            'top_users_7d': [{'username': u, 'count': c} for u, c in top_users]
        }), 200
    except Exception as e:
        app.logger.error(f"Admin audit log stats error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve audit log statistics'}), 500

@app.route('/api/admin/audit-logs/export', methods=['GET'])
@admin_required
def admin_export_audit_logs():
    """Export audit logs as JSON for external SIEM systems"""
    try:
        # Get filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        severity = request.args.get('severity')

        query = AuditLog.query

        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.created_at <= end_dt)
        if category:
            query = query.filter(AuditLog.event_category == category)
        if severity:
            query = query.filter(AuditLog.severity == severity)

        # Limit to prevent excessive exports
        logs = query.order_by(AuditLog.created_at.desc()).limit(10000).all()

        # Export as JSON
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'total_records': len(logs),
            'logs': [log.to_dict() for log in logs]
        }

        return jsonify(export_data), 200
    except Exception as e:
        app.logger.error(f"Admin export audit logs error: {str(e)}")
        return jsonify({'error': 'Failed to export audit logs'}), 500

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Get all users for admin management"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = sanitize_input(request.args.get('search', ''), max_length=100)

        query = User.query

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_pattern)) |
                (User.email.ilike(search_pattern)) |
                (User.full_name.ilike(search_pattern))
            )

        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'users': [{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'full_name': u.full_name,
                'user_type': u.user_type,
                'location': u.location,
                'rating': u.rating,
                'total_earnings': u.total_earnings,
                'completed_gigs': u.completed_gigs,
                'is_verified': u.is_verified,
                'halal_verified': u.halal_verified,
                'is_admin': u.is_admin,
                'created_at': u.created_at.isoformat()
            } for u in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': users.page
        }), 200
    except Exception as e:
        app.logger.error(f"Admin get users error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve users'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['GET'])
@admin_required
def admin_get_user(user_id):
    """Get a single user's complete details for admin view"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'ic_number': user.ic_number,
                'user_type': user.user_type,
                'location': user.location,
                'skills': user.skills,
                'bio': user.bio,
                'rating': user.rating,
                'review_count': user.review_count,
                'total_earnings': user.total_earnings,
                'completed_gigs': user.completed_gigs,
                'language': user.language,
                'is_verified': user.is_verified,
                'halal_verified': user.halal_verified,
                'is_admin': user.is_admin,
                'bank_name': user.bank_name,
                'bank_account_number': user.bank_account_number,
                'bank_account_holder': user.bank_account_holder,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Admin get user error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve user'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def admin_update_user(user_id):
    """Update user details (verify, ban, make admin)"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update verification status
        if 'is_verified' in data:
            user.is_verified = bool(data['is_verified'])

        if 'halal_verified' in data:
            user.halal_verified = bool(data['halal_verified'])

        # Update admin status
        if 'is_admin' in data:
            user.is_admin = bool(data['is_admin'])

        # Update user type
        if 'user_type' in data and data['user_type'] in ['freelancer', 'client', 'both']:
            user.user_type = data['user_type']

        db.session.commit()

        return jsonify({
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_verified': user.is_verified,
                'halal_verified': user.halal_verified,
                'is_admin': user.is_admin
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin update user error: {str(e)}")
        return jsonify({'error': 'Failed to update user'}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user (use with caution)"""
    try:
        # Prevent deleting yourself
        if session['user_id'] == user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400

        user = User.query.get_or_404(user_id)

        # Delete associated data
        Application.query.filter_by(freelancer_id=user_id).delete()
        Review.query.filter(
            (Review.reviewer_id == user_id) | (Review.reviewee_id == user_id)
        ).delete()

        # Delete user's gigs and related applications
        user_gigs = Gig.query.filter_by(client_id=user_id).all()
        for gig in user_gigs:
            Application.query.filter_by(gig_id=gig.id).delete()
            db.session.delete(gig)

        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin delete user error: {str(e)}")
        return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/admin/send-sms', methods=['POST'])
@admin_required
def admin_send_sms():
    """Send SMS message to all users"""
    try:
        if not twilio_client or not twilio_phone_number:
            return jsonify({'error': 'SMS service not configured'}), 500
        
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if len(message) > 160:
            return jsonify({'error': 'Message must be 160 characters or less'}), 400
        
        # Get all users with phone numbers
        users = User.query.filter(User.phone != None).filter(User.phone != '').all()
        
        if not users:
            return jsonify({'error': 'No users with phone numbers found'}), 400
        
        sent_count = 0
        failed_count = 0
        failed_users = []
        
        for user in users:
            try:
                twilio_client.messages.create(
                    body=message,
                    from_=twilio_phone_number,
                    to=user.phone
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                failed_users.append({
                    'username': user.username,
                    'phone': user.phone,
                    'error': str(e)
                })
                app.logger.warning(f"Failed to send SMS to {user.username} ({user.phone}): {str(e)}")
        
        return jsonify({
            'message': 'SMS broadcast completed',
            'sent': sent_count,
            'failed': failed_count,
            'total_users': len(users),
            'failed_users': failed_users if failed_count > 0 else []
        }), 200
    except Exception as e:
        app.logger.error(f"Admin send SMS error: {str(e)}")
        return jsonify({'error': 'Failed to send SMS broadcast'}), 500

@app.route('/api/admin/send-email', methods=['POST'])
@admin_required
def admin_send_email():
    """Send email to selected users or all users"""
    try:
        data = request.get_json()
        subject = data.get('subject', '').strip()
        html_content = data.get('html_content', '').strip()
        text_content = data.get('text_content', '').strip()
        recipient_type = data.get('recipient_type', 'all')  # 'all', 'freelancers', 'clients', 'selected'
        selected_user_ids = data.get('selected_user_ids', [])
        
        # Validation
        if not subject:
            return jsonify({'error': 'Email subject cannot be empty'}), 400
        if not html_content:
            return jsonify({'error': 'Email content cannot be empty'}), 400
        
        # Build recipient list
        if recipient_type == 'all':
            users = User.query.all()
        elif recipient_type == 'freelancers':
            users = User.query.filter(User.user_type.in_(['freelancer', 'both'])).all()
        elif recipient_type == 'clients':
            users = User.query.filter(User.user_type.in_(['client', 'both'])).all()
        elif recipient_type == 'selected':
            if not selected_user_ids:
                return jsonify({'error': 'No users selected'}), 400
            users = User.query.filter(User.id.in_(selected_user_ids)).all()
        else:
            return jsonify({'error': 'Invalid recipient type'}), 400
        
        if not users:
            return jsonify({'error': 'No matching users found'}), 400
        
        # Prepare email list
        to_emails = [(user.email, user.full_name or user.username) for user in users]
        
        # Ensure HTML content has proper line breaks if it's plain text from a textarea
        if '<' not in html_content and '>' not in html_content:
            html_content = html_content.replace('\n', '<br>')

        # Send email
        success, message, status_code, details = email_service.send_bulk_email(
            to_emails=to_emails,
            subject=subject,
            html_content=html_content,
            text_content=text_content or None
        )

        # Create database log entry
        try:
            email_log = EmailSendLog(
                email_type='admin_bulk',
                subject=subject,
                sender_user_id=current_user.id if current_user and current_user.is_authenticated else None,
                recipient_count=details.get('total_count', len(users)),
                successful_count=details.get('successful_count', 0),
                failed_count=details.get('failed_count', 0),
                recipient_type=recipient_type,
                success=success,
                error_message=message if not success else None,
                brevo_message_ids=json.dumps(details.get('brevo_message_ids', [])),
                failed_recipients=json.dumps(details.get('failed_recipients', []))
            )
            db.session.add(email_log)
            db.session.commit()
            app.logger.info(f"[EMAIL_LOG] Created database log entry ID {email_log.id} for email send operation")
        except Exception as log_error:
            app.logger.error(f"[EMAIL_LOG] Failed to create database log: {str(log_error)}")
            # Don't fail the request if logging fails
            db.session.rollback()

        if success:
            # Log the email action
            app.logger.info(f"Admin sent email to {len(users)} users. Subject: {subject}. Success: {details.get('successful_count', 0)}, Failed: {details.get('failed_count', 0)}")
            return jsonify({
                'message': message,
                'recipients_count': len(users),
                'recipient_type': recipient_type,
                'successful_count': details.get('successful_count', 0),
                'failed_count': details.get('failed_count', 0)
            }), 200
        else:
            return jsonify({'error': message}), 500

    except Exception as e:
        app.logger.error(f"Admin send email error: {str(e)}")
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500


@app.route('/api/admin/send-whatsapp', methods=['POST'])
@admin_required
def admin_send_whatsapp():
    """Send WhatsApp message to all users"""
    try:
        if not twilio_client or not twilio_phone_number:
            return jsonify({'error': 'WhatsApp service not configured'}), 500
        
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        if len(message) > 1024:
            return jsonify({'error': 'Message must be 1024 characters or less'}), 400
        
        # Get all users with phone numbers
        users = User.query.filter(User.phone != None).filter(User.phone != '').all()
        
        if not users:
            return jsonify({'error': 'No users with phone numbers found'}), 400
        
        sent_count = 0
        failed_count = 0
        failed_users = []
        
        # WhatsApp format: whatsapp:+[phone number]
        whatsapp_from = f"whatsapp:{twilio_phone_number}"
        
        for user in users:
            try:
                whatsapp_to = f"whatsapp:{user.phone}"
                twilio_client.messages.create(
                    body=message,
                    from_=whatsapp_from,
                    to=whatsapp_to
                )
                sent_count += 1
            except Exception as e:
                failed_count += 1
                failed_users.append({
                    'username': user.username,
                    'phone': user.phone,
                    'error': str(e)
                })
                app.logger.warning(f"Failed to send WhatsApp to {user.username} ({user.phone}): {str(e)}")
        
        return jsonify({
            'message': 'WhatsApp broadcast completed',
            'sent': sent_count,
            'failed': failed_count,
            'total_users': len(users),
            'failed_users': failed_users if failed_count > 0 else []
        }), 200
    except Exception as e:
        app.logger.error(f"Admin send WhatsApp error: {str(e)}")
        return jsonify({'error': 'Failed to send WhatsApp broadcast'}), 500

@app.route('/api/admin/gigs', methods=['GET'])
@admin_required
def admin_get_gigs():
    """Get all gigs for admin management"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        status = request.args.get('status', '')

        query = Gig.query

        if status:
            query = query.filter_by(status=status)

        gigs = query.order_by(Gig.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        result = []
        for g in gigs.items:
            client = User.query.get(g.client_id)
            worker = User.query.get(g.freelancer_id) if g.freelancer_id else None
            result.append({
                'id': g.id,
                'title': g.title,
                'description': g.description,
                'category': g.category,
                'budget_min': g.budget_min,
                'budget_max': g.budget_max,
                'approved_budget': g.approved_budget,
                'status': g.status,
                'halal_compliant': g.halal_compliant,
                'halal_verified': g.halal_verified,
                'views': g.views,
                'applications': g.applications,
                'created_at': g.created_at.isoformat(),
                'agreed_amount': g.agreed_amount,
                'client': {
                    'id': client.id,
                    'username': client.username,
                    'email': client.email
                } if client else None,
                'worker': {
                    'id': worker.id,
                    'username': worker.username,
                    'email': worker.email
                } if worker else None
            })

        return jsonify({
            'gigs': result,
            'total': gigs.total,
            'pages': gigs.pages,
            'current_page': gigs.page
        }), 200
    except Exception as e:
        app.logger.error(f"Admin get gigs error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve gigs'}), 500

@app.route('/api/admin/gigs/<int:gig_id>', methods=['PUT'])
@admin_required
def admin_update_gig(gig_id):
    """Update gig status or verification"""
    try:
        gig = Gig.query.get_or_404(gig_id)
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update status
        if 'status' in data and data['status'] in ['open', 'in_progress', 'completed', 'cancelled']:
            gig.status = data['status']

        # Update halal verification
        if 'halal_verified' in data:
            gig.halal_verified = bool(data['halal_verified'])

        # Update agreed amount
        if 'agreed_amount' in data:
            gig.agreed_amount = float(data['agreed_amount']) if data['agreed_amount'] else None

        # Update approved budget
        if 'approved_budget' in data:
            gig.approved_budget = float(data['approved_budget']) if data['approved_budget'] else None

        db.session.commit()

        return jsonify({
            'message': 'Gig updated successfully',
            'gig': {
                'id': gig.id,
                'title': gig.title,
                'status': gig.status,
                'halal_verified': gig.halal_verified
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin update gig error: {str(e)}")
        return jsonify({'error': 'Failed to update gig'}), 500

@app.route('/api/admin/gigs/<int:gig_id>', methods=['DELETE'])
@admin_required
def admin_delete_gig(gig_id):
    """Delete a gig and all associated records"""
    try:
        gig = Gig.query.get_or_404(gig_id)

        # Get gig owner information before deletion
        gig_owner = User.query.get(gig.client_id)
        if gig_owner and gig_owner.email:
            # Send email notification to gig owner
            try:
                subject = "GigHala - Gig Removed Due to Policy Violation"
                recipient_name = gig_owner.full_name or gig_owner.username

                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">GigHala</h1>
    </div>

    <div style="background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #dc2626; margin-top: 0;">Gig Removed - Terms and Conditions Breach</h2>

        <p>Dear {recipient_name},</p>

        <p>We are writing to inform you that your gig "<strong>{gig.title}</strong>" has been removed from GigHala by our administrative team.</p>

        <div style="background: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; color: #991b1b;">
                <strong>Reason:</strong> Your gig has breached the terms and conditions of GigHala.
            </p>
        </div>

        <p>This action was taken to maintain the integrity and safety of our platform. We take our community guidelines and terms of service very seriously.</p>

        <h3 style="color: #374151; margin-top: 25px;">What happens next?</h3>
        <ul style="color: #4b5563;">
            <li>Your gig has been permanently removed from the platform</li>
            <li>All associated applications and data have been deleted</li>
            <li>You may create new gigs if they comply with our terms and conditions</li>
        </ul>

        <p style="margin-top: 25px;">If you believe this action was taken in error, please contact our support team with details about your gig.</p>

        <div style="background: #e0e7ff; padding: 15px; margin: 25px 0; border-radius: 4px; text-align: center;">
            <p style="margin: 0; color: #3730a3;">
                <strong>Need Help?</strong><br>
                Please review our <a href="https://gighala.com/terms" style="color: #4f46e5;">Terms and Conditions</a> to ensure future gigs comply with our policies.
            </p>
        </div>

        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            Thank you for your understanding.<br>
            The GigHala Team
        </p>
    </div>

    <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="color: #9ca3af; font-size: 12px; margin: 5px 0;">
            © 2024 GigHala. All rights reserved.
        </p>
        <p style="color: #9ca3af; font-size: 12px; margin: 5px 0;">
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
</body>
</html>
"""

                text_content = f"""
GigHala - Gig Removed Due to Policy Violation

Dear {recipient_name},

We are writing to inform you that your gig "{gig.title}" has been removed from GigHala by our administrative team.

REASON: Your gig has breached the terms and conditions of GigHala.

This action was taken to maintain the integrity and safety of our platform. We take our community guidelines and terms of service very seriously.

What happens next?
- Your gig has been permanently removed from the platform
- All associated applications and data have been deleted
- You may create new gigs if they comply with our terms and conditions

If you believe this action was taken in error, please contact our support team with details about your gig.

Please review our Terms and Conditions at https://gighala.com/terms to ensure future gigs comply with our policies.

Thank you for your understanding.
The GigHala Team

---
© 2024 GigHala. All rights reserved.
This is an automated notification. Please do not reply to this email.
"""

                # Send the email
                email_sent = email_service.send_email(
                    to_email=gig_owner.email,
                    to_name=recipient_name,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )

                if email_sent:
                    app.logger.info(f"Breach notification email sent to {gig_owner.email} for deleted gig: {gig.title}")
                else:
                    app.logger.warning(f"Failed to send breach notification email to {gig_owner.email}")

            except Exception as email_error:
                # Log the error but don't stop the deletion process
                app.logger.error(f"Error sending breach notification email: {str(email_error)}")

        # Delete gig photos with file cleanup
        gig_photos = GigPhoto.query.filter_by(gig_id=gig_id).all()
        for photo in gig_photos:
            if photo.file_path and os.path.exists(photo.file_path):
                os.remove(photo.file_path)
            db.session.delete(photo)

        # Delete work photos with file cleanup
        work_photos = WorkPhoto.query.filter_by(gig_id=gig_id).all()
        for photo in work_photos:
            if photo.file_path and os.path.exists(photo.file_path):
                os.remove(photo.file_path)
            db.session.delete(photo)

        # Delete dispute messages (must be before disputes)
        disputes = Dispute.query.filter_by(gig_id=gig_id).all()
        for dispute in disputes:
            DisputeMessage.query.filter_by(dispute_id=dispute.id).delete()
            db.session.delete(dispute)

        # Delete reviews and recalculate affected user ratings
        reviews = Review.query.filter_by(gig_id=gig_id).all()
        affected_users = set()
        for review in reviews:
            affected_users.add(review.reviewee_id)
            db.session.delete(review)

        # Recalculate ratings for affected users
        for user_id in affected_users:
            recalculate_user_rating(user_id)

        # Delete milestones
        Milestone.query.filter_by(gig_id=gig_id).delete()

        # Delete invoices
        Invoice.query.filter_by(gig_id=gig_id).delete()

        # Delete transactions
        Transaction.query.filter_by(gig_id=gig_id).delete()

        # Delete escrow records
        Escrow.query.filter_by(gig_id=gig_id).delete()

        # Delete applications
        Application.query.filter_by(gig_id=gig_id).delete()

        # Finally delete the gig itself
        db.session.delete(gig)
        db.session.commit()

        return jsonify({'message': 'Gig and all associated data deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin delete gig error: {str(e)}")
        return jsonify({'error': 'Failed to delete gig'}), 500

@app.route('/api/admin/gigs/<int:gig_id>/block', methods=['POST'])
@admin_required
def admin_block_gig(gig_id):
    """Admin blocks a gig (soft delete)"""
    try:
        gig = Gig.query.get_or_404(gig_id)
        data = request.json or {}

        if gig.status == 'blocked':
            return jsonify({'error': 'Gig is already blocked'}), 400

        admin_id = session.get('user_id')
        block_reason = sanitize_input(data.get('reason', 'Blocked by admin'), max_length=1000)

        gig.status = 'blocked'
        gig.blocked_at = datetime.utcnow()
        gig.blocked_by = admin_id
        gig.block_reason = block_reason

        # Notify gig owner
        notification = Notification(
            user_id=gig.client_id,
            notification_type='admin',
            title='Gig Blocked by Admin',
            message=f'Your gig "{gig.title}" has been blocked. Reason: {block_reason}',
            link=f'/gig/{gig_id}',
            related_id=gig_id
        )
        db.session.add(notification)

        # Log security event
        from security_logger import log_security_event
        log_security_event(
            event_category='content_moderation',
            event_type='admin_block_gig',
            severity='high',
            user_id=admin_id,
            action='block',
            resource_type='gig',
            resource_id=gig_id,
            status='success',
            details={
                'gig_id': gig_id,
                'reason': block_reason
            }
        )

        db.session.commit()

        return jsonify({
            'message': 'Gig blocked successfully',
            'gig_id': gig_id,
            'blocked_at': gig.blocked_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin block gig error: {str(e)}")
        return jsonify({'error': 'Failed to block gig'}), 500

@app.route('/api/admin/gigs/<int:gig_id>/unblock', methods=['POST'])
@admin_required
def admin_unblock_gig(gig_id):
    """Admin unblocks a gig"""
    try:
        gig = Gig.query.get_or_404(gig_id)

        if gig.status != 'blocked':
            return jsonify({'error': 'Gig is not blocked'}), 400

        admin_id = session.get('user_id')

        # Restore to open status
        gig.status = 'open'
        gig.blocked_at = None
        gig.blocked_by = None
        gig.block_reason = None

        # Notify gig owner
        notification = Notification(
            user_id=gig.client_id,
            notification_type='admin',
            title='Gig Unblocked',
            message=f'Your gig "{gig.title}" has been reviewed and unblocked by an admin.',
            link=f'/gig/{gig_id}',
            related_id=gig_id
        )
        db.session.add(notification)

        # Log security event
        from security_logger import log_security_event
        log_security_event(
            event_category='content_moderation',
            event_type='admin_unblock_gig',
            severity='medium',
            user_id=admin_id,
            action='unblock',
            resource_type='gig',
            resource_id=gig_id,
            status='success',
            details={'gig_id': gig_id}
        )

        db.session.commit()

        return jsonify({
            'message': 'Gig unblocked successfully',
            'gig_id': gig_id
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin unblock gig error: {str(e)}")
        return jsonify({'error': 'Failed to unblock gig'}), 500

@app.route('/api/admin/reports', methods=['GET'])
@admin_required
def admin_get_reports():
    """Get all gig reports with filtering options"""
    try:
        # Query parameters
        status = request.args.get('status', '')  # pending, reviewed, dismissed, action_taken
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        query = GigReport.query

        # Filter by status
        if status:
            query = query.filter_by(status=status)

        # Order by creation date (newest first)
        query = query.order_by(GigReport.created_at.desc())

        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        reports = []
        for report in paginated.items:
            # Get gig details
            gig = Gig.query.get(report.gig_id)
            # Get reporter details
            reporter = User.query.get(report.reporter_id)
            # Get reviewer details if reviewed
            reviewer = User.query.get(report.reviewed_by) if report.reviewed_by else None

            reports.append({
                'id': report.id,
                'gig_id': report.gig_id,
                'gig_title': gig.title if gig else 'Deleted Gig',
                'gig_status': gig.status if gig else 'deleted',
                'reporter_id': report.reporter_id,
                'reporter_name': reporter.full_name or reporter.username if reporter else 'Unknown',
                'reason': report.reason,
                'description': report.description,
                'status': report.status,
                'reviewed_by': report.reviewed_by,
                'reviewer_name': reviewer.full_name or reviewer.username if reviewer else None,
                'reviewed_at': report.reviewed_at.isoformat() if report.reviewed_at else None,
                'admin_notes': report.admin_notes,
                'created_at': report.created_at.isoformat()
            })

        return jsonify({
            'reports': reports,
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'pages': paginated.pages
        }), 200

    except Exception as e:
        app.logger.error(f"Admin get reports error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve reports'}), 500

@app.route('/api/admin/reports/<int:report_id>', methods=['PUT'])
@admin_required
def admin_update_report(report_id):
    """Admin updates a report status"""
    try:
        report = GigReport.query.get_or_404(report_id)
        data = request.json or {}
        admin_id = session.get('user_id')

        # Update status
        new_status = data.get('status', '').strip()
        valid_statuses = ['pending', 'reviewed', 'dismissed', 'action_taken']
        if new_status and new_status in valid_statuses:
            report.status = new_status
            report.reviewed_by = admin_id
            report.reviewed_at = datetime.utcnow()

        # Update admin notes
        if 'admin_notes' in data:
            report.admin_notes = sanitize_input(data.get('admin_notes', ''), max_length=2000)

        db.session.commit()

        return jsonify({
            'message': 'Report updated successfully',
            'report_id': report_id,
            'status': report.status
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin update report error: {str(e)}")
        return jsonify({'error': 'Failed to update report'}), 500

# ==================== BILLING ROUTES ====================

@app.route('/billing')
@page_login_required
def billing_page():
    """Billing dashboard page"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    # Get wallet information for header display
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id)
        db.session.add(wallet)
        db.session.commit()

    # Get gig statistics for header display
    total_gigs_posted = Gig.query.filter_by(client_id=user_id).count() if user.user_type in ['client', 'both'] else 0

    # Count accepted gigs
    total_gigs_accepted = 0
    if user.user_type in ['freelancer', 'both']:
        total_gigs_accepted += Application.query.filter_by(freelancer_id=user_id, status='accepted').count()
    if user.user_type in ['client', 'both']:
        client_accepted = db.session.query(Application).join(
            Gig, Application.gig_id == Gig.id
        ).filter(
            Gig.client_id == user_id,
            Application.status == 'accepted'
        ).count()
        total_gigs_accepted += client_accepted

    return render_template('billing.html',
                         user=user,
                         wallet=wallet,
                         total_gigs_posted=total_gigs_posted,
                         total_gigs_accepted=total_gigs_accepted,
                         active_page='billing',
                         lang=get_user_language(),
                         t=t)

@app.route('/billing/socso-statement')
@page_login_required
def socso_statement():
    """SOCSO contribution statement for printing"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    # Get all SOCSO contributions for this user
    contributions = SocsoContribution.query.filter_by(
        freelancer_id=user_id
    ).order_by(SocsoContribution.created_at.desc()).all()

    # Calculate totals
    total_gross = sum(c.gross_amount for c in contributions)
    total_fees = sum(c.platform_commission for c in contributions)
    total_net = sum(c.net_earnings for c in contributions)
    total_socso = sum(c.socso_amount for c in contributions)

    # Get date range
    start_date = None
    end_date = None
    if contributions:
        start_date = contributions[-1].created_at.strftime('%d/%m/%Y')
        end_date = contributions[0].created_at.strftime('%d/%m/%Y')

    return render_template('socso_print_view.html',
                         user=user,
                         contributions=contributions,
                         total_gross=total_gross,
                         total_fees=total_fees,
                         total_net=total_net,
                         total_socso=total_socso,
                         start_date=start_date,
                         end_date=end_date,
                         active_page='billing',
                         lang=get_user_language(),
                         t=t)

@app.route('/api/billing/wallet', methods=['GET'])
@login_required
def get_wallet():
    """Get user's wallet information"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        wallet = Wallet.query.filter_by(user_id=user_id).first()

        # Create wallet if it doesn't exist
        if not wallet:
            wallet = Wallet(user_id=user_id)
            db.session.add(wallet)
            db.session.commit()

        return jsonify({
            'user_id': user_id,
            'user_type': user.user_type if user else None,
            'balance': wallet.balance,
            'held_balance': wallet.held_balance,
            'total_earned': wallet.total_earned,
            'total_spent': wallet.total_spent,
            'currency': wallet.currency,
            'available_balance': wallet.balance - wallet.held_balance
        }), 200
    except Exception as e:
        app.logger.error(f"Get wallet error: {str(e)}")
        return jsonify({'error': 'Failed to get wallet information'}), 500

@app.route('/api/billing/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user's transaction history"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        transaction_type = request.args.get('type', 'all')  # all, sent, received

        app.logger.info(f"GET /api/billing/transactions - user_id={user_id}, type={transaction_type}")

        # Build query
        if transaction_type == 'sent':
            query = Transaction.query.filter_by(client_id=user_id)
        elif transaction_type == 'received':
            query = Transaction.query.filter_by(freelancer_id=user_id)
        else:
            query = Transaction.query.filter(
                (Transaction.client_id == user_id) | (Transaction.freelancer_id == user_id)
            )

        total_count = query.count()
        app.logger.info(f"Found {total_count} total transactions for user {user_id}")

        pagination = query.order_by(Transaction.transaction_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        transactions = []
        for t in pagination.items:
            gig = Gig.query.get(t.gig_id)
            client = User.query.get(t.client_id)
            freelancer = User.query.get(t.freelancer_id)

            transactions.append({
                'id': t.id,
                'gig_id': t.gig_id,
                'client_id': t.client_id,
                'freelancer_id': t.freelancer_id,
                'gig_title': gig.title if gig else 'N/A',
                'client_name': client.username if client else 'N/A',
                'freelancer_name': freelancer.username if freelancer else 'N/A',
                'amount': t.amount,
                'commission': t.commission,
                'net_amount': t.net_amount,
                'payment_method': t.payment_method,
                'status': t.status,
                'transaction_date': t.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                'date': t.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'sent' if t.client_id == user_id else 'received'
            })

        app.logger.info(f"Returning {len(transactions)} transactions to frontend")
        return jsonify(transactions), 200
    except Exception as e:
        app.logger.error(f"Get transactions error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to get transactions'}), 500

@app.route('/api/billing/invoices', methods=['GET'])
@login_required
def get_invoices():
    """Get user's invoices"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', 'all')

        app.logger.info(f"GET /api/billing/invoices - user_id={user_id}, status={status}")

        # Build query
        query = Invoice.query.filter(
            (Invoice.client_id == user_id) | (Invoice.freelancer_id == user_id)
        )

        if status != 'all':
            query = query.filter_by(status=status)

        total_count = query.count()
        app.logger.info(f"Found {total_count} total invoices for user {user_id}")

        pagination = query.order_by(Invoice.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        invoices = []
        for inv in pagination.items:
            gig = Gig.query.get(inv.gig_id)
            client = User.query.get(inv.client_id)
            freelancer = User.query.get(inv.freelancer_id)

            invoices.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'gig_id': inv.gig_id,
                'gig_title': gig.title if gig else 'N/A',
                'gig_code': gig.gig_code if gig else None,
                'client_id': inv.client_id,
                'client_name': client.username if client else 'N/A',
                'freelancer_id': inv.freelancer_id,
                'freelancer_name': freelancer.username if freelancer else 'N/A',
                'amount': inv.amount,
                'platform_fee': inv.platform_fee,
                'tax_amount': inv.tax_amount,
                'total_amount': inv.total_amount,
                'status': inv.status,
                'payment_method': inv.payment_method,
                'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'issue_date': inv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'paid_at': inv.paid_at.strftime('%Y-%m-%d %H:%M:%S') if inv.paid_at else None,
                'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else None,
                'role': 'client' if inv.client_id == user_id else 'freelancer'
            })

        app.logger.info(f"Returning {len(invoices)} invoices to frontend")
        return jsonify(invoices), 200
    except Exception as e:
        app.logger.error(f"Get invoices error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to get invoices'}), 500

@app.route('/api/billing/payouts', methods=['GET'])
@login_required
def get_payouts():
    """Get user's payout history"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        app.logger.info(f"GET /api/billing/payouts - user_id={user_id}")

        total_count = Payout.query.filter_by(freelancer_id=user_id).count()
        app.logger.info(f"Found {total_count} total payouts for user {user_id}")

        pagination = Payout.query.filter_by(freelancer_id=user_id).order_by(
            Payout.requested_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        payouts = []
        for p in pagination.items:
            payouts.append({
                'id': p.id,
                'payout_number': p.payout_number,
                'amount': p.amount,
                'fee': p.fee,
                'net_amount': p.net_amount,
                'payment_method': p.payment_method,
                'payout_method': p.payment_method,  # Alias for frontend compatibility
                'bank_name': p.bank_name,
                'account_number': p.account_number[-4:] if p.account_number else None,  # Last 4 digits
                'status': p.status,
                'requested_at': p.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': p.completed_at.strftime('%Y-%m-%d %H:%M:%S') if p.completed_at else None,
                'failure_reason': p.failure_reason
            })

        app.logger.info(f"Returning {len(payouts)} payouts to frontend")
        return jsonify(payouts), 200
    except Exception as e:
        app.logger.error(f"Get payouts error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to get payouts'}), 500

@app.route('/api/billing/payouts', methods=['POST'])
@login_required
def request_payout():
    """Request a payout withdrawal from wallet balance (NO SOCSO deduction on payout - SOCSO deducted on escrow release)"""
    try:
        user_id = session['user_id']
        data = request.get_json()

        amount = data.get('amount')
        payment_method = data.get('payment_method')
        account_number = data.get('account_number')
        account_name = data.get('account_name')
        bank_name = data.get('bank_name')

        # Validate
        if not all([amount, payment_method, account_number, account_name]):
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid amount format'}), 400

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check wallet balance
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet or wallet.balance < amount:
            return jsonify({'error': 'Insufficient balance'}), 400

        # ALLOW multiple pending payouts - removing restriction if it existed
        # Based on user feedback "stuck with one payout", I'll ensure we don't block additional requests
        app.logger.info(f"User {user_id} requesting payout of {amount}. Current balance: {wallet.balance}")
        
        # Calculate fee (2% platform fee only - NO SOCSO deduction here)
        # SOCSO is deducted only when client releases escrow, not on payout withdrawal
        fee = round(amount * 0.02, 2)

        # Net amount after fee deduction only (SOCSO already deducted at escrow release)
        net_amount = round(amount - fee, 2)

        # Generate payout number
        import random
        payout_number = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

        # Create payout request
        payout = Payout(
            payout_number=payout_number,
            freelancer_id=user_id,
            amount=amount,
            fee=fee,
            socso_amount=0.0,  # NO SOCSO deduction on payout - already deducted at escrow release
            net_amount=net_amount,
            payment_method=payment_method,
            account_number=account_number,
            account_name=account_name,
            bank_name=bank_name,
            status='pending'
        )

        db.session.add(payout)
        db.session.flush()  # Get payout ID

        # Hold the balance
        wallet.balance -= amount
        wallet.held_balance += amount

        # Create payment history for hold
        history = PaymentHistory(
            user_id=user_id,
            payout_id=payout.id,
            type='hold',
            amount=amount,
            socso_amount=0.0,  # NO SOCSO on payout
            balance_before=wallet.balance + amount,
            balance_after=wallet.balance,
            description=f'Payout request {payout_number} (SOCSO already deducted at escrow release)'
        )

        db.session.add(history)
        db.session.commit()

        # Log financial operation
        security_logger.log_financial(
            event_type='payout_requested',
            action=f'Payout request submitted by {user.username}',
            amount=amount,
            resource_type='payout',
            resource_id=payout_number,
            details={
                'payout_number': payout_number,
                'amount': amount,
                'fee': fee,
                'net_amount': net_amount,
                'payment_method': payment_method,
                'wallet_balance_before': wallet.balance + amount,
                'wallet_balance_after': wallet.balance
            }
        )

        return jsonify({
            'message': 'Payout request submitted successfully',
            'payout_number': payout_number,
            'status': 'pending',
            'amount': amount,
            'fee': fee,
            'socso_amount': 0.0,
            'net_amount': net_amount,
            'breakdown': {
                'gross_amount': amount,
                'platform_fee': fee,
                'socso_contribution': 0.0,
                'final_payout': net_amount
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Request payout error: {str(e)}")
        return jsonify({'error': 'Failed to request payout'}), 500

@app.route('/api/billing/payment-history', methods=['GET'])
@login_required
def get_payment_history():
    """Get detailed payment history"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        pagination = PaymentHistory.query.filter_by(user_id=user_id).order_by(
            PaymentHistory.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        history = []
        for h in pagination.items:
            history.append({
                'id': h.id,
                'type': h.type,
                'amount': h.amount,
                'balance_before': h.balance_before,
                'balance_after': h.balance_after,
                'description': h.description,
                'reference_number': h.reference_number,
                'created_at': h.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify({
            'history': history,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        }), 200
    except Exception as e:
        app.logger.error(f"Get payment history error: {str(e)}")
        return jsonify({'error': 'Failed to get payment history'}), 500

@app.route('/api/billing/socso-contributions', methods=['GET'])
@login_required
def get_socso_contributions():
    """Get freelancer's SOCSO contribution history (Gig Workers Bill 2025)"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if not user or user.user_type not in ['freelancer', 'both']:
            return jsonify({'error': 'Only freelancers can view SOCSO contributions'}), 403

        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)

        # Build query
        query = SocsoContribution.query.filter_by(freelancer_id=user_id)

        # Filter by year/month if provided
        if year:
            query = query.filter_by(contribution_year=year)
        if month and year:
            contribution_month = f"{year}-{month:02d}"
            query = query.filter_by(contribution_month=contribution_month)

        # Order by most recent first
        query = query.order_by(SocsoContribution.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Format contributions
        contributions = []
        for contrib in pagination.items:
            contributions.append({
                'id': contrib.id,
                'gig_id': contrib.gig_id,
                'gross_amount': contrib.gross_amount,
                'platform_commission': contrib.platform_commission,
                'net_earnings': contrib.net_earnings,
                'socso_amount': contrib.socso_amount,
                'final_payout': contrib.final_payout,
                'contribution_month': contrib.contribution_month,
                'contribution_year': contrib.contribution_year,
                'contribution_type': contrib.contribution_type,
                'remitted_to_socso': contrib.remitted_to_socso,
                'remittance_date': contrib.remittance_date.isoformat() if contrib.remittance_date else None,
                'created_at': contrib.created_at.isoformat() if contrib.created_at else None
            })

        # Calculate totals
        total_query = SocsoContribution.query.filter_by(freelancer_id=user_id)
        if year:
            total_query = total_query.filter_by(contribution_year=year)
        if month and year:
            contribution_month = f"{year}-{month:02d}"
            total_query = total_query.filter_by(contribution_month=contribution_month)

        totals = db.session.query(
            db.func.sum(SocsoContribution.socso_amount).label('total_socso'),
            db.func.sum(SocsoContribution.net_earnings).label('total_net_earnings'),
            db.func.sum(SocsoContribution.final_payout).label('total_final_payout'),
            db.func.count(SocsoContribution.id).label('transaction_count')
        ).filter(SocsoContribution.freelancer_id == user_id)

        if year:
            totals = totals.filter(SocsoContribution.contribution_year == year)
        if month and year:
            totals = totals.filter(SocsoContribution.contribution_month == contribution_month)

        totals_result = totals.first()

        return jsonify({
            'contributions': contributions,
            'pagination': {
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': pagination.page,
                'per_page': pagination.per_page
            },
            'totals': {
                'total_socso': float(totals_result.total_socso or 0),
                'total_net_earnings': float(totals_result.total_net_earnings or 0),
                'total_final_payout': float(totals_result.total_final_payout or 0),
                'transaction_count': totals_result.transaction_count or 0
            },
            'user_info': {
                'socso_consent': user.socso_consent,
                'socso_consent_date': user.socso_consent_date.isoformat() if user.socso_consent_date else None,
                'ic_number': user.ic_number
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Get SOCSO contributions error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to get SOCSO contributions'}), 500

@app.route('/api/billing/socso-monthly-breakdown', methods=['GET'])
@login_required
def get_socso_monthly_breakdown():
    """Get worker's monthly SOCSO contribution breakdown"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user or user.user_type not in ['freelancer', 'both']:
            return jsonify({'error': 'Only freelancers can view SOCSO contributions'}), 403
        
        # Get last 12 months of SOCSO data grouped by month
        monthly_data = db.session.query(
            SocsoContribution.contribution_month,
            db.func.count(SocsoContribution.id).label('transaction_count'),
            db.func.sum(SocsoContribution.gross_amount).label('total_gross'),
            db.func.sum(SocsoContribution.net_earnings).label('total_net'),
            db.func.sum(SocsoContribution.socso_amount).label('total_socso'),
            db.func.sum(SocsoContribution.final_payout).label('total_payout')
        ).filter(SocsoContribution.freelancer_id == user_id).group_by(
            SocsoContribution.contribution_month
        ).order_by(SocsoContribution.contribution_month.desc()).limit(12).all()
        
        breakdown = []
        for month_data in monthly_data:
            breakdown.append({
                'month': month_data.contribution_month,
                'transaction_count': month_data.transaction_count,
                'total_gross': float(month_data.total_gross or 0),
                'total_net': float(month_data.total_net or 0),
                'total_socso': float(month_data.total_socso or 0),
                'total_payout': float(month_data.total_payout or 0)
            })
        
        return jsonify({'monthly_breakdown': breakdown}), 200
    except Exception as e:
        app.logger.error(f"Get monthly SOCSO breakdown error: {str(e)}")
        return jsonify({'error': 'Failed to get monthly breakdown'}), 500

@app.route('/api/dashboard/socso-deductions', methods=['GET'])
@login_required
def get_dashboard_socso_deductions():
    """Get recent SOCSO deductions for dashboard (when client releases escrow)"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        
        if not user or user.user_type not in ['freelancer', 'both']:
            return jsonify({'error': 'Only freelancers can view SOCSO deductions'}), 403
        
        # Get last 5 SOCSO deductions from escrow releases
        deductions = db.session.query(
            SocsoContribution.id,
            SocsoContribution.gig_id,
            SocsoContribution.socso_amount,
            SocsoContribution.net_earnings,
            SocsoContribution.final_payout,
            SocsoContribution.created_at,
            Gig.title.label('gig_title')
        ).outerjoin(Gig, SocsoContribution.gig_id == Gig.id)\
         .filter(
             SocsoContribution.freelancer_id == user_id,
             SocsoContribution.contribution_type == 'escrow_release'
         ).order_by(SocsoContribution.created_at.desc()).limit(5).all()
        
        items = []
        for deduction in deductions:
            items.append({
                'id': deduction.id,
                'gig_id': deduction.gig_id,
                'gig_title': deduction.gig_title or 'Unknown Gig',
                'socso_amount': float(deduction.socso_amount),
                'net_earnings': float(deduction.net_earnings),
                'final_payout': float(deduction.final_payout),
                'created_at': deduction.created_at.isoformat()
            })
        
        return jsonify({'socso_deductions': items}), 200
    except Exception as e:
        app.logger.error(f"Get dashboard SOCSO deductions error: {str(e)}")
        return jsonify({'error': 'Failed to get SOCSO deductions'}), 500

@app.route('/api/admin/socso/monthly-report', methods=['GET'])
@admin_required
def admin_socso_monthly_report():
    """
    Admin endpoint: Generate monthly SOCSO report for ASSIST Portal bulk upload
    Supports CSV export for SOCSO remittance compliance (Gig Workers Bill 2025)
    """
    try:
        # Get query parameters
        year = request.args.get('year', datetime.utcnow().year, type=int)
        month = request.args.get('month', type=int)  # Optional
        export_format = request.args.get('format', 'json')  # json or csv

        # Build query
        query = db.session.query(
            SocsoContribution.contribution_month,
            SocsoContribution.contribution_year,
            User.id.label('freelancer_id'),
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.email,
            User.phone,
            db.func.count(SocsoContribution.id).label('transaction_count'),
            db.func.sum(SocsoContribution.net_earnings).label('total_net_earnings'),
            db.func.sum(SocsoContribution.socso_amount).label('total_socso_amount'),
            db.func.sum(SocsoContribution.final_payout).label('total_final_payout'),
            db.func.bool_and(SocsoContribution.remitted_to_socso).label('all_remitted'),
            db.func.max(SocsoContribution.remittance_date).label('last_remittance_date')
        ).join(User, SocsoContribution.freelancer_id == User.id)\
         .filter(SocsoContribution.contribution_year == year)

        if month:
            contribution_month = f"{year}-{month:02d}"
            query = query.filter(SocsoContribution.contribution_month == contribution_month)

        query = query.group_by(
            SocsoContribution.contribution_month,
            SocsoContribution.contribution_year,
            User.id,
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.email,
            User.phone
        ).order_by(
            SocsoContribution.contribution_year.desc(),
            SocsoContribution.contribution_month.desc(),
            User.full_name
        )

        results = query.all()

        # Format results
        report_data = []
        for row in results:
            report_data.append({
                'contribution_month': row.contribution_month,
                'contribution_year': row.contribution_year,
                'freelancer_id': row.freelancer_id,
                'full_name': row.full_name,
                'ic_number': row.ic_number,
                'socso_membership_number': row.socso_membership_number,
                'email': row.email,
                'phone': row.phone,
                'transaction_count': row.transaction_count,
                'total_net_earnings': float(row.total_net_earnings or 0),
                'total_socso_amount': float(row.total_socso_amount or 0),
                'total_final_payout': float(row.total_final_payout or 0),
                'all_remitted': row.all_remitted or False,
                'last_remittance_date': row.last_remittance_date.isoformat() if row.last_remittance_date else None
            })

        # Calculate grand totals
        grand_totals = {
            'total_freelancers': len(report_data),
            'total_transactions': sum(r['transaction_count'] for r in report_data),
            'total_net_earnings': sum(r['total_net_earnings'] for r in report_data),
            'total_socso_amount': sum(r['total_socso_amount'] for r in report_data),
            'total_final_payout': sum(r['total_final_payout'] for r in report_data)
        }

        # Export as CSV if requested
        if export_format == 'csv':
            import io
            import csv
            from flask import make_response

            output = io.StringIO()
            writer = csv.writer(output)

            # CSV Headers for ASSIST Portal bulk upload
            writer.writerow([
                'Month',
                'Year',
                'IC Number',
                'SOCSO Membership Number',
                'Full Name',
                'Email',
                'Phone',
                'Transaction Count',
                'Total Net Earnings (MYR)',
                'SOCSO Contribution (MYR)',
                'Final Payout (MYR)',
                'Remitted to SOCSO'
            ])

            # Data rows
            for row in report_data:
                writer.writerow([
                    row['contribution_month'],
                    row['contribution_year'],
                    row['ic_number'],
                    row['socso_membership_number'] or '',
                    row['full_name'],
                    row['email'],
                    row['phone'],
                    row['transaction_count'],
                    f"{row['total_net_earnings']:.2f}",
                    f"{row['total_socso_amount']:.2f}",
                    f"{row['total_final_payout']:.2f}",
                    'Yes' if row['all_remitted'] else 'No'
                ])

            # Add summary row
            writer.writerow([])
            writer.writerow(['SUMMARY'])
            writer.writerow(['Total Freelancers', grand_totals['total_freelancers']])
            writer.writerow(['Total Transactions', grand_totals['total_transactions']])
            writer.writerow(['Total SOCSO Collected (MYR)', f"{grand_totals['total_socso_amount']:.2f}"])

            # Create response
            csv_output = output.getvalue()
            response = make_response(csv_output)
            filename = f"socso_report_{year}"
            if month:
                filename += f"_{month:02d}"
            filename += ".csv"

            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            response.headers['Content-Type'] = 'text/csv'
            return response

        # Return JSON
        return jsonify({
            'report': report_data,
            'totals': grand_totals,
            'filters': {
                'year': year,
                'month': month
            }
        }), 200

    except Exception as e:
        app.logger.error(f"Admin SOCSO monthly report error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to generate SOCSO report'}), 500

@app.route('/api/admin/socso/user-totals', methods=['GET'])
@admin_required
def admin_socso_user_totals():
    """
    Admin endpoint: Get SOCSO payment totals per user for specified period
    Supports 1 month, 6 months, or 12 months lookback
    """
    try:
        # Get period parameter (default 1 month)
        period = request.args.get('period', 1, type=int)

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period * 30)  # Approximate months

        # Build query
        query = db.session.query(
            User.id.label('freelancer_id'),
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.email,
            User.phone,
            db.func.count(SocsoContribution.id).label('transaction_count'),
            db.func.sum(SocsoContribution.net_earnings).label('total_net_earnings'),
            db.func.sum(SocsoContribution.socso_amount).label('total_socso'),
            db.func.sum(SocsoContribution.final_payout).label('total_final_payout'),
            db.func.bool_and(SocsoContribution.remitted_to_socso).label('all_remitted'),
            db.func.max(SocsoContribution.remittance_date).label('last_remittance_date')
        ).join(SocsoContribution, User.id == SocsoContribution.freelancer_id)\
         .filter(SocsoContribution.created_at >= start_date)\
         .filter(SocsoContribution.created_at <= end_date)\
         .group_by(
            User.id,
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.email,
            User.phone
        ).order_by(
            db.func.sum(SocsoContribution.socso_amount).desc()
        )

        results = query.all()

        # Format results
        totals_data = []
        for row in results:
            totals_data.append({
                'freelancer_id': row.freelancer_id,
                'full_name': row.full_name,
                'ic_number': row.ic_number,
                'socso_membership_number': row.socso_membership_number,
                'email': row.email,
                'phone': row.phone,
                'transaction_count': row.transaction_count,
                'total_net_earnings': float(row.total_net_earnings or 0),
                'total_socso': float(row.total_socso or 0),
                'total_final_payout': float(row.total_final_payout or 0),
                'all_remitted': row.all_remitted or False,
                'last_remittance_date': row.last_remittance_date.isoformat() if row.last_remittance_date else None
            })

        # Calculate grand totals
        grand_totals = {
            'total_users': len(totals_data),
            'total_transactions': sum(r['transaction_count'] for r in totals_data),
            'total_net_earnings': sum(r['total_net_earnings'] for r in totals_data),
            'total_socso': sum(r['total_socso'] for r in totals_data),
            'total_final_payout': sum(r['total_final_payout'] for r in totals_data)
        }

        return jsonify({
            'totals': totals_data,
            'summary': grand_totals,
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }), 200

    except Exception as e:
        app.logger.error(f"Admin SOCSO user totals error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to load SOCSO user totals'}), 500

@app.route('/api/admin/socso/user-totals/export', methods=['GET'])
@admin_required
def admin_socso_user_totals_export():
    """
    Admin endpoint: Export SOCSO user totals as CSV
    """
    try:
        # Get period parameter (default 1 month)
        period = request.args.get('period', 1, type=int)

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period * 30)

        # Build query
        query = db.session.query(
            User.id.label('freelancer_id'),
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.email,
            User.phone,
            db.func.count(SocsoContribution.id).label('transaction_count'),
            db.func.sum(SocsoContribution.net_earnings).label('total_net_earnings'),
            db.func.sum(SocsoContribution.socso_amount).label('total_socso'),
            db.func.sum(SocsoContribution.final_payout).label('total_final_payout'),
            db.func.bool_and(SocsoContribution.remitted_to_socso).label('all_remitted')
        ).join(SocsoContribution, User.id == SocsoContribution.freelancer_id)\
         .filter(SocsoContribution.created_at >= start_date)\
         .filter(SocsoContribution.created_at <= end_date)\
         .group_by(
            User.id,
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.email,
            User.phone
        ).order_by(
            db.func.sum(SocsoContribution.socso_amount).desc()
        )

        results = query.all()

        import io
        import csv
        from flask import make_response

        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Headers
        writer.writerow([
            'IC Number',
            'SOCSO Membership Number',
            'Full Name',
            'Email',
            'Phone',
            'Transaction Count',
            'Total Net Earnings (MYR)',
            'Total SOCSO (MYR)',
            'Total Final Payout (MYR)',
            'All Remitted'
        ])

        # Data rows
        total_socso = 0
        for row in results:
            total_socso += float(row.total_socso or 0)
            writer.writerow([
                row.ic_number,
                row.socso_membership_number or '',
                row.full_name,
                row.email,
                row.phone,
                row.transaction_count,
                f"{float(row.total_net_earnings or 0):.2f}",
                f"{float(row.total_socso or 0):.2f}",
                f"{float(row.total_final_payout or 0):.2f}",
                'Yes' if row.all_remitted else 'No'
            ])

        # Add summary row
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Total Users', len(results)])
        writer.writerow(['Total SOCSO Collected (MYR)', f"{total_socso:.2f}"])
        writer.writerow(['Period (Months)', period])

        # Create response
        csv_output = output.getvalue()
        response = make_response(csv_output)
        filename = f"socso_user_totals_{period}months_{end_date.strftime('%Y%m%d')}.csv"

        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = 'text/csv'
        return response

    except Exception as e:
        app.logger.error(f"Admin SOCSO user totals export error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to export SOCSO user totals'}), 500

@app.route('/api/admin/socso/mark-remitted', methods=['POST'])
@admin_required
def admin_mark_socso_remitted():
    """Admin endpoint: Mark SOCSO contributions as remitted to ASSIST Portal"""
    try:
        data = request.get_json()
        contribution_ids = data.get('contribution_ids', [])
        remittance_reference = data.get('remittance_reference')
        remittance_batch_id = data.get('remittance_batch_id')

        if not contribution_ids:
            return jsonify({'error': 'No contribution IDs provided'}), 400

        # Update contributions
        updated_count = 0
        for contrib_id in contribution_ids:
            contrib = SocsoContribution.query.get(contrib_id)
            if contrib:
                contrib.remitted_to_socso = True
                contrib.remittance_date = datetime.utcnow()
                contrib.remittance_reference = remittance_reference
                contrib.remittance_batch_id = remittance_batch_id
                updated_count += 1

        db.session.commit()

        return jsonify({
            'message': f'Marked {updated_count} contributions as remitted',
            'updated_count': updated_count
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Mark SOCSO remitted error: {str(e)}")
        return jsonify({'error': 'Failed to mark contributions as remitted'}), 500

@app.route('/api/admin/socso/borang-8a', methods=['GET'])
@admin_required
def admin_generate_borang_8a():
    """
    Admin endpoint: Generate SOCSO Borang 8A (Monthly Contribution Report)

    This generates the official SOCSO Form 8A for monthly submission to PERKESO
    via the ASSIST Portal. Must be submitted by the 15th of each month.

    Query Parameters:
    - year (int): Contribution year (default: current year)
    - month (int): Contribution month 1-12 (default: previous month)
    - format (str): 'json', 'txt', or 'html' (default: 'json')

    Text File Format (for ASSIST Portal upload):
    Fixed-width format with fields: Employer Code, SSM Number, IC Number,
    Employee Name, Contribution Month, Contribution Amount, Employment Date, Status
    """
    try:
        # Get query parameters
        current_date = datetime.utcnow()
        year = request.args.get('year', current_date.year, type=int)
        month = request.args.get('month', type=int)

        # Default to previous month if not specified
        if not month:
            if current_date.month == 1:
                month = 12
                year = current_date.year - 1
            else:
                month = current_date.month - 1

        export_format = request.args.get('format', 'json')  # json, txt, or html

        # Get employer settings
        employer_code = get_site_setting('socso_employer_code', '')
        ssm_number = get_site_setting('socso_ssm_number', '')
        company_name = get_site_setting('socso_company_name', 'GigHala Sdn Bhd')
        company_address = get_site_setting('socso_company_address', '')
        company_phone = get_site_setting('socso_company_phone', '')
        company_email = get_site_setting('socso_company_email', 'compliance@gighala.com')

        # Validate required settings
        if not employer_code or not ssm_number:
            return jsonify({
                'error': 'Employer SOCSO settings incomplete',
                'message': 'Please configure SOCSO Employer Code and SSM Number in settings',
                'missing': {
                    'employer_code': not employer_code,
                    'ssm_number': not ssm_number
                }
            }), 400

        # Build query for monthly contributions
        contribution_month = f"{year}-{month:02d}"

        # Get all workers with contributions for this month
        # Group by worker to get total monthly contribution
        query = db.session.query(
            User.id.label('freelancer_id'),
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.created_at.label('employment_date'),
            db.func.sum(SocsoContribution.socso_amount).label('total_contribution'),
            db.func.sum(SocsoContribution.net_earnings).label('total_wages'),
            db.func.count(SocsoContribution.id).label('transaction_count'),
            db.func.min(SocsoContribution.created_at).label('first_contribution_date')
        ).join(User, SocsoContribution.freelancer_id == User.id)\
         .filter(SocsoContribution.contribution_month == contribution_month)\
         .group_by(
            User.id,
            User.full_name,
            User.ic_number,
            User.socso_membership_number,
            User.created_at
        ).order_by(User.full_name)

        results = query.all()

        if not results:
            return jsonify({
                'error': 'No SOCSO contributions found',
                'message': f'No contributions found for {contribution_month}',
                'year': year,
                'month': month
            }), 404

        # Format employee data
        employees = []
        total_contribution = 0
        total_wages = 0

        for row in results:
            # Determine employment status
            # B = New (first contribution this month)
            # H = Terminated (future: need termination tracking)
            # Blank = Existing employee
            employment_status = ''

            # Check if this is their first ever contribution
            first_ever = SocsoContribution.query.filter_by(
                freelancer_id=row.freelancer_id
            ).order_by(SocsoContribution.created_at.asc()).first()

            if first_ever and first_ever.contribution_month == contribution_month:
                employment_status = 'B'  # New employee

            employee_data = {
                'ic_number': row.ic_number or '',
                'socso_number': row.socso_membership_number or '',
                'full_name': row.full_name or 'Unknown',
                'employment_date': row.employment_date.strftime('%Y-%m-%d') if row.employment_date else '',
                'monthly_wages': float(row.total_wages or 0),
                'contribution_amount': float(row.total_contribution or 0),
                'employment_status': employment_status,
                'transaction_count': row.transaction_count
            }

            employees.append(employee_data)
            total_contribution += employee_data['contribution_amount']
            total_wages += employee_data['monthly_wages']

        # Prepare Borang 8A data
        borang_8a_data = {
            'form_info': {
                'form_name': 'Borang 8A - Senarai Pekerja dan Caruman Bulanan',
                'form_name_en': 'Form 8A - Monthly List of Employees and Contributions',
                'submission_deadline': f'15th of {calendar.month_name[(month % 12) + 1]} {year if month < 12 else year + 1}'
            },
            'employer': {
                'employer_code': employer_code,
                'ssm_number': ssm_number,
                'company_name': company_name,
                'company_address': company_address,
                'company_phone': company_phone,
                'company_email': company_email
            },
            'period': {
                'month': month,
                'year': year,
                'month_name': calendar.month_name[month],
                'contribution_month': contribution_month
            },
            'employees': employees,
            'summary': {
                'total_employees': len(employees),
                'total_wages': round(total_wages, 2),
                'total_contribution': round(total_contribution, 2),
                'new_employees': len([e for e in employees if e['employment_status'] == 'B']),
                'terminated_employees': len([e for e in employees if e['employment_status'] == 'H'])
            },
            'generated_at': current_date.isoformat(),
            'generated_by': session.get('username', 'admin')
        }

        # Export as Text File for ASSIST Portal
        if export_format == 'txt':
            import io
            from flask import make_response

            output = io.StringIO()

            # PERKESO Text File Format (fixed-width fields)
            # Note: This is a standard format based on PERKESO specifications
            # Field positions may need adjustment based on actual PERKESO requirements

            # Header line (optional, for reference)
            output.write(f"# Borang 8A - {company_name}\n")
            output.write(f"# Period: {borang_8a_data['period']['month_name']} {year}\n")
            output.write(f"# Employer Code: {employer_code}\n")
            output.write(f"# SSM Number: {ssm_number}\n")
            output.write("#\n")

            # Employee records
            for emp in employees:
                # Format: Employer Code | SSM | IC Number | Name | Month | Contribution | Employment Date | Status
                # Using pipe-delimited format for clarity (PERKESO may require specific fixed-width)
                line = "|".join([
                    employer_code.ljust(15),
                    ssm_number.ljust(20),
                    emp['ic_number'].ljust(20),
                    emp['full_name'][:60].ljust(60),
                    contribution_month.ljust(7),
                    f"{emp['contribution_amount']:.2f}".rjust(10),
                    f"{emp['monthly_wages']:.2f}".rjust(12),
                    emp['employment_date'].ljust(10),
                    emp['employment_status'].ljust(1)
                ])
                output.write(line + "\n")

            # Create response
            txt_output = output.getvalue()
            response = make_response(txt_output)
            filename = f"borang_8a_{year}_{month:02d}.txt"

            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            response.headers['Content-Type'] = 'text/plain; charset=utf-8'

            # Update last submission date
            set_site_setting('socso_last_submission_date', current_date.isoformat())

            return response

        # Export as HTML (printable format)
        elif export_format == 'html':
            return render_template(
                'borang_8a_print.html',
                data=borang_8a_data,
                lang=session.get('language', 'en')
            )

        # Return JSON (default)
        return jsonify(borang_8a_data), 200

    except Exception as e:
        app.logger.error(f"Generate Borang 8A error: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to generate Borang 8A', 'details': str(e)}), 500

@app.route('/api/billing/complete-gig/<int:gig_id>', methods=['POST'])
@login_required
def complete_gig_transaction(gig_id):
    """
    Complete a gig and create transaction/invoice with tiered commission
    Only the client can mark a gig as complete
    """
    try:
        user_id = session['user_id']
        data = request.get_json()

        # Get the gig
        gig = Gig.query.get_or_404(gig_id)

        # Verify the user is the client
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can complete this gig'}), 403

        # Verify gig has a freelancer assigned
        if not gig.freelancer_id:
            return jsonify({'error': 'No freelancer assigned to this gig'}), 400

        # Verify gig is in progress
        if gig.status != 'in_progress':
            return jsonify({'error': 'Gig must be in progress to complete'}), 400

        # Get payment details
        amount = data.get('amount')
        payment_method = data.get('payment_method', 'bank_transfer')

        if not amount or amount <= 0:
            return jsonify({'error': 'Invalid payment amount'}), 400

        # Calculate commission using tiered structure
        commission = calculate_commission(amount)
        net_amount = amount - commission

        # Generate invoice number
        import random
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

        # Create transaction
        transaction = Transaction(
            gig_id=gig_id,
            freelancer_id=gig.freelancer_id,
            client_id=gig.client_id,
            amount=amount,
            commission=commission,
            net_amount=net_amount,
            payment_method=payment_method,
            status='completed'
        )
        db.session.add(transaction)
        db.session.flush()  # Get transaction ID

        # Check if invoice already exists (auto-generated on completion)
        invoice = Invoice.query.filter_by(gig_id=gig_id).first()

        if invoice:
            # Update existing invoice to mark as paid
            invoice.status = 'paid'
            invoice.paid_at = datetime.utcnow()
            invoice.payment_method = payment_method
            invoice.transaction_id = transaction.id
            invoice_number = invoice.invoice_number
        else:
            # Create new invoice if it doesn't exist
            invoice = Invoice(
                invoice_number=invoice_number,
                transaction_id=transaction.id,
                gig_id=gig_id,
                client_id=gig.client_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=commission,
                tax_amount=0.0,
                total_amount=amount,
                status='paid',
                payment_method=payment_method,
                paid_at=datetime.utcnow(),
                notes=f'Payment for: {gig.title}'
            )
            db.session.add(invoice)

        # Update or create freelancer wallet
        freelancer_wallet = Wallet.query.filter_by(user_id=gig.freelancer_id).first()
        if not freelancer_wallet:
            freelancer_wallet = Wallet(user_id=gig.freelancer_id)
            db.session.add(freelancer_wallet)
            db.session.flush()

        # Update wallet balances
        old_balance = freelancer_wallet.balance
        freelancer_wallet.balance += net_amount
        freelancer_wallet.total_earned += net_amount

        # Create payment history for freelancer (earning)
        freelancer_history = PaymentHistory(
            user_id=gig.freelancer_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            type='payment',
            amount=net_amount,
            balance_before=old_balance,
            balance_after=freelancer_wallet.balance,
            description=f'Payment received for: {gig.title}',
            reference_number=invoice_number
        )
        db.session.add(freelancer_history)

        # Update or create client wallet
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        if not client_wallet:
            client_wallet = Wallet(user_id=gig.client_id)
            db.session.add(client_wallet)
            db.session.flush()

        # Update client wallet
        client_old_balance = client_wallet.balance
        client_wallet.total_spent += amount

        # Create payment history for client (payment made)
        client_history = PaymentHistory(
            user_id=gig.client_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            type='payment',
            amount=amount,
            balance_before=client_old_balance,
            balance_after=client_wallet.balance,
            description=f'Payment made for: {gig.title}',
            reference_number=invoice_number
        )
        db.session.add(client_history)

        # Update gig status
        gig.status = 'completed'

        # Update freelancer stats
        freelancer = User.query.get(gig.freelancer_id)
        if freelancer:
            freelancer.completed_gigs = (freelancer.completed_gigs or 0) + 1
            freelancer.total_earnings = (freelancer.total_earnings or 0) + net_amount

        db.session.commit()

        return jsonify({
            'message': 'Gig completed successfully',
            'invoice_number': invoice_number,
            'transaction_id': transaction.id,
            'amount': amount,
            'commission': commission,
            'net_amount': net_amount,
            'freelancer_receives': net_amount
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Complete gig transaction error: {str(e)}")
        return jsonify({'error': 'Failed to complete transaction'}), 500

@app.route('/api/gigs/<int:gig_id>/approve-and-pay', methods=['POST'])
@login_required
def approve_and_pay_gig(gig_id):
    """
    Automatically approve gig completion and process payment
    Uses the accepted application's proposed price
    Client just needs to call this endpoint - payment is automatic
    """
    try:
        user_id = session['user_id']

        # Get the gig
        gig = Gig.query.get_or_404(gig_id)

        # Verify the user is the client
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can approve this gig'}), 403

        # Verify gig has a freelancer assigned
        if not gig.freelancer_id:
            return jsonify({'error': 'No freelancer assigned to this gig'}), 400

        # Verify gig is in progress
        if gig.status != 'in_progress':
            return jsonify({'error': 'Gig must be in progress to approve'}), 400

        # Find the accepted application to get the agreed price
        accepted_app = Application.query.filter_by(
            gig_id=gig_id,
            freelancer_id=gig.freelancer_id,
            status='accepted'
        ).first()

        if not accepted_app or not accepted_app.proposed_price:
            # Fallback to budget max if no application found
            amount = gig.budget_max
        else:
            amount = accepted_app.proposed_price

        # Get payment method from request (optional)
        data = request.get_json() or {}
        payment_method = data.get('payment_method', 'bank_transfer')

        # Calculate commission using tiered structure
        commission = calculate_commission(amount)
        net_amount = amount - commission

        # Generate invoice number
        import random
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

        # Create transaction
        transaction = Transaction(
            gig_id=gig_id,
            freelancer_id=gig.freelancer_id,
            client_id=gig.client_id,
            amount=amount,
            commission=commission,
            net_amount=net_amount,
            payment_method=payment_method,
            status='completed'
        )
        db.session.add(transaction)
        db.session.flush()

        # Check if invoice already exists (auto-generated on completion)
        invoice = Invoice.query.filter_by(gig_id=gig_id).first()

        if invoice:
            # Update existing invoice to mark as paid
            invoice.status = 'paid'
            invoice.paid_at = datetime.utcnow()
            invoice.payment_method = payment_method
            invoice.transaction_id = transaction.id
            invoice.notes = f'Auto-payment for completed gig: {gig.title}'
            invoice_number = invoice.invoice_number
        else:
            # Create new invoice if it doesn't exist
            invoice = Invoice(
                invoice_number=invoice_number,
                transaction_id=transaction.id,
                gig_id=gig_id,
                client_id=gig.client_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=commission,
                tax_amount=0.0,
                total_amount=amount,
                status='paid',
                payment_method=payment_method,
                paid_at=datetime.utcnow(),
                notes=f'Auto-payment for completed gig: {gig.title}'
            )
            db.session.add(invoice)

        # Update or create freelancer wallet
        freelancer_wallet = Wallet.query.filter_by(user_id=gig.freelancer_id).first()
        if not freelancer_wallet:
            freelancer_wallet = Wallet(user_id=gig.freelancer_id)
            db.session.add(freelancer_wallet)
            db.session.flush()

        # Update wallet balances
        old_balance = freelancer_wallet.balance
        freelancer_wallet.balance += net_amount
        freelancer_wallet.total_earned += net_amount

        # Create payment history for freelancer
        freelancer_history = PaymentHistory(
            user_id=gig.freelancer_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            type='payment',
            amount=net_amount,
            balance_before=old_balance,
            balance_after=freelancer_wallet.balance,
            description=f'Payment received (auto): {gig.title}',
            reference_number=invoice_number
        )
        db.session.add(freelancer_history)

        # Update or create client wallet
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        if not client_wallet:
            client_wallet = Wallet(user_id=gig.client_id)
            db.session.add(client_wallet)
            db.session.flush()

        # Update client wallet
        client_old_balance = client_wallet.balance
        client_wallet.total_spent += amount

        # Create payment history for client
        client_history = PaymentHistory(
            user_id=gig.client_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            type='payment',
            amount=amount,
            balance_before=client_old_balance,
            balance_after=client_wallet.balance,
            description=f'Payment made (auto): {gig.title}',
            reference_number=invoice_number
        )
        db.session.add(client_history)

        # Update gig status to completed
        gig.status = 'completed'

        # Update freelancer stats
        freelancer = User.query.get(gig.freelancer_id)
        if freelancer:
            freelancer.completed_gigs = (freelancer.completed_gigs or 0) + 1
            freelancer.total_earnings = (freelancer.total_earnings or 0) + net_amount

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Gig approved and payment processed automatically!',
            'invoice_number': invoice_number,
            'transaction_id': transaction.id,
            'payment_details': {
                'amount_paid': amount,
                'platform_commission': commission,
                'freelancer_receives': net_amount
            },
            'commission_tier': '15%' if amount <= 500 else ('10%' if amount <= 2000 else '5%')
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Auto-approve and pay error: {str(e)}")
        return jsonify({'error': f'Failed to process automatic payment: {str(e)}'}), 500

# Admin Billing Routes
@app.route('/api/admin/billing/payouts', methods=['GET'])
@admin_required
def admin_get_payouts():
    """Admin: Get all payout requests"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', 'all')

        query = Payout.query
        if status != 'all':
            query = query.filter_by(status=status)

        pagination = query.order_by(Payout.requested_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        payouts = []
        for p in pagination.items:
            user = User.query.get(p.freelancer_id)
            payouts.append({
                'id': p.id,
                'payout_number': p.payout_number,
                'freelancer_name': user.username if user else 'N/A',
                'freelancer_email': user.email if user else 'N/A',
                'amount': p.amount,
                'fee': p.fee,
                'net_amount': p.net_amount,
                'payment_method': p.payment_method,
                'bank_name': p.bank_name,
                'account_number': p.account_number,
                'account_name': p.account_name,
                'status': p.status,
                'requested_at': p.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                'processed_at': p.processed_at.strftime('%Y-%m-%d %H:%M:%S') if p.processed_at else None,
                'completed_at': p.completed_at.strftime('%Y-%m-%d %H:%M:%S') if p.completed_at else None,
                'failure_reason': p.failure_reason,
                'admin_notes': p.admin_notes
            })

        return jsonify({
            'payouts': payouts,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        }), 200
    except Exception as e:
        app.logger.error(f"Admin get payouts error: {str(e)}")
        return jsonify({'error': 'Failed to get payouts'}), 500

@app.route('/api/admin/billing/payouts/<int:payout_id>', methods=['PUT'])
@admin_required
def admin_update_payout(payout_id):
    """Admin: Update payout status"""
    try:
        payout = Payout.query.get_or_404(payout_id)
        data = request.get_json()

        new_status = data.get('status')
        admin_notes = data.get('admin_notes')

        if new_status not in ['pending', 'processing', 'completed', 'failed', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400

        old_status = payout.status
        payout.status = new_status

        if admin_notes:
            payout.admin_notes = admin_notes

        if new_status == 'processing' and old_status == 'pending':
            payout.processed_at = datetime.utcnow()

        if new_status == 'completed':
            payout.completed_at = datetime.utcnow()

            # Release held balance and update wallet
            wallet = Wallet.query.filter_by(user_id=payout.freelancer_id).first()
            if wallet:
                wallet.held_balance -= payout.amount

                # Create payment history
                history = PaymentHistory(
                    user_id=payout.freelancer_id,
                    payout_id=payout.id,
                    type='payout',
                    amount=payout.amount,
                    balance_before=wallet.balance + payout.amount,
                    balance_after=wallet.balance,
                    description=f'Payout completed: {payout.payout_number}',
                    reference_number=payout.payout_number
                )
                db.session.add(history)

        if new_status in ['failed', 'cancelled']:
            # Return balance to wallet
            wallet = Wallet.query.filter_by(user_id=payout.freelancer_id).first()
            if wallet:
                wallet.balance += payout.amount
                wallet.held_balance -= payout.amount

                # Create payment history
                history = PaymentHistory(
                    user_id=payout.freelancer_id,
                    payout_id=payout.id,
                    type='release',
                    amount=payout.amount,
                    balance_before=wallet.balance - payout.amount,
                    balance_after=wallet.balance,
                    description=f'Payout {new_status}: {payout.payout_number}',
                    reference_number=payout.payout_number
                )
                db.session.add(history)

        if data.get('failure_reason'):
            payout.failure_reason = data['failure_reason']

        db.session.commit()

        # Log admin payout action
        admin_user = User.query.get(session['user_id'])
        security_logger.log_admin_action(
            action=f'Admin updated payout status from {old_status} to {new_status}',
            resource_type='payout',
            resource_id=payout.payout_number,
            details={
                'payout_id': payout_id,
                'payout_number': payout.payout_number,
                'freelancer_id': payout.freelancer_id,
                'amount': payout.amount,
                'old_status': old_status,
                'new_status': new_status,
                'admin_notes': admin_notes,
                'failure_reason': data.get('failure_reason'),
                'admin_username': admin_user.username if admin_user else 'unknown'
            },
            severity='high'
        )

        return jsonify({'message': 'Payout updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin update payout error: {str(e)}")
        return jsonify({'error': 'Failed to update payout'}), 500

@app.route('/api/admin/billing/stats', methods=['GET'])
@admin_required
def admin_billing_stats():
    """Admin: Get billing statistics"""
    try:
        # Total transactions
        total_transactions = Transaction.query.filter_by(status='completed').count()
        total_revenue = db.session.query(db.func.sum(Transaction.commission)).filter_by(status='completed').scalar() or 0

        # Pending payouts
        pending_payouts = Payout.query.filter_by(status='pending').count()
        pending_payout_amount = db.session.query(db.func.sum(Payout.amount)).filter_by(status='pending').scalar() or 0

        # Total invoices
        total_invoices = Invoice.query.count()
        paid_invoices = Invoice.query.filter_by(status='paid').count()

        # Recent transactions (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_transactions = Transaction.query.filter(
            Transaction.transaction_date >= thirty_days_ago,
            Transaction.status == 'completed'
        ).count()

        return jsonify({
            'total_transactions': total_transactions,
            'total_revenue': float(total_revenue),
            'pending_payouts_count': pending_payouts,
            'pending_payouts_amount': float(pending_payout_amount),
            'total_invoices': total_invoices,
            'paid_invoices': paid_invoices,
            'recent_transactions': recent_transactions
        }), 200
    except Exception as e:
        app.logger.error(f"Admin billing stats error: {str(e)}")
        return jsonify({'error': 'Failed to get billing statistics'}), 500

# ==================== ADMIN FINANCIAL REPORTS ROUTES ====================

@app.route('/api/admin/reports/platform', methods=['GET'])
@admin_required
def admin_platform_financial_report():
    """Generate platform-wide financial report for specified date range"""
    try:
        # Get date range parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # Set end date to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        if start_date > end_date:
            return jsonify({'error': 'start_date must be before end_date'}), 400

        # Total transactions in period
        transactions = Transaction.query.filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == 'completed'
        ).all()

        total_transactions = len(transactions)
        total_transaction_amount = sum(t.amount for t in transactions)
        total_commission = sum(t.commission for t in transactions)
        total_net_amount = sum(t.net_amount for t in transactions)

        # Breakdown by payment method
        payment_methods = {}
        for t in transactions:
            method = t.payment_method or 'unknown'
            if method not in payment_methods:
                payment_methods[method] = {'count': 0, 'amount': 0, 'commission': 0}
            payment_methods[method]['count'] += 1
            payment_methods[method]['amount'] += float(t.amount)
            payment_methods[method]['commission'] += float(t.commission)

        # Commission breakdown by tier
        commission_breakdown = {
            'tier_15_percent': {'count': 0, 'amount': 0, 'commission': 0},
            'tier_10_percent': {'count': 0, 'amount': 0, 'commission': 0},
            'tier_5_percent': {'count': 0, 'amount': 0, 'commission': 0}
        }

        for t in transactions:
            amount = float(t.amount)
            commission = float(t.commission)
            if amount <= 500:
                commission_breakdown['tier_15_percent']['count'] += 1
                commission_breakdown['tier_15_percent']['amount'] += amount
                commission_breakdown['tier_15_percent']['commission'] += commission
            elif amount <= 2000:
                commission_breakdown['tier_10_percent']['count'] += 1
                commission_breakdown['tier_10_percent']['amount'] += amount
                commission_breakdown['tier_10_percent']['commission'] += commission
            else:
                commission_breakdown['tier_5_percent']['count'] += 1
                commission_breakdown['tier_5_percent']['amount'] += amount
                commission_breakdown['tier_5_percent']['commission'] += commission

        # Escrow statistics
        escrows_funded = Escrow.query.filter(
            Escrow.funded_at >= start_date,
            Escrow.funded_at <= end_date
        ).all()

        escrows_released = Escrow.query.filter(
            Escrow.released_at >= start_date,
            Escrow.released_at <= end_date,
            Escrow.status == 'released'
        ).all()

        total_escrow_funded = sum(e.amount for e in escrows_funded)
        total_escrow_released = sum(e.amount for e in escrows_released)
        total_escrow_fees = sum(e.platform_fee for e in escrows_released)

        # Payout statistics
        payouts_completed = Payout.query.filter(
            Payout.completed_at >= start_date,
            Payout.completed_at <= end_date,
            Payout.status == 'completed'
        ).all()

        total_payouts = len(payouts_completed)
        total_payout_amount = sum(p.amount for p in payouts_completed)
        total_payout_fees = sum(p.fee for p in payouts_completed)

        # Payout breakdown by method
        payout_methods = {}
        for p in payouts_completed:
            method = p.payment_method or 'unknown'
            if method not in payout_methods:
                payout_methods[method] = {'count': 0, 'amount': 0, 'fees': 0}
            payout_methods[method]['count'] += 1
            payout_methods[method]['amount'] += float(p.amount)
            payout_methods[method]['fees'] += float(p.fee)

        # Invoice statistics
        invoices_paid = Invoice.query.filter(
            Invoice.paid_at >= start_date,
            Invoice.paid_at <= end_date,
            Invoice.status == 'paid'
        ).all()

        total_invoices = len(invoices_paid)
        total_invoice_amount = sum(i.total_amount for i in invoices_paid)
        total_platform_fees = sum(i.platform_fee for i in invoices_paid)

        # New users in period
        new_users = User.query.filter(
            User.created_at >= start_date,
            User.created_at <= end_date
        ).count()

        # Gigs completed in period
        gigs_completed = Gig.query.filter(
            Gig.updated_at >= start_date,
            Gig.updated_at <= end_date,
            Gig.status == 'completed'
        ).count()

        return jsonify({
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            },
            'transactions': {
                'total_count': total_transactions,
                'total_amount': float(total_transaction_amount),
                'total_commission': float(total_commission),
                'total_net_amount': float(total_net_amount),
                'payment_methods': payment_methods,
                'commission_breakdown': commission_breakdown
            },
            'escrow': {
                'funded_count': len(escrows_funded),
                'funded_amount': float(total_escrow_funded),
                'released_count': len(escrows_released),
                'released_amount': float(total_escrow_released),
                'platform_fees': float(total_escrow_fees)
            },
            'payouts': {
                'total_count': total_payouts,
                'total_amount': float(total_payout_amount),
                'total_fees': float(total_payout_fees),
                'payment_methods': payout_methods
            },
            'invoices': {
                'total_count': total_invoices,
                'total_amount': float(total_invoice_amount),
                'platform_fees': float(total_platform_fees)
            },
            'overview': {
                'new_users': new_users,
                'gigs_completed': gigs_completed,
                'total_revenue': float(total_commission + total_escrow_fees + total_platform_fees)
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Platform financial report error: {str(e)}")
        return jsonify({'error': 'Failed to generate platform report'}), 500

@app.route('/api/admin/reports/worker/<int:worker_id>', methods=['GET'])
@admin_required
def admin_worker_financial_report(worker_id):
    """Generate financial report for a specific worker"""
    try:
        # Get worker
        worker = User.query.get(worker_id)
        if not worker:
            return jsonify({'error': 'Worker not found'}), 404

        # Get date range parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Get worker's wallet
        wallet = Wallet.query.filter_by(user_id=worker_id).first()

        # Get completed transactions
        transactions = Transaction.query.filter(
            Transaction.freelancer_id == worker_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == 'completed'
        ).all()

        total_earned = sum(t.net_amount for t in transactions)
        total_commission_paid = sum(t.commission for t in transactions)
        transaction_count = len(transactions)

        # Get gigs
        gigs = Gig.query.join(Application).filter(
            Application.freelancer_id == worker_id,
            Application.status == 'accepted',
            Gig.updated_at >= start_date,
            Gig.updated_at <= end_date
        ).all()

        completed_gigs = [g for g in gigs if g.status == 'completed']
        in_progress_gigs = [g for g in gigs if g.status == 'in_progress']

        # Gig breakdown
        gig_details = []
        for gig in completed_gigs:
            transaction = Transaction.query.filter_by(
                gig_id=gig.id,
                freelancer_id=worker_id,
                status='completed'
            ).first()

            gig_details.append({
                'gig_id': gig.id,
                'title': gig.title,
                'budget': float(gig.agreed_amount or gig.approved_budget or 0),
                'earned': float(transaction.net_amount) if transaction else 0,
                'commission': float(transaction.commission) if transaction else 0,
                'completed_at': gig.updated_at.strftime('%Y-%m-%d') if gig.updated_at else None
            })

        # Get payouts
        payouts = Payout.query.filter(
            Payout.freelancer_id == worker_id,
            Payout.completed_at >= start_date,
            Payout.completed_at <= end_date,
            Payout.status == 'completed'
        ).all()

        total_payouts = sum(p.amount for p in payouts)
        payout_fees = sum(p.fee for p in payouts)

        # Payout details
        payout_details = [{
            'payout_id': p.id,
            'payout_number': p.payout_number,
            'amount': float(p.amount),
            'fee': float(p.fee),
            'net_amount': float(p.net_amount),
            'payment_method': p.payment_method,
            'completed_at': p.completed_at.strftime('%Y-%m-%d %H:%M:%S') if p.completed_at else None
        } for p in payouts]

        # Escrows
        escrows = Escrow.query.filter(
            Escrow.freelancer_id == worker_id,
            Escrow.released_at >= start_date,
            Escrow.released_at <= end_date,
            Escrow.status == 'released'
        ).all()

        total_escrow_released = sum(e.net_amount for e in escrows)

        return jsonify({
            'worker': {
                'id': worker.id,
                'username': worker.username,
                'email': worker.email,
                'user_type': worker.user_type
            },
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            },
            'wallet': {
                'current_balance': float(wallet.balance) if wallet else 0,
                'held_balance': float(wallet.held_balance) if wallet else 0,
                'total_earned': float(wallet.total_earned) if wallet else 0
            },
            'earnings': {
                'total_earned': float(total_earned),
                'total_commission_paid': float(total_commission_paid),
                'transaction_count': transaction_count,
                'escrow_released': float(total_escrow_released)
            },
            'gigs': {
                'completed_count': len(completed_gigs),
                'in_progress_count': len(in_progress_gigs),
                'gig_details': gig_details
            },
            'payouts': {
                'total_amount': float(total_payouts),
                'total_fees': float(payout_fees),
                'payout_count': len(payouts),
                'payout_details': payout_details
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Worker financial report error: {str(e)}")
        return jsonify({'error': 'Failed to generate worker report'}), 500

@app.route('/api/admin/reports/client/<int:client_id>', methods=['GET'])
@admin_required
def admin_client_financial_report(client_id):
    """Generate spending report for a specific client"""
    try:
        # Get client
        client = User.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Get date range parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Get client's wallet
        wallet = Wallet.query.filter_by(user_id=client_id).first()

        # Get transactions
        transactions = Transaction.query.filter(
            Transaction.client_id == client_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.status == 'completed'
        ).all()

        total_spent = sum(t.amount for t in transactions)
        total_commission = sum(t.commission for t in transactions)
        transaction_count = len(transactions)

        # Payment method breakdown
        payment_methods = {}
        for t in transactions:
            method = t.payment_method or 'unknown'
            if method not in payment_methods:
                payment_methods[method] = {'count': 0, 'amount': 0}
            payment_methods[method]['count'] += 1
            payment_methods[method]['amount'] += float(t.amount)

        # Get gigs
        gigs = Gig.query.filter(
            Gig.client_id == client_id,
            Gig.created_at >= start_date,
            Gig.created_at <= end_date
        ).all()

        completed_gigs = [g for g in gigs if g.status == 'completed']
        active_gigs = [g for g in gigs if g.status in ['open', 'in_progress']]

        # Gig breakdown
        gig_details = []
        for gig in gigs:
            transaction = Transaction.query.filter_by(
                gig_id=gig.id,
                client_id=client_id,
                status='completed'
            ).first()

            gig_details.append({
                'gig_id': gig.id,
                'title': gig.title,
                'status': gig.status,
                'budget': float(gig.agreed_amount or gig.approved_budget or gig.budget_max or 0),
                'spent': float(transaction.amount) if transaction else 0,
                'commission': float(transaction.commission) if transaction else 0,
                'created_at': gig.created_at.strftime('%Y-%m-%d') if gig.created_at else None,
                'completed_at': gig.updated_at.strftime('%Y-%m-%d') if gig.status == 'completed' and gig.updated_at else None
            })

        # Get escrows
        escrows_funded = Escrow.query.filter(
            Escrow.client_id == client_id,
            Escrow.funded_at >= start_date,
            Escrow.funded_at <= end_date
        ).all()

        total_escrow_funded = sum(e.amount for e in escrows_funded)
        escrow_pending = sum(e.amount for e in escrows_funded if e.status == 'funded')

        # Get invoices
        invoices = Invoice.query.filter(
            Invoice.client_id == client_id,
            Invoice.created_at >= start_date,
            Invoice.created_at <= end_date
        ).all()

        paid_invoices = [i for i in invoices if i.status == 'paid']
        total_invoice_amount = sum(i.total_amount for i in paid_invoices)

        return jsonify({
            'client': {
                'id': client.id,
                'username': client.username,
                'email': client.email,
                'user_type': client.user_type
            },
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            },
            'wallet': {
                'current_balance': float(wallet.balance) if wallet else 0,
                'total_spent': float(wallet.total_spent) if wallet else 0
            },
            'spending': {
                'total_spent': float(total_spent),
                'total_commission': float(total_commission),
                'transaction_count': transaction_count,
                'payment_methods': payment_methods
            },
            'gigs': {
                'total_count': len(gigs),
                'completed_count': len(completed_gigs),
                'active_count': len(active_gigs),
                'gig_details': gig_details
            },
            'escrow': {
                'total_funded': float(total_escrow_funded),
                'pending_amount': float(escrow_pending),
                'funded_count': len(escrows_funded)
            },
            'invoices': {
                'total_count': len(invoices),
                'paid_count': len(paid_invoices),
                'total_amount': float(total_invoice_amount)
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Client financial report error: {str(e)}")
        return jsonify({'error': 'Failed to generate client report'}), 500

@app.route('/api/admin/reports/workers', methods=['GET'])
@admin_required
def admin_get_workers_list():
    """Get list of workers for report selection"""
    try:
        workers = User.query.filter_by(user_type='freelancer').order_by(User.username).all()

        workers_list = [{
            'id': w.id,
            'username': w.username,
            'email': w.email,
            'total_earnings': float(w.total_earnings or 0),
            'completed_gigs': w.completed_gigs or 0
        } for w in workers]

        return jsonify({'workers': workers_list}), 200
    except Exception as e:
        app.logger.error(f"Get workers list error: {str(e)}")
        return jsonify({'error': 'Failed to get workers list'}), 500

@app.route('/api/admin/reports/clients', methods=['GET'])
@admin_required
def admin_get_clients_list():
    """Get list of clients for report selection"""
    try:
        clients = User.query.filter_by(user_type='client').order_by(User.username).all()

        clients_list = [{
            'id': c.id,
            'username': c.username,
            'email': c.email
        } for c in clients]

        # Get spending for each client
        for client_data in clients_list:
            wallet = Wallet.query.filter_by(user_id=client_data['id']).first()
            client_data['total_spent'] = float(wallet.total_spent) if wallet else 0

        return jsonify({'clients': clients_list}), 200
    except Exception as e:
        app.logger.error(f"Get clients list error: {str(e)}")
        return jsonify({'error': 'Failed to get clients list'}), 500

# ==================== ACCOUNTING/BILLING ADMIN ROUTES ====================

@app.route('/api/accounting/invoices', methods=['GET'])
@billing_admin_required
def accounting_get_invoices():
    """Accounting: Get all invoices with filters"""
    try:
        status_filter = request.args.get('status', 'all')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        query = Invoice.query
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)

        total_count = query.count()
        invoices = query.order_by(Invoice.created_at.desc()).limit(limit).offset(offset).all()

        invoice_list = []
        for inv in invoices:
            client = User.query.get(inv.client_id)
            freelancer = User.query.get(inv.freelancer_id)
            invoice_list.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'client_name': client.username if client else 'Unknown',
                'freelancer_name': freelancer.username if freelancer else 'Unknown',
                'amount': float(inv.amount),
                'total_amount': float(inv.total_amount),
                'status': inv.status,
                'created_at': inv.created_at.isoformat() if inv.created_at else None,
                'paid_at': inv.paid_at.isoformat() if inv.paid_at else None
            })

        return jsonify({
            'invoices': invoice_list,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        app.logger.error(f"Accounting get invoices error: {str(e)}")
        return jsonify({'error': 'Failed to get invoices'}), 500

@app.route('/api/accounting/payouts', methods=['GET'])
@billing_admin_required
def accounting_get_payouts():
    """Accounting: Get all payout requests"""
    try:
        status_filter = request.args.get('status', 'all')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        query = Payout.query
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)

        total_count = query.count()
        payouts = query.order_by(Payout.requested_at.desc()).limit(limit).offset(offset).all()

        payout_list = []
        for payout in payouts:
            freelancer = User.query.get(payout.freelancer_id)
            payout_list.append({
                'id': payout.id,
                'payout_number': payout.payout_number,
                'freelancer_name': freelancer.username if freelancer else 'Unknown',
                'amount': float(payout.amount),
                'net_amount': float(payout.net_amount),
                'status': payout.status,
                'payment_method': payout.payment_method,
                'requested_at': payout.requested_at.isoformat() if payout.requested_at else None,
                'completed_at': payout.completed_at.isoformat() if payout.completed_at else None
            })

        return jsonify({
            'payouts': payout_list,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        app.logger.error(f"Accounting get payouts error: {str(e)}")
        return jsonify({'error': 'Failed to get payouts'}), 500

@app.route('/api/accounting/revenue-summary', methods=['GET'])
@billing_admin_required
def accounting_revenue_summary():
    """Accounting: Get revenue summary for specified period"""
    try:
        period = request.args.get('period', 'month')  # day, week, month, year

        # Calculate date range based on period
        now = datetime.utcnow()
        if period == 'day':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return jsonify({'error': 'Invalid period'}), 400

        # Get completed transactions in period
        transactions = Transaction.query.filter(
            Transaction.transaction_date >= start_date,
            Transaction.status == 'completed'
        ).all()

        total_revenue = sum(float(t.commission) for t in transactions)
        total_transaction_amount = sum(float(t.amount) for t in transactions)
        transaction_count = len(transactions)

        # Get paid invoices in period
        invoices = Invoice.query.filter(
            Invoice.paid_at >= start_date,
            Invoice.status == 'paid'
        ).all()

        total_invoiced = sum(float(inv.total_amount) for inv in invoices)
        invoice_count = len(invoices)

        # Get completed payouts in period
        payouts = Payout.query.filter(
            Payout.completed_at >= start_date,
            Payout.status == 'completed'
        ).all()

        total_paid_out = sum(float(p.net_amount) for p in payouts)
        payout_count = len(payouts)

        return jsonify({
            'period': period,
            'start_date': start_date.isoformat(),
            'revenue': {
                'total': total_revenue,
                'transaction_count': transaction_count,
                'total_transaction_amount': total_transaction_amount
            },
            'invoices': {
                'total': total_invoiced,
                'count': invoice_count
            },
            'payouts': {
                'total': total_paid_out,
                'count': payout_count
            },
            'net_revenue': total_revenue
        }), 200
    except Exception as e:
        app.logger.error(f"Accounting revenue summary error: {str(e)}")
        return jsonify({'error': 'Failed to get revenue summary'}), 500

@app.route('/api/accounting/user-roles', methods=['GET'])
@admin_required
def accounting_get_user_roles():
    """Get all admin users and their roles"""
    try:
        admin_users = User.query.filter_by(is_admin=True).order_by(User.username).all()

        user_list = []
        for user in admin_users:
            user_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'admin_role': user.admin_role,
                'admin_permissions': user.admin_permissions
            })

        return jsonify({'users': user_list}), 200
    except Exception as e:
        app.logger.error(f"Get user roles error: {str(e)}")
        return jsonify({'error': 'Failed to get user roles'}), 500

@app.route('/api/accounting/user-roles/<int:user_id>', methods=['PUT'])
@admin_required
def accounting_update_user_role(user_id):
    """Update admin user's role - only super_admin can do this"""
    try:
        current_user = User.query.get(session['user_id'])

        # Only super_admin can modify roles
        if current_user.admin_role != 'super_admin':
            return jsonify({'error': 'Only super admins can modify user roles'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        new_role = data.get('admin_role')
        new_permissions = data.get('admin_permissions')

        # Validate role
        valid_roles = ['super_admin', 'billing', 'moderator', None]
        if new_role not in valid_roles:
            return jsonify({'error': 'Invalid role'}), 400

        user.admin_role = new_role
        if new_permissions is not None:
            user.admin_permissions = new_permissions

        # If setting a role, ensure is_admin is True
        if new_role:
            user.is_admin = True

        db.session.commit()

        return jsonify({
            'message': 'User role updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'admin_role': user.admin_role,
                'admin_permissions': user.admin_permissions
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Update user role error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update user role'}), 500

# ==================== ADMIN SETTINGS ROUTES ====================

@app.route('/api/admin/settings/payment-gateway', methods=['GET'])
@admin_required
def get_payment_gateway_setting():
    """Get current payment gateway setting"""
    try:
        gateway = get_site_setting('payment_gateway', 'stripe')
        payhalal_configured = bool(os.environ.get('PAYHALAL_MERCHANT_ID') and os.environ.get('PAYHALAL_API_KEY'))
        stripe_configured = bool(os.environ.get('STRIPE_SECRET_KEY'))
        
        return jsonify({
            'gateway': gateway,
            'payhalal_configured': payhalal_configured,
            'stripe_configured': stripe_configured
        }), 200
    except Exception as e:
        app.logger.error(f"Get payment gateway error: {str(e)}")
        return jsonify({'error': 'Failed to get payment gateway setting'}), 500

@app.route('/api/admin/settings/payment-gateway', methods=['POST'])
@admin_required
def set_payment_gateway_setting():
    """Set payment gateway preference"""
    try:
        data = request.get_json()
        gateway = data.get('gateway')
        
        if gateway not in ['stripe', 'payhalal']:
            return jsonify({'error': 'Invalid gateway. Must be stripe or payhalal'}), 400
        
        user_id = session.get('user_id')
        set_site_setting(
            'payment_gateway', 
            gateway, 
            description=f'Payment gateway set to {gateway}',
            user_id=user_id
        )
        
        return jsonify({
            'message': f'Payment gateway set to {gateway}',
            'gateway': gateway
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Set payment gateway error: {str(e)}")
        return jsonify({'error': 'Failed to set payment gateway'}), 500

@app.route('/api/admin/settings/stripe-mode', methods=['GET'])
@admin_required
def get_stripe_mode_setting():
    """Get current Stripe mode setting (test/live)"""
    try:
        mode = get_site_setting('stripe_mode', 'test')

        # Check if keys are configured for both modes
        test_configured = bool(
            os.environ.get('STRIPE_TEST_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')
        )
        live_configured = bool(os.environ.get('STRIPE_LIVE_SECRET_KEY'))

        # Get current Stripe keys info
        keys = get_stripe_keys()

        return jsonify({
            'mode': mode,
            'test_configured': test_configured,
            'live_configured': live_configured,
            'current_key_set': bool(keys['secret_key'])
        }), 200
    except Exception as e:
        app.logger.error(f"Get Stripe mode error: {str(e)}")
        return jsonify({'error': 'Failed to get Stripe mode setting'}), 500

@app.route('/api/admin/settings/stripe-mode', methods=['POST'])
@admin_required
def set_stripe_mode_setting():
    """Set Stripe mode (test/live)"""
    try:
        data = request.get_json()
        mode = data.get('mode')

        if mode not in ['test', 'live']:
            return jsonify({'error': 'Invalid mode. Must be test or live'}), 400

        # Check if keys are configured for the selected mode
        if mode == 'live':
            if not os.environ.get('STRIPE_LIVE_SECRET_KEY'):
                return jsonify({'error': 'Live mode keys are not configured. Please set STRIPE_LIVE_SECRET_KEY and STRIPE_LIVE_PUBLISHABLE_KEY in environment variables.'}), 400
        else:
            if not (os.environ.get('STRIPE_TEST_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')):
                return jsonify({'error': 'Test mode keys are not configured. Please set STRIPE_TEST_SECRET_KEY and STRIPE_TEST_PUBLISHABLE_KEY in environment variables.'}), 400

        user_id = session.get('user_id')
        set_site_setting(
            'stripe_mode',
            mode,
            description=f'Stripe mode set to {mode}',
            user_id=user_id
        )

        # Reinitialize Stripe with new mode
        init_stripe()

        return jsonify({
            'message': f'Stripe mode set to {mode}',
            'mode': mode
        }), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Set Stripe mode error: {str(e)}")
        return jsonify({'error': 'Failed to set Stripe mode'}), 500

@app.route('/api/admin/master-reset', methods=['POST'])
@admin_required
def admin_master_reset():
    """Master reset - delete all data except user accounts"""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        user_id = session.get('user_id')
        admin_user = User.query.get(user_id)
        
        if not admin_user or not check_password_hash(admin_user.password_hash, password):
            return jsonify({'error': 'Invalid password'}), 401
        
        deleted_count = 0
        
        deleted_count += Notification.query.delete()
        deleted_count += DisputeMessage.query.delete()
        deleted_count += Milestone.query.delete()
        deleted_count += Dispute.query.delete()
        deleted_count += Message.query.delete()
        deleted_count += Conversation.query.delete()
        deleted_count += Review.query.delete()
        deleted_count += PaymentHistory.query.delete()
        deleted_count += Receipt.query.delete()
        deleted_count += Invoice.query.delete()
        deleted_count += Escrow.query.delete()
        deleted_count += Transaction.query.delete()
        deleted_count += Application.query.delete()
        deleted_count += WorkPhoto.query.delete()
        deleted_count += GigPhoto.query.delete()
        deleted_count += PortfolioItem.query.delete()
        deleted_count += PlatformFeedback.query.delete()
        deleted_count += Payout.query.delete()
        deleted_count += MicroTask.query.delete()
        deleted_count += Referral.query.delete()
        deleted_count += Gig.query.delete()
        
        Wallet.query.update({Wallet.balance: 0, Wallet.held_balance: 0, Wallet.total_earned: 0, Wallet.total_spent: 0})
        
        db.session.commit()

        app.logger.warning(f"MASTER RESET performed by admin user {user_id} ({admin_user.username}). Deleted {deleted_count} records.")

        # Log critical security event for master reset
        security_logger.log_admin_action(
            action='Master reset - deleted all platform data except users',
            resource_type='system',
            resource_id='master_reset',
            details={
                'deleted_count': deleted_count,
                'performed_by': admin_user.username
            },
            severity='critical',
            message=f'Admin {admin_user.username} performed master reset, deleting {deleted_count} records'
        )

        return jsonify({
            'message': 'Master reset completed successfully',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Master reset error: {str(e)}")
        return jsonify({'error': f'Failed to perform reset: {str(e)}'}), 500

# ==================== PAYMENT APPROVAL ROUTES ====================

@app.route('/payments')
@page_login_required
def payments_page():
    """Payment approval page for clients"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    return render_template('payments.html', user=user, lang=get_user_language(), t=t)

@app.route('/api/payments/pending', methods=['GET'])
@login_required
def get_pending_payments():
    """Get pending payments awaiting client approval"""
    try:
        user_id = session['user_id']
        
        pending_gigs = Gig.query.filter(
            Gig.client_id == user_id,
            Gig.status == 'in_progress',
            Gig.freelancer_id.isnot(None)
        ).all()
        
        payments = []
        for gig in pending_gigs:
            accepted_app = Application.query.filter_by(
                gig_id=gig.id,
                status='accepted'
            ).first()
            
            if accepted_app:
                freelancer = User.query.get(gig.freelancer_id)
                amount = accepted_app.proposed_price or gig.budget_max
                
                commission = calculate_commission(amount)
                commission_rate = 0.15 if amount <= 500 else (0.10 if amount <= 2000 else 0.05)
                processing_fee = (amount * PROCESSING_FEE_PERCENT) + PROCESSING_FEE_FIXED
                net_amount = amount - commission - processing_fee
                
                existing_invoice = Invoice.query.filter_by(gig_id=gig.id).first()
                
                payments.append({
                    'id': gig.id,
                    'gig_title': gig.title,
                    'freelancer_id': gig.freelancer_id,
                    'freelancer_name': freelancer.full_name or freelancer.username if freelancer else 'N/A',
                    'amount': amount,
                    'commission': commission,
                    'commission_rate': commission_rate,
                    'processing_fee': round(processing_fee, 2),
                    'net_amount': round(net_amount, 2),
                    'completed_date': gig.created_at.strftime('%Y-%m-%d'),
                    'invoice_number': existing_invoice.invoice_number if existing_invoice else None
                })
        
        return jsonify({'payments': payments}), 200
    except Exception as e:
        app.logger.error(f"Get pending payments error: {str(e)}")
        return jsonify({'error': 'Failed to get pending payments'}), 500

@app.route('/api/payments/<int:gig_id>/approve', methods=['POST'])
@login_required
def approve_payment(gig_id):
    """Approve payment and release funds to freelancer via Stripe"""
    try:
        user_id = session['user_id']
        gig = Gig.query.get_or_404(gig_id)
        
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can approve this payment'}), 403
        
        if not gig.freelancer_id:
            return jsonify({'error': 'No freelancer assigned to this gig'}), 400
        
        if gig.status != 'in_progress':
            return jsonify({'error': 'Gig must be in progress to approve payment'}), 400
        
        accepted_app = Application.query.filter_by(
            gig_id=gig.id,
            status='accepted'
        ).first()
        
        if not accepted_app:
            return jsonify({'error': 'No accepted application found'}), 400
        
        amount = accepted_app.proposed_price or gig.budget_max
        
        commission = calculate_commission(amount)
        processing_fee = (amount * PROCESSING_FEE_PERCENT) + PROCESSING_FEE_FIXED
        net_amount = amount - commission - processing_fee
        
        import random
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
        
        stripe_payment_id = None
        payment_method = 'internal'
        
        if stripe.api_key:
            try:
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(amount * 100),
                    currency='myr',
                    metadata={
                        'gig_id': gig_id,
                        'invoice_number': invoice_number,
                        'freelancer_id': gig.freelancer_id
                    },
                    description=f'Payment for gig: {gig.title}'
                )
                stripe_payment_id = payment_intent.id
                payment_method = 'stripe'
            except Exception as e:
                app.logger.warning(f"Stripe payment creation skipped, using internal settlement: {str(e)}")
                payment_method = 'internal'
        else:
            app.logger.info("Stripe not configured, using internal settlement")
        
        transaction = Transaction(
            gig_id=gig_id,
            freelancer_id=gig.freelancer_id,
            client_id=gig.client_id,
            amount=amount,
            commission=commission,
            net_amount=net_amount,
            payment_method=payment_method,
            status='completed'
        )
        db.session.add(transaction)
        db.session.flush()

        # Check if invoice already exists (auto-generated on completion)
        invoice = Invoice.query.filter_by(gig_id=gig_id).first()

        if invoice:
            # Update existing invoice to mark as paid
            invoice.status = 'paid'
            invoice.paid_at = datetime.utcnow()
            invoice.payment_method = payment_method
            invoice.payment_reference = stripe_payment_id
            invoice.transaction_id = transaction.id
            invoice.tax_amount = processing_fee
            invoice.notes = f'Payment approved for: {gig.title}'
            invoice_number = invoice.invoice_number
        else:
            # Create new invoice if it doesn't exist
            invoice = Invoice(
                invoice_number=invoice_number,
                transaction_id=transaction.id,
                gig_id=gig_id,
                client_id=gig.client_id,
                freelancer_id=gig.freelancer_id,
                amount=amount,
                platform_fee=commission,
                tax_amount=processing_fee,
                total_amount=amount,
                status='paid',
                payment_method=payment_method,
                payment_reference=stripe_payment_id,
                paid_at=datetime.utcnow(),
                notes=f'Payment approved for: {gig.title}'
            )
            db.session.add(invoice)
        
        freelancer_wallet = Wallet.query.filter_by(user_id=gig.freelancer_id).first()
        if not freelancer_wallet:
            freelancer_wallet = Wallet(user_id=gig.freelancer_id)
            db.session.add(freelancer_wallet)
            db.session.flush()
        
        old_balance = freelancer_wallet.balance
        freelancer_wallet.balance += net_amount
        freelancer_wallet.total_earned += net_amount
        
        freelancer_history = PaymentHistory(
            user_id=gig.freelancer_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            type='payment',
            amount=net_amount,
            balance_before=old_balance,
            balance_after=freelancer_wallet.balance,
            description=f'Payment received for: {gig.title}',
            reference_number=invoice_number,
            payment_gateway=payment_method
        )
        db.session.add(freelancer_history)
        
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        if not client_wallet:
            client_wallet = Wallet(user_id=gig.client_id)
            db.session.add(client_wallet)
            db.session.flush()
        
        client_old_balance = client_wallet.balance
        client_wallet.total_spent += amount
        
        client_history = PaymentHistory(
            user_id=gig.client_id,
            transaction_id=transaction.id,
            invoice_id=invoice.id,
            type='payment',
            amount=amount,
            balance_before=client_old_balance,
            balance_after=client_wallet.balance,
            description=f'Payment approved for: {gig.title}',
            reference_number=invoice_number,
            payment_gateway=payment_method
        )
        db.session.add(client_history)
        
        gig.status = 'completed'
        
        freelancer = User.query.get(gig.freelancer_id)
        if freelancer:
            freelancer.completed_gigs = (freelancer.completed_gigs or 0) + 1
            freelancer.total_earnings = (freelancer.total_earnings or 0) + net_amount
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment approved and released successfully',
            'invoice_number': invoice_number,
            'transaction_id': transaction.id,
            'amount': amount,
            'commission': commission,
            'processing_fee': round(processing_fee, 2),
            'net_amount': round(net_amount, 2)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Approve payment error: {str(e)}")
        return jsonify({'error': 'Failed to approve payment'}), 500

@app.route('/api/payments/<int:gig_id>/reject', methods=['POST'])
@login_required
def reject_payment(gig_id):
    """Reject payment - gig remains in progress for resolution"""
    try:
        user_id = session['user_id']
        data = request.get_json()
        
        gig = Gig.query.get_or_404(gig_id)
        
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can reject this payment'}), 403
        
        reason = data.get('reason', 'No reason provided')
        
        gig.status = 'disputed'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment rejected. The gig is now in dispute status.',
            'reason': reason
        }), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Reject payment error: {str(e)}")
        return jsonify({'error': 'Failed to reject payment'}), 500

@app.route('/api/payments/history', methods=['GET'])
@login_required
def get_client_payment_history():
    """Get client's payment history for approved/rejected payments"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Transaction.query.filter_by(client_id=user_id).order_by(
            Transaction.transaction_date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        payments = []
        for t in pagination.items:
            gig = Gig.query.get(t.gig_id)
            freelancer = User.query.get(t.freelancer_id)
            
            payments.append({
                'id': t.id,
                'gig_title': gig.title if gig else 'N/A',
                'freelancer_name': freelancer.full_name or freelancer.username if freelancer else 'N/A',
                'amount': t.amount,
                'commission': t.commission,
                'net_amount': t.net_amount,
                'status': t.status,
                'date': t.transaction_date.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({
            'payments': payments,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        }), 200
    except Exception as e:
        app.logger.error(f"Get client payment history error: {str(e)}")
        return jsonify({'error': 'Failed to get payment history'}), 500

# Lazy initialization flag
_db_initialized = False

def init_database():
    """Initialize database with tables, categories, and sample data (lazy loading)"""
    global _db_initialized
    if _db_initialized:
        return
    
    try:
        # Create tables
        db.create_all()
        
        # Add default categories if they don't exist
        default_categories = [
            # Design & Creative
            Category(name='Graphic Design', slug='graphic-design', description='Logo design, graphic design, branding', icon='palette'),
            Category(name='UI/UX Design', slug='ui-ux', description='User interface, user experience, web design', icon='layers'),
            Category(name='Illustration & Art', slug='illustration', description='Digital art, illustration, custom artwork', icon='pen-tool'),
            Category(name='Logo Design', slug='logo-design', description='Custom logo creation, brand identity', icon='flag'),
            Category(name='Fashion Design', slug='fashion', description='Fashion design, clothing design, style consultation', icon='shopping-bag'),
            Category(name='Interior Design', slug='interior-design', description='Room design, furniture layout, space planning', icon='home'),
            
            # Writing & Content
            Category(name='Content Writing', slug='content-writing', description='Blog posts, website content, copywriting', icon='edit'),
            Category(name='Translation Services', slug='translation', description='Document translation, language translation, localization', icon='globe'),
            Category(name='Proofreading & Editing', slug='proofreading', description='Copy editing, proofreading, grammar checking', icon='check-square'),
            Category(name='Resume & Cover Letter', slug='resume', description='Resume writing, cover letters, CV optimization', icon='file-text'),
            Category(name='Email & Newsletter', slug='email-marketing', description='Email marketing, newsletter design, campaign copy', icon='mail'),
            Category(name='Social Media Copy', slug='social-copy', description='Social media captions, post writing, hashtag strategy', icon='message-square'),
            
            # Video & Media
            Category(name='Video Editing', slug='video-editing', description='Video editing, video production, post-production', icon='video'),
            Category(name='Animation', slug='animation', description='Animation, motion graphics, explainer videos', icon='video'),
            Category(name='Voiceover & Voice Acting', slug='voiceover', description='Professional voiceovers, audio narration, voice acting', icon='mic'),
            Category(name='Podcast Production', slug='podcast', description='Podcast editing, audio production, music production', icon='headphones'),
            Category(name='Photography', slug='photography', description='Photo shoots, photo editing, photo retouching', icon='camera'),
            
            # Web & App Development
            Category(name='Web Development', slug='web-development', description='Website development, web apps, e-commerce sites', icon='code'),
            Category(name='App Development', slug='app-development', description='Mobile apps, iOS/Android, app design', icon='smartphone'),
            Category(name='E-commerce Solutions', slug='ecommerce', description='Online store setup, Shopify, WooCommerce', icon='shopping-cart'),
            
            # Marketing & Business
            Category(name='Digital Marketing', slug='digital-marketing', description='SEO, social media marketing, Google Ads', icon='trending-up'),
            Category(name='Social Media Management', slug='social-media', description='Content management, community engagement, posting schedule', icon='instagram'),
            Category(name='Business Consulting', slug='business-consulting', description='Business strategy, startup advice, mentoring', icon='briefcase'),
            Category(name='Data Analysis', slug='data-analysis', description='Spreadsheets, research, analytics, data entry', icon='bar-chart-2'),
            
            # Education & Tutoring
            Category(name='Tutoring & Lessons', slug='tutoring', description='Online tutoring, language lessons, academic coaching', icon='book'),
            Category(name='Language Teaching', slug='language-teaching', description='English, Malay, Arabic, Chinese language lessons', icon='globe'),
            
            # Technical & Engineering
            Category(name='Programming & Development', slug='programming', description='Coding, bug fixes, software development, IT support', icon='code-square'),
            Category(name='Engineering & CAD', slug='engineering', description='CAD design, 3D design, technical drawings', icon='tool'),
            
            # Admin & Support
            Category(name='Virtual Assistance', slug='virtual-assistant', description='Administrative tasks, email management, scheduling', icon='clipboard'),
            Category(name='Transcription', slug='transcription', description='Audio transcription, video transcription, captioning', icon='type'),
            Category(name='Data Entry', slug='data-entry', description='Data input, database management, spreadsheet work', icon='database'),
            
            # Finance & Legal
            Category(name='Bookkeeping & Accounting', slug='bookkeeping', description='Bookkeeping, basic accounting, tax preparation', icon='dollar-sign'),
            Category(name='Legal Document Services', slug='legal', description='Document review, contract analysis, legal assistance', icon='file'),
            
            # Lifestyle & Personal
            Category(name='Life & Wellness Coaching', slug='wellness-coaching', description='Health coaching, fitness guidance, wellness consulting', icon='heart'),
            Category(name='Personal Styling', slug='personal-styling', description='Personal styling, wardrobe advice, image consulting', icon='user-check'),
            Category(name='Pet Services', slug='pet-services', description='Pet sitting, dog walking, pet training, grooming', icon='award'),
            
            # Home & Handyman
            Category(name='Home Repairs & Handyman', slug='home-repair', description='Minor repairs, assembly, maintenance, installation', icon='wrench'),
            Category(name='Cleaning Services', slug='cleaning', description='House cleaning, office cleaning, deep cleaning', icon='trash-2'),
            Category(name='Gardening & Landscaping', slug='gardening', description='Gardening, landscaping, plant care', icon='leaf'),
            
            # Specialized Services
            Category(name='Crafts & Handmade Items', slug='crafts', description='Custom handmade products, DIY tutorials, craft services', icon='package'),
            Category(name='Music & Audio Production', slug='music-production', description='Music composition, beat production, audio mastering', icon='music'),
            Category(name='Event Planning & Coordination', slug='event-planning', description='Event planning, party coordination, wedding planning', icon='calendar'),
            Category(name='Travel Guide & Tours', slug='tours', description='Local guides, virtual tours, travel planning', icon='map-pin'),
            
            # General
            Category(name='General Services', slug='general', description='General tasks, miscellaneous work, other services', icon='briefcase'),
        ]
        
        # Add all categories that don't exist (support for existing databases)
        added_count = 0
        for cat in default_categories:
            # Check if category exists by slug or name
            existing = Category.query.filter((Category.slug == cat.slug) | (Category.name == cat.name)).first()
            if not existing:
                db.session.add(cat)
                added_count += 1
        
        if added_count > 0:
            db.session.commit()
            print(f"Added {added_count} new categories successfully!")

        # Migration: Fix existing gigs with incorrect category values
        category_migration_map = {
            'design': 'logo-design',
            'writing': 'translation',
            'video': 'video-editing',
            'content': 'social-media'
        }

        migrated_count = 0
        for old_cat, new_cat in category_migration_map.items():
            gigs_to_update = Gig.query.filter_by(category=old_cat).all()
            for gig in gigs_to_update:
                gig.category = new_cat
                migrated_count += 1

        if migrated_count > 0:
            db.session.commit()
            print(f"Migrated {migrated_count} gigs to use correct category slugs")

        # Add sample data if database is empty
        if User.query.count() == 0:
            # Sample users
            sample_user = User(
                username='demo_freelancer',
                email='freelancer@gighala.com',
                password_hash=generate_password_hash('password123'),
                full_name='Ahmad Zaki',
                user_type='freelancer',
                location='Kuala Lumpur',
                skills=json.dumps(['Graphic Design', 'Video Editing', 'Canva']),
                bio='Experienced graphic designer specializing in halal-compliant branding',
                rating=4.8,
                total_earnings=2500.0,
                completed_gigs=15,
                is_verified=True,
                halal_verified=True
            )
            
            sample_client = User(
                username='demo_client',
                email='client@gighala.com',
                password_hash=generate_password_hash('password123'),
                full_name='Siti Nurhaliza',
                user_type='client',
                location='Penang',
                is_verified=True
            )

            # Admin user
            admin_user = User(
                username='admin',
                email='admin@gighala.com',
                password_hash=generate_password_hash('Admin123!'),
                full_name='GigHala Administrator',
                user_type='both',
                location='Kuala Lumpur',
                is_verified=True,
                halal_verified=True,
                is_admin=True
            )

            db.session.add(sample_user)
            db.session.add(sample_client)
            db.session.add(admin_user)
            db.session.commit()
            
            # Sample gigs
            sample_gigs = [
                Gig(
                    title='Design Logo for Halal Restaurant',
                    description='Need a modern logo for my new halal restaurant in KL. Should incorporate Islamic geometric patterns.',
                    category='logo-design',
                    budget_min=200,
                    budget_max=500,
                    duration='3-5 days',
                    location='Kuala Lumpur',
                    is_remote=True,
                    client_id=sample_client.id,
                    halal_compliant=True,
                    halal_verified=True,
                    is_instant_payout=True,
                    skills_required=json.dumps(['Adobe Illustrator', 'Logo Design', 'Branding']),
                    deadline=datetime.utcnow() + timedelta(days=7)
                ),
                Gig(
                    title='Translate Website from English to Bahasa Malaysia',
                    description='Need professional translation for e-commerce website (approximately 50 pages)',
                    category='translation',
                    budget_min=800,
                    budget_max=1200,
                    duration='1 week',
                    location='Remote',
                    is_remote=True,
                    client_id=sample_client.id,
                    halal_compliant=True,
                    skills_required=json.dumps(['Translation', 'Bahasa Malaysia', 'English']),
                    deadline=datetime.utcnow() + timedelta(days=10)
                ),
                Gig(
                    title='Edit 10 Instagram Reels for Modest Fashion Brand',
                    description='Looking for creative video editor to produce engaging Reels showcasing our modest wear collection',
                    category='video-editing',
                    budget_min=300,
                    budget_max=600,
                    duration='5-7 days',
                    location='Remote',
                    is_remote=True,
                    client_id=sample_client.id,
                    halal_compliant=True,
                    is_brand_partnership=True,
                    skills_required=json.dumps(['Video Editing', 'CapCut', 'Social Media']),
                    deadline=datetime.utcnow() + timedelta(days=14)
                ),
                Gig(
                    title='SPM Mathematics Tutoring (Online)',
                    description='Need experienced tutor for SPM Add Maths. 2 hours per week, flexible schedule.',
                    category='tutoring',
                    budget_min=150,
                    budget_max=250,
                    duration='1 month',
                    location='Remote',
                    is_remote=True,
                    client_id=sample_client.id,
                    halal_compliant=True,
                    skills_required=json.dumps(['SPM', 'Mathematics', 'Teaching']),
                    deadline=datetime.utcnow() + timedelta(days=5)
                ),
                Gig(
                    title='Create TikTok Content for Halal Food Delivery App',
                    description='Need 5 creative TikTok videos promoting our halal food delivery service. RM100 per approved video.',
                    category='social-media',
                    budget_min=500,
                    budget_max=800,
                    duration='1 week',
                    location='Johor Bahru',
                    is_remote=False,
                    client_id=sample_client.id,
                    halal_compliant=True,
                    is_brand_partnership=True,
                    is_instant_payout=True,
                    skills_required=json.dumps(['TikTok', 'Content Creation', 'Video Production']),
                    deadline=datetime.utcnow() + timedelta(days=7)
                )
            ]
            
            for gig in sample_gigs:
                db.session.add(gig)
            
            # Sample microtasks
            microtasks = [
                MicroTask(
                    title='Review Halal Restaurant on Google Maps',
                    description='Visit and write honest review for halal restaurant',
                    reward=15.0,
                    task_type='review'
                ),
                MicroTask(
                    title='Complete Survey on Gig Economy',
                    description='10-minute survey about freelance work preferences',
                    reward=10.0,
                    task_type='survey'
                ),
                MicroTask(
                    title='Share GigHala Post on Social Media',
                    description='Share our promotional post and tag 3 friends',
                    reward=5.0,
                    task_type='content_creation'
                )
            ]
            
            for task in microtasks:
                db.session.add(task)
            
            db.session.commit()
            print("Sample data added successfully!")
        
        _db_initialized = True
    except Exception as e:
        print(f"Database initialization error: {e}")
        _db_initialized = True  # Mark as done to avoid retry loops


# ============ STATIC PAGES ============

@app.route('/cara-kerja')
def cara_kerja():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">🚀</span> Bagaimana GigHala Berfungsi</h2>
        <p>GigHala menghubungkan freelancers dengan klien yang mencari perkhidmatan berkualiti. Platform kami memastikan semua transaksi adalah telus, selamat dan mematuhi prinsip halal.</p>
        
        <div class="step-list">
            <div class="step-item">
                <div class="step-number">1</div>
                <div class="step-content">
                    <h4>Daftar Akaun Percuma</h4>
                    <p>Buat akaun dalam masa 2 minit sahaja. Tiada bayaran pendaftaran dan tiada syarat rumit. Isi maklumat asas dan mula meneroka peluang gig.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">2</div>
                <div class="step-content">
                    <h4>Lengkapkan Profil Anda</h4>
                    <p>Tambah kemahiran, pengalaman kerja dan portfolio anda. Profil yang lengkap meningkatkan peluang anda untuk mendapat gig.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">3</div>
                <div class="step-content">
                    <h4>Cari & Apply Gig</h4>
                    <p>Terokai beratus gig dalam pelbagai kategori. Gunakan filter untuk mencari gig yang sesuai dengan kemahiran dan jadual anda. Hantar proposal yang menarik untuk menonjol.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">4</div>
                <div class="step-content">
                    <h4>Siapkan Kerja</h4>
                    <p>Selepas diterima, siapkan kerja mengikut keperluan klien. Komunikasi yang baik adalah kunci kejayaan.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">5</div>
                <div class="step-content">
                    <h4>Terima Bayaran</h4>
                    <p>Bayaran diproses dengan selamat melalui platform. Instant payout dalam 24 jam ke Touch 'n Go atau akaun bank anda.</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">💼</span> Untuk Klien</h2>
        <p>Sebagai klien, anda boleh menyiarkan gig dan mencari freelancers berkualiti untuk projek anda.</p>
        
        <div class="step-list">
            <div class="step-item">
                <div class="step-number">1</div>
                <div class="step-content">
                    <h4>Siarkan Gig</h4>
                    <p>Terangkan projek anda dengan jelas termasuk keperluan, bajet dan deadline.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">2</div>
                <div class="step-content">
                    <h4>Terima Proposal</h4>
                    <p>Freelancers akan menghantar proposal. Semak profil, rating dan portfolio mereka.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">3</div>
                <div class="step-content">
                    <h4>Pilih Freelancer Terbaik</h4>
                    <p>Pilih freelancer yang paling sesuai berdasarkan kemahiran, pengalaman dan harga.</p>
                </div>
            </div>
            <div class="step-item">
                <div class="step-number">4</div>
                <div class="step-content">
                    <h4>Bayar Dengan Selamat</h4>
                    <p>Bayaran dilindungi melalui escrow system. Wang hanya dikeluarkan selepas kerja disiapkan.</p>
                </div>
            </div>
        </div>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='cara-kerja',
                         page_title='Cara Kerja',
                         page_subtitle='Ketahui bagaimana platform GigHala berfungsi untuk freelancers dan klien',
                         content=content)

@app.route('/pricing')
def pricing():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">💰</span> Harga Telus & Berpatutan</h2>
        <p>GigHala menawarkan struktur harga yang telus tanpa bayaran tersembunyi. Kami menggunakan sistem komisyen berperingkat yang memberi ganjaran kepada freelancers dengan projek bernilai tinggi.</p>
        
        <div class="pricing-grid">
            <div class="pricing-card">
                <div class="pricing-title">Freelancer</div>
                <div class="pricing-price">PERCUMA<span></span></div>
                <p style="color: var(--text-gray);">Untuk freelancers yang mencari gig</p>
                <ul class="pricing-features">
                    <li>Pendaftaran percuma</li>
                    <li>Browse unlimited gigs</li>
                    <li>Hantar unlimited proposals</li>
                    <li>Komisyen berperingkat (lihat bawah)</li>
                    <li>Instant payout dalam 24 jam</li>
                    <li>Sokongan pelanggan</li>
                </ul>
            </div>
            
            <div class="pricing-card featured">
                <div class="pricing-title">Komisyen Berperingkat</div>
                <div class="pricing-price">5-15%<span></span></div>
                <p style="color: var(--text-gray);">Lebih besar projek, lebih rendah komisyen</p>
                <ul class="pricing-features">
                    <li><strong>RM0 - RM500:</strong> 15% komisyen</li>
                    <li><strong>RM501 - RM2,000:</strong> 10% komisyen</li>
                    <li><strong>RM2,001+:</strong> 5% komisyen</li>
                    <li>Yuran pemprosesan: 2.9% + RM1</li>
                    <li>Yuran pengeluaran: 2%</li>
                </ul>
            </div>
            
            <div class="pricing-card">
                <div class="pricing-title">Client / Bisnes</div>
                <div class="pricing-price">PERCUMA<span></span></div>
                <p style="color: var(--text-gray);">Untuk klien yang menyiarkan gig</p>
                <ul class="pricing-features">
                    <li>Pendaftaran percuma</li>
                    <li>Siarkan unlimited gigs</li>
                    <li>Akses ke freelancers</li>
                    <li>3% yuran pemprosesan</li>
                    <li>Sistem escrow selamat</li>
                    <li>Resolusi pertikaian</li>
                </ul>
            </div>
        </div>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📋</span> Pecahan Yuran Terperinci</h2>
        
        <h3>Komisyen Freelancer (Berperingkat)</h3>
        <ul>
            <li><strong>Tier 1 (RM0 - RM500):</strong> 15% komisyen</li>
            <li><strong>Tier 2 (RM501 - RM2,000):</strong> 10% komisyen</li>
            <li><strong>Tier 3 (RM2,001+):</strong> 5% komisyen</li>
        </ul>
        
        <h3>Yuran Pemprosesan</h3>
        <ul>
            <li><strong>Yuran Transaksi:</strong> 2.9% + RM1.00 setiap transaksi</li>
            <li><strong>Yuran Pengeluaran:</strong> 2% daripada jumlah pengeluaran</li>
            <li><strong>E-wallet:</strong> RM1 tambahan untuk pengeluaran ke e-wallet</li>
        </ul>
        
        <h3>Yuran Client</h3>
        <ul>
            <li><strong>Yuran Pemprosesan:</strong> 3% daripada nilai gig</li>
            <li><strong>Deposit Escrow:</strong> Percuma</li>
            <li><strong>Refund:</strong> Tiada yuran untuk refund yang diluluskan</li>
        </ul>
        
        <div class="highlight-box">
            <p><strong>💡 Contoh:</strong> Untuk gig bernilai RM1,000, komisyen adalah 10% = RM100. Freelancer menerima RM900 sebelum yuran pemprosesan.</p>
        </div>
        
        <div class="highlight-box">
            <p><strong>💡 Nota:</strong> Semua yuran dikira secara automatik dan ditunjukkan dengan jelas sebelum pembayaran. Tiada bayaran tersembunyi!</p>
        </div>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='pricing',
                         page_title='Pricing',
                         page_subtitle='Struktur harga telus untuk freelancers dan klien',
                         content=content)

@app.route('/kategori')
def kategori():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    # Get main categories only (exclude detailed subcategories)
    categories_list = Category.query.filter(Category.slug.in_(MAIN_CATEGORY_SLUGS)).all()
    
    categories_html = '<div class="blog-grid">'
    for cat in categories_list:
        icon = cat.icon or '📁'
        categories_html += f'''
        <a href="/gigs?category={cat.slug}" class="blog-card" style="text-decoration: none;">
            <div class="blog-card-image" style="font-size: 64px;">{icon}</div>
            <div class="blog-card-content">
                <div class="blog-card-title">{cat.name}</div>
                <div class="blog-card-excerpt">{cat.description or 'Terokai peluang gig dalam kategori ini.'}</div>
            </div>
        </a>
        '''
    categories_html += '</div>'
    
    content = f'''
    <div class="content-section">
        <h2><span class="icon">📂</span> Semua Kategori</h2>
        <p>Terokai pelbagai kategori gig yang tersedia di GigHala. Sama ada anda mahir dalam design, penulisan, video editing atau tutoring - pasti ada peluang untuk anda!</p>
        
        {categories_html}
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='kategori',
                         page_title='Kategori',
                         page_subtitle='Pilih kategori mengikut kemahiran anda',
                         content=content)

@app.route('/blog')
def blog():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="blog-grid">
        <div class="blog-card">
            <div class="blog-card-image">📝</div>
            <div class="blog-card-content">
                <div class="blog-card-date">15 Disember 2025</div>
                <div class="blog-card-title">10 Tips Untuk Freelancer Baru di Malaysia</div>
                <div class="blog-card-excerpt">Baru bermula sebagai freelancer? Berikut adalah 10 tips penting untuk berjaya dalam dunia gig economy di Malaysia.</div>
            </div>
        </div>
        
        <div class="blog-card">
            <div class="blog-card-image">💰</div>
            <div class="blog-card-content">
                <div class="blog-card-date">12 Disember 2025</div>
                <div class="blog-card-title">Bagaimana Jana RM3,000 Pertama Anda</div>
                <div class="blog-card-excerpt">Kisah inspirasi freelancers yang berjaya mencapai RM3,000 pertama mereka dalam masa kurang dari 30 hari.</div>
            </div>
        </div>
        
        <div class="blog-card">
            <div class="blog-card-image">🎨</div>
            <div class="blog-card-content">
                <div class="blog-card-date">10 Disember 2025</div>
                <div class="blog-card-title">Trend Design 2025 Yang Perlu Anda Tahu</div>
                <div class="blog-card-excerpt">Ketahui trend design terkini yang dicari oleh klien pada tahun 2025 ini.</div>
            </div>
        </div>
        
        <div class="blog-card">
            <div class="blog-card-image">📱</div>
            <div class="blog-card-content">
                <div class="blog-card-date">8 Disember 2025</div>
                <div class="blog-card-title">Peluang Content Creation di TikTok</div>
                <div class="blog-card-excerpt">TikTok terus berkembang di Malaysia. Ketahui bagaimana anda boleh menjana pendapatan melalui content creation.</div>
            </div>
        </div>
        
        <div class="blog-card">
            <div class="blog-card-image">📚</div>
            <div class="blog-card-content">
                <div class="blog-card-date">5 Disember 2025</div>
                <div class="blog-card-title">Menjadi Tutor Online Yang Berjaya</div>
                <div class="blog-card-excerpt">Panduan lengkap untuk menjadi tutor online yang dicari - dari SPM hingga kemahiran profesional.</div>
            </div>
        </div>
        
        <div class="blog-card">
            <div class="blog-card-image">☪️</div>
            <div class="blog-card-content">
                <div class="blog-card-date">1 Disember 2025</div>
                <div class="blog-card-title">Mengapa Penting Memilih GigHala</div>
                <div class="blog-card-excerpt">Fahami kepentingan memilih kerja yang halal dan berkah dalam membina kerjaya freelance anda.</div>
            </div>
        </div>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='blog',
                         page_title='Blog',
                         page_subtitle='Tips, panduan dan kisah inspirasi untuk freelancers',
                         content=content)

@app.route('/panduan-freelancer')
def panduan_freelancer():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">📖</span> Panduan Lengkap Freelancer</h2>
        <p>Selamat datang ke dunia freelancing! Panduan ini akan membantu anda memulakan perjalanan sebagai freelancer di GigHala.</p>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">🚀</span> Bermula Sebagai Freelancer</h2>
        
        <h3>1. Lengkapkan Profil Anda</h3>
        <p>Profil yang lengkap adalah kunci pertama untuk menarik klien. Pastikan anda:</p>
        <ul>
            <li>Tambah foto profil profesional</li>
            <li>Tulis bio yang menarik dan jelas</li>
            <li>Senaraikan semua kemahiran anda</li>
            <li>Tambah portfolio kerja terdahulu</li>
            <li>Nyatakan pengalaman dan kelayakan</li>
        </ul>
        
        <h3>2. Tetapkan Harga Yang Kompetitif</h3>
        <p>Sebagai freelancer baru, pertimbangkan untuk:</p>
        <ul>
            <li>Mulakan dengan harga yang berpatutan untuk membina portfolio</li>
            <li>Kaji harga pasaran untuk kemahiran anda</li>
            <li>Tingkatkan harga secara beransur apabila rating meningkat</li>
        </ul>
        
        <h3>3. Tulis Proposal Yang Menarik</h3>
        <p>Proposal yang baik adalah kunci untuk mendapat gig. Tips untuk proposal menarik:</p>
        <ul>
            <li>Baca keperluan gig dengan teliti</li>
            <li>Tunjukkan pemahaman anda tentang projek</li>
            <li>Berikan contoh kerja yang relevan</li>
            <li>Nyatakan timeline yang realistik</li>
            <li>Jangan copy-paste - personalize setiap proposal</li>
        </ul>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">⭐</span> Tips Untuk Berjaya</h2>
        
        <h3>Komunikasi Yang Baik</h3>
        <p>Komunikasi adalah kunci kejayaan dalam freelancing. Pastikan anda:</p>
        <ul>
            <li>Balas mesej dengan cepat (dalam 24 jam)</li>
            <li>Tanya soalan jika tidak jelas</li>
            <li>Beri update berkala tentang kemajuan kerja</li>
            <li>Bersikap profesional dalam semua interaksi</li>
        </ul>
        
        <h3>Siapkan Kerja Berkualiti</h3>
        <ul>
            <li>Fahami keperluan klien dengan jelas</li>
            <li>Siapkan kerja sebelum deadline</li>
            <li>Semak kerja sebelum hantar</li>
            <li>Bersedia untuk revisi jika diperlukan</li>
        </ul>
        
        <h3>Bina Reputasi</h3>
        <ul>
            <li>Minta review selepas setiap projek selesai</li>
            <li>Jaga rating dengan memberikan servis terbaik</li>
            <li>Kumpul portfolio yang kukuh</li>
            <li>Bina hubungan jangka panjang dengan klien</li>
        </ul>
        
        <div class="highlight-box">
            <p><strong>💡 Pro Tip:</strong> Freelancers dengan rating 4.5+ dan profil lengkap mendapat 3x lebih banyak tawaran gig!</p>
        </div>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">💵</span> Pengurusan Kewangan</h2>
        <p>Sebagai freelancer, penting untuk menguruskan kewangan dengan baik:</p>
        <ul>
            <li><strong>Simpan rekod:</strong> Catat semua pendapatan dan perbelanjaan</li>
            <li><strong>Cukai:</strong> Fahami kewajipan cukai sebagai pekerja bebas</li>
            <li><strong>Simpanan kecemasan:</strong> Sisihkan 20% daripada pendapatan</li>
            <li><strong>Invoice:</strong> Gunakan sistem invoice yang sistematik</li>
        </ul>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='panduan-freelancer',
                         page_title='Panduan Freelancer',
                         page_subtitle='Panduan lengkap untuk berjaya sebagai freelancer di GigHala',
                         content=content)

@app.route('/faq')
def faq():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">❓</span> Soalan Lazim (FAQ)</h2>
        
        <div class="faq-item">
            <div class="faq-question">Apakah GigHala?</div>
            <div class="faq-answer">GigHala adalah platform gig economy #1 di Malaysia yang menghubungkan freelancers dengan klien. Kami fokus kepada peluang kerja yang halal dan berkah.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Adakah pendaftaran percuma?</div>
            <div class="faq-answer">Ya! Pendaftaran adalah 100% percuma untuk freelancers dan klien. Tiada bayaran tersembunyi untuk mendaftar.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Berapa komisyen yang dikenakan?</div>
            <div class="faq-answer">Untuk freelancers, komisyen standard adalah 10% daripada nilai gig. Freelancers dengan langganan Pro hanya dikenakan 5%. Klien dikenakan 3% yuran pemprosesan.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Bagaimana saya menerima bayaran?</div>
            <div class="faq-answer">Bayaran boleh dikeluarkan ke akaun bank Malaysia atau e-wallet seperti Touch 'n Go. Proses pengeluaran mengambil masa 24 jam bekerja.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Apakah maksud "Halal Verified"?</div>
            <div class="faq-answer">Gig dengan label "Halal Verified" telah disahkan mematuhi prinsip halal - tidak melibatkan aktiviti haram seperti judi, arak, atau kandungan tidak senonoh.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Adakah wang saya selamat?</div>
            <div class="faq-answer">Ya! Kami menggunakan sistem escrow di mana wang klien disimpan dengan selamat sehingga kerja disiapkan. Ini melindungi kedua-dua pihak.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Bagaimana jika ada pertikaian?</div>
            <div class="faq-answer">Kami mempunyai pasukan resolusi pertikaian yang akan membantu menyelesaikan sebarang masalah antara freelancer dan klien dengan adil.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Bolehkah saya menjadi freelancer dan klien serentak?</div>
            <div class="faq-answer">Ya! Anda boleh memilih "Kedua-duanya" semasa pendaftaran untuk mengakses ciri-ciri freelancer dan klien dalam satu akaun.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Apakah keperluan minimum untuk menjadi freelancer?</div>
            <div class="faq-answer">Anda perlu berumur 18 tahun ke atas, mempunyai akaun bank Malaysia yang sah, dan kemahiran dalam sekurang-kurangnya satu kategori yang kami tawarkan.</div>
        </div>
        
        <div class="faq-item">
            <div class="faq-question">Bagaimana cara menghubungi sokongan pelanggan?</div>
            <div class="faq-answer">Anda boleh menghubungi kami melalui email di support@gighala.com atau WhatsApp di +60 12-345 6789. Waktu operasi: Isnin-Jumaat, 9am-6pm.</div>
        </div>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='faq',
                         page_title='FAQ',
                         page_subtitle='Jawapan kepada soalan-soalan lazim tentang GigHala',
                         content=content)

@app.route('/support')
def support():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">🤝</span> Hubungi Kami</h2>
        <p>Pasukan sokongan kami sedia membantu anda. Pilih cara yang paling sesuai untuk menghubungi kami.</p>
        
        <div class="contact-grid">
            <div class="contact-card">
                <div class="icon">📧</div>
                <h4>Email</h4>
                <p>support@gighala.com</p>
                <p style="font-size: 12px; margin-top: 8px;">Balas dalam 24 jam</p>
            </div>
            
            <div class="contact-card">
                <div class="icon">📱</div>
                <h4>WhatsApp</h4>
                <p>+60 12-345 6789</p>
                <p style="font-size: 12px; margin-top: 8px;">Isnin-Jumaat, 9am-6pm</p>
            </div>
            
            <div class="contact-card">
                <div class="icon">💬</div>
                <h4>Live Chat</h4>
                <p>Chat dengan kami</p>
                <p style="font-size: 12px; margin-top: 8px;">Tersedia 24/7</p>
            </div>
        </div>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📋</span> Topik Bantuan Popular</h2>
        <ul>
            <li><a href="/faq" style="color: var(--primary);">Soalan Lazim (FAQ)</a></li>
            <li><a href="/panduan-freelancer" style="color: var(--primary);">Panduan Freelancer</a></li>
            <li><a href="/cara-kerja" style="color: var(--primary);">Cara GigHala Berfungsi</a></li>
            <li><a href="/pricing" style="color: var(--primary);">Struktur Harga</a></li>
        </ul>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">🏢</span> Alamat Pejabat</h2>
        <p><strong>Calmic Sdn Bhd</strong></p>
        <p>Level 15, Menara KL<br>
        Jalan Sultan Ismail<br>
        50250 Kuala Lumpur, Malaysia</p>
        <p style="margin-top: 16px;"><strong>Waktu Operasi:</strong> Isnin - Jumaat, 9:00 AM - 6:00 PM</p>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='support',
                         page_title='Support',
                         page_subtitle='Kami sedia membantu anda',
                         content=content)

@app.route('/feedback', methods=['GET', 'POST'])
def platform_feedback():
    """Platform feedback submission page"""
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    
    if request.method == 'POST':
        if not user:
            flash('Sila log masuk untuk menghantar maklum balas.', 'error')
            return redirect('/feedback')
        
        feedback_type = request.form.get('feedback_type', 'other')
        subject = sanitize_input(request.form.get('subject', ''), max_length=200)
        message = sanitize_input(request.form.get('message', ''), max_length=2000)
        
        if not subject or not message:
            flash('Sila isi semua medan yang diperlukan.', 'error')
            return redirect('/feedback')
        
        feedback = PlatformFeedback(
            user_id=user.id,
            feedback_type=feedback_type,
            subject=subject,
            message=message
        )
        db.session.add(feedback)
        db.session.commit()
        
        flash('Terima kasih! Maklum balas anda telah dihantar.', 'success')
        return redirect('/feedback')
    
    user_feedbacks = []
    if user:
        user_feedbacks = PlatformFeedback.query.filter_by(user_id=user.id).order_by(PlatformFeedback.created_at.desc()).limit(10).all()
    
    return render_template('feedback.html', 
                         user=user, 
                         active_page='feedback',
                         user_feedbacks=user_feedbacks,
                         lang=get_user_language(),
                         t=t)

@app.route('/syarat-terma')
def syarat_terma():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">📜</span> Syarat & Terma Perkhidmatan</h2>
        <p><em>Kemas kini terakhir: 15 Disember 2025</em></p>
        
        <h3>1. Penerimaan Terma</h3>
        <p>Dengan mengakses atau menggunakan platform GigHala, anda bersetuju untuk mematuhi Syarat & Terma ini. Jika anda tidak bersetuju dengan mana-mana bahagian terma ini, anda tidak boleh menggunakan perkhidmatan kami.</p>
        
        <h3>2. Kelayakan</h3>
        <p>Untuk menggunakan GigHala, anda mestilah:</p>
        <ul>
            <li>Berumur 18 tahun atau lebih</li>
            <li>Mempunyai kapasiti undang-undang untuk memasuki kontrak yang mengikat</li>
            <li>Bukan orang yang dilarang menggunakan perkhidmatan di bawah undang-undang Malaysia</li>
        </ul>
        
        <h3>3. Akaun Pengguna</h3>
        <p>Anda bertanggungjawab untuk:</p>
        <ul>
            <li>Mengekalkan kerahsiaan kata laluan akaun anda</li>
            <li>Semua aktiviti yang berlaku di bawah akaun anda</li>
            <li>Memberikan maklumat yang tepat dan terkini</li>
        </ul>
        
        <h3>4. Yuran & Pembayaran</h3>
        <p>GigHala mengenakan yuran berikut:</p>
        <ul>
            <li>Komisyen freelancer: 10% (standard) atau 5% (Pro)</li>
            <li>Yuran pemprosesan klien: 3%</li>
        </ul>
        <p>Semua yuran ditunjukkan dengan jelas sebelum transaksi.</p>
        
        <h3>5. Kelakuan Pengguna</h3>
        <p>Anda bersetuju untuk TIDAK:</p>
        <ul>
            <li>Melanggar undang-undang Malaysia atau antarabangsa</li>
            <li>Menyiarkan kandungan palsu, mengelirukan atau menipu</li>
            <li>Mengganggu pengguna lain</li>
            <li>Menggunakan platform untuk aktiviti haram atau tidak bermoral</li>
            <li>Cuba memintas sistem pembayaran platform</li>
        </ul>
        
        <h3>6. Hak Harta Intelek</h3>
        <p>Selepas pembayaran penuh, hak harta intelek untuk kerja yang disiapkan dipindahkan kepada klien kecuali dinyatakan sebaliknya dalam perjanjian gig.</p>
        
        <h3>7. Penyelesaian Pertikaian</h3>
        <p>Sebarang pertikaian antara pengguna akan diselesaikan melalui proses mediasi GigHala terlebih dahulu. Keputusan kami adalah muktamad.</p>
        
        <h3>8. Penamatan</h3>
        <p>GigHala berhak untuk menggantung atau menamatkan akaun anda atas sebarang pelanggaran Syarat & Terma ini.</p>
        
        <h3>9. Penafian</h3>
        <p>Platform disediakan "sebagaimana adanya". GigHala tidak menjamin ketersediaan berterusan atau bebas ralat.</p>
        
        <h3>10. Undang-undang Yang Mentadbir</h3>
        <p>Terma ini ditadbir oleh undang-undang Malaysia. Sebarang pertikaian akan diselesaikan di mahkamah Malaysia.</p>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='syarat-terma',
                         page_title='Syarat & Terma',
                         page_subtitle='Terma perkhidmatan GigHala',
                         content=content)

@app.route('/privasi')
def privasi():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">🔒</span> Polisi Privasi</h2>
        <p><em>Kemas kini terakhir: 15 Disember 2025</em></p>
        
        <h3>1. Maklumat Yang Kami Kumpul</h3>
        <p>Kami mengumpul maklumat berikut:</p>
        <ul>
            <li><strong>Maklumat Peribadi:</strong> Nama, email, nombor telefon, alamat</li>
            <li><strong>Maklumat Akaun:</strong> Username, kata laluan (encrypted), foto profil</li>
            <li><strong>Maklumat Kewangan:</strong> Butiran bank untuk pembayaran</li>
            <li><strong>Data Penggunaan:</strong> Log aktiviti, alamat IP, jenis peranti</li>
        </ul>
        
        <h3>2. Bagaimana Kami Menggunakan Maklumat</h3>
        <p>Maklumat anda digunakan untuk:</p>
        <ul>
            <li>Menyediakan dan mengekalkan perkhidmatan kami</li>
            <li>Memproses transaksi dan pembayaran</li>
            <li>Berkomunikasi dengan anda tentang akaun anda</li>
            <li>Meningkatkan perkhidmatan kami</li>
            <li>Mematuhi keperluan undang-undang</li>
        </ul>
        
        <h3>3. Perkongsian Maklumat</h3>
        <p>Kami TIDAK menjual maklumat peribadi anda. Kami mungkin berkongsi maklumat dengan:</p>
        <ul>
            <li>Penyedia perkhidmatan pembayaran (untuk memproses transaksi)</li>
            <li>Pihak berkuasa undang-undang (jika dikehendaki oleh undang-undang)</li>
            <li>Pengguna lain (maklumat profil awam sahaja)</li>
        </ul>
        
        <h3>4. Keselamatan Data</h3>
        <p>Kami mengambil langkah keselamatan yang serius:</p>
        <ul>
            <li>Enkripsi SSL untuk semua data dalam transit</li>
            <li>Kata laluan di-hash menggunakan algoritma selamat</li>
            <li>Akses terhad kepada data peribadi</li>
            <li>Pemantauan keselamatan berterusan</li>
        </ul>
        
        <h3>5. Hak Anda</h3>
        <p>Anda mempunyai hak untuk:</p>
        <ul>
            <li>Mengakses maklumat peribadi anda</li>
            <li>Membetulkan maklumat yang tidak tepat</li>
            <li>Meminta pemadaman akaun</li>
            <li>Menarik balik persetujuan untuk komunikasi pemasaran</li>
        </ul>
        
        <h3>6. Cookies</h3>
        <p>Kami menggunakan cookies untuk:</p>
        <ul>
            <li>Mengekalkan sesi log masuk anda</li>
            <li>Mengingat pilihan bahasa anda</li>
            <li>Menganalisis penggunaan laman web</li>
        </ul>
        
        <h3>7. Penyimpanan Data</h3>
        <p>Data anda disimpan selagi akaun anda aktif. Selepas pemadaman akaun, data dikekalkan selama 30 hari sebelum dipadam sepenuhnya.</p>
        
        <h3>8. Sumber Pengumpulan Data</h3>
        <p>Kami mengumpul data peribadi anda secara langsung daripada anda apabila anda mendaftar atau menggunakan perkhidmatan kami, dan secara automatik melalui peranti anda (contoh: alamat IP dan log penggunaan).</p>
        
        <h3>9. Data Wajib</h3>
        <p>Pemberian data peribadi tertentu (contoh: butiran hubungan dan pembayaran) adalah wajib untuk kami memproses pendaftaran dan transaksi anda. Kegagalan memberikan data tersebut mungkin bermakna kami tidak dapat menyediakan perkhidmatan yang diminta.</p>
        
        <h3>10. Pemindahan Data Antarabangsa</h3>
        <p>Data anda mungkin dipindahkan dan disimpan dalam server di luar Malaysia (contoh: di Amerika Syarikat). Kami memastikan pemindahan mematuhi keperluan PDPA melalui perlindungan yang mencukupi atau kontrak yang sesuai.</p>
        
        <h3>11. Data Peribadi Sensitif</h3>
        <p>Jika kami mengumpul data peribadi sensitif (seperti data biometrik atau maklumat kesihatan), kami akan mendapatkan persetujuan eksplisit anda secara berasingan.</p>
        
        <h3>12. Pemberitahuan Pelanggaran Data</h3>
        <p>Sekiranya berlaku pelanggaran data peribadi yang boleh menyebabkan kemudaratan yang ketara, kami dikehendaki untuk memberitahu Pesuruhjaya Perlindungan Data Peribadi (JPDP) dalam masa 72 jam dan memaklumkan anda jika perlu.</p>
        
        <h3>13. Pegawai Perlindungan Data (DPO)</h3>
        <p>Kami telah melantik Pegawai Perlindungan Data (DPO) yang bertanggungjawab untuk mengawasi pematuhan dengan PDPA.</p>
        <p><strong>Hubungi DPO:</strong></p>
        <ul>
            <li>Email: dpo@gighala.com</li>
            <li>Telefon: +60 3-XXXX XXXX</li>
        </ul>
        
        <h3>14. Hubungi Kami</h3>
        <p>Untuk soalan tentang privasi, hubungi: privacy@gighala.com</p>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='privasi',
                         page_title='Polisi Privasi',
                         page_subtitle='Bagaimana kami melindungi maklumat anda',
                         content=content)

@app.route('/halal-compliance')
def halal_compliance():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">☪️</span> Pematuhan Halal</h2>
        <p>GigHala komited untuk menyediakan platform yang mematuhi prinsip-prinsip Islam. Berikut adalah garis panduan pematuhan halal kami.</p>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">✅</span> Prinsip Halal Kami</h2>
        
        <h3>1. Tiada Aktiviti Haram</h3>
        <p>Kami TIDAK membenarkan gig yang melibatkan:</p>
        <ul>
            <li>Perjudian atau pertaruhan</li>
            <li>Arak, rokok atau dadah</li>
            <li>Kandungan lucah atau tidak senonoh</li>
            <li>Riba atau skim cepat kaya</li>
            <li>Penipuan atau aktiviti menipu</li>
            <li>Kandungan yang menghina agama</li>
        </ul>
        
        <h3>2. Sistem Halal Verified</h3>
        <p>Gig dengan label "Halal Verified" telah melalui proses semakan untuk memastikan:</p>
        <ul>
            <li>Tidak melanggar prinsip syariah</li>
            <li>Kandungan dan tujuan adalah halal</li>
            <li>Klien dan produk/perkhidmatan adalah halal</li>
        </ul>
        
        <h3>3. Proses Pengesahan</h3>
        <p>Untuk mendapat status Halal Verified:</p>
        <ul>
            <li>Gig disemak oleh pasukan pematuhan kami</li>
            <li>Kategori dan deskripsi dinilai</li>
            <li>Klien dan tujuan projek disahkan</li>
            <li>Status boleh ditarik balik jika melanggar garis panduan</li>
        </ul>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📋</span> Garis Panduan Kategori</h2>
        
        <h3>Kategori Yang Dibenarkan</h3>
        <ul>
            <li>✓ Design & Kreatif (dengan kandungan yang sopan)</li>
            <li>✓ Penulisan & Terjemahan (bukan untuk kandungan haram)</li>
            <li>✓ Video & Animasi (kandungan yang sesuai)</li>
            <li>✓ Pembangunan Web (bukan untuk laman web haram)</li>
            <li>✓ Pemasaran Digital (produk/perkhidmatan halal)</li>
            <li>✓ Tunjuk Ajar & Pendidikan</li>
            <li>✓ Admin & Sokongan</li>
        </ul>
        
        <h3>Kategori Yang TIDAK Dibenarkan</h3>
        <ul>
            <li>✗ Kandungan dewasa atau lucah</li>
            <li>✗ Promosi alkohol, rokok atau dadah</li>
            <li>✗ Platform perjudian</li>
            <li>✗ Perkhidmatan kewangan berasaskan riba</li>
            <li>✗ Kandungan yang menghina mana-mana agama</li>
        </ul>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">🤝</span> Komitmen Kami</h2>
        
        <div class="highlight-box">
            <p><strong>Misi Kami:</strong> Menyediakan platform gig economy yang membolehkan umat Islam menjana pendapatan yang halal dan berkah, sambil memastikan semua aktiviti mematuhi prinsip syariah.</p>
        </div>
        
        <p>Kami bekerjasama dengan penasihat syariah untuk memastikan platform kami terus mematuhi garis panduan Islam. Jika anda mempunyai sebarang soalan atau kebimbangan tentang pematuhan halal, sila hubungi kami di halal@gighala.com.</p>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📣</span> Laporkan Pelanggaran</h2>
        <p>Jika anda menjumpai gig yang tidak mematuhi prinsip halal, sila laporkan kepada kami. Kami akan menyiasat dan mengambil tindakan yang sewajarnya.</p>
        <p>Email: halal@gighala.com</p>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='halal-compliance',
                         page_title='Halal Compliance',
                         page_subtitle='Komitmen kami terhadap pematuhan prinsip halal',
                         content=content)

@app.route('/gig-workers-bill')
def gig_workers_bill():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">📜</span> Rang Undang-undang Pekerja Gig</h2>
        <p>GigHala menyokong hak-hak pekerja gig dan mematuhi peraturan yang ditetapkan oleh kerajaan Malaysia.</p>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">⚖️</span> Hak-hak Pekerja Gig</h2>
        
        <h3>Perlindungan Sosial</h3>
        <p>Selaras dengan inisiatif kerajaan, kami menyokong:</p>
        <ul>
            <li>Caruman PERKESO untuk pekerja gig</li>
            <li>Skim perlindungan kemalangan pekerjaan</li>
            <li>Akses kepada faedah kesihatan</li>
        </ul>
        
        <h3>Bayaran Adil</h3>
        <p>Kami memastikan:</p>
        <ul>
            <li>Struktur bayaran yang telus</li>
            <li>Tiada pemotongan tersembunyi</li>
            <li>Pembayaran tepat pada masanya</li>
            <li>Sistem escrow untuk perlindungan</li>
        </ul>
        
        <h3>Kebebasan & Fleksibiliti</h3>
        <p>Sebagai pekerja gig di GigHala, anda menikmati:</p>
        <ul>
            <li>Kebebasan memilih gig</li>
            <li>Fleksibiliti waktu kerja</li>
            <li>Tiada komitmen jangka panjang</li>
            <li>Kawalan penuh ke atas jadual anda</li>
        </ul>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📋</span> Pematuhan Peraturan</h2>
        
        <h3>Akta Pekerjaan 1955</h3>
        <p>Walaupun pekerja gig mempunyai status yang berbeza daripada pekerja tetap, kami memastikan platform kami beroperasi dalam rangka kerja undang-undang Malaysia.</p>
        
        <h3>Perlindungan Data Peribadi</h3>
        <p>Kami mematuhi Akta Perlindungan Data Peribadi 2010 (PDPA) dalam mengendalikan maklumat pengguna.</p>
        
        <h3>Cukai</h3>
        <p>Freelancers bertanggungjawab untuk:</p>
        <ul>
            <li>Mengisytiharkan pendapatan kepada LHDN</li>
            <li>Membayar cukai yang berkenaan</li>
            <li>Menyimpan rekod pendapatan</li>
        </ul>
        
        <div class="highlight-box">
            <p><strong>💡 Nota:</strong> GigHala menyediakan penyata pendapatan tahunan untuk membantu anda dengan pengisytiharan cukai.</p>
        </div>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">🔮</span> Perkembangan Masa Hadapan</h2>
        <p>Kami sentiasa mengikuti perkembangan peraturan berkaitan ekonomi gig di Malaysia. Kami komited untuk:</p>
        <ul>
            <li>Mematuhi peraturan baru yang diperkenalkan</li>
            <li>Bekerjasama dengan pihak berkuasa</li>
            <li>Melindungi hak-hak pengguna platform kami</li>
            <li>Menyediakan sumber dan panduan terkini</li>
        </ul>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📞</span> Maklumat Lanjut</h2>
        <p>Untuk maklumat lanjut tentang hak-hak anda sebagai pekerja gig, sila rujuk:</p>
        <ul>
            <li>Kementerian Sumber Manusia Malaysia</li>
            <li>PERKESO (Pertubuhan Keselamatan Sosial)</li>
            <li>LHDN (Lembaga Hasil Dalam Negeri)</li>
        </ul>
        <p style="margin-top: 16px;">Atau hubungi kami di: legal@gighala.com</p>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='gig-workers-bill',
                         page_title='Gig Workers Bill',
                         page_subtitle='Hak-hak dan perlindungan untuk pekerja gig',
                         content=content)

# ============================================
# PORTFOLIO ROUTES
# ============================================

@app.route('/portfolio')
@page_login_required
def portfolio():
    """View and manage user portfolio"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    portfolio_items = PortfolioItem.query.filter_by(user_id=user_id).order_by(PortfolioItem.display_order, PortfolioItem.created_at.desc()).all()
    # Get main categories only (exclude detailed subcategories)
    categories = Category.query.filter(Category.slug.in_(MAIN_CATEGORY_SLUGS)).all()
    return render_template('portfolio.html', user=user, portfolio_items=portfolio_items, categories=categories, active_page='portfolio', lang=get_user_language(), t=t)

@app.route('/api/portfolio', methods=['POST'])
@login_required
def add_portfolio_item():
    """Add a new portfolio item"""
    try:
        user_id = session['user_id']
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        external_url = request.form.get('external_url', '').strip()
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        image_filename = None
        image_path = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{user_id}_{uuid.uuid4().hex}_{file.filename}")
                portfolio_folder = os.path.join(UPLOAD_FOLDER, 'portfolio')
                os.makedirs(portfolio_folder, exist_ok=True)
                file_path = os.path.join(portfolio_folder, filename)
                file.save(file_path)
                image_filename = filename
                image_path = file_path
        
        item = PortfolioItem(
            user_id=user_id,
            title=title,
            description=description,
            category=category,
            external_url=external_url,
            image_filename=image_filename,
            image_path=image_path
        )
        db.session.add(item)
        db.session.commit()
        
        return jsonify({'success': True, 'item': item.to_dict()}), 201
    except Exception as e:
        app.logger.error(f"Portfolio add error: {str(e)}")
        return jsonify({'error': 'Failed to add portfolio item'}), 500

@app.route('/api/portfolio/<int:item_id>', methods=['DELETE'])
@login_required
def delete_portfolio_item(item_id):
    """Delete a portfolio item"""
    try:
        user_id = session['user_id']
        item = PortfolioItem.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        if item.image_path and os.path.exists(item.image_path):
            os.remove(item.image_path)
        
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        app.logger.error(f"Portfolio delete error: {str(e)}")
        return jsonify({'error': 'Failed to delete item'}), 500

@app.route('/profile/<username>')
def public_profile(username):
    """View public user profile with portfolio"""
    profile_user = User.query.filter_by(username=username).first_or_404()
    portfolio_items = PortfolioItem.query.filter_by(user_id=profile_user.id).order_by(PortfolioItem.display_order, PortfolioItem.created_at.desc()).all()
    reviews = Review.query.filter_by(reviewee_id=profile_user.id).order_by(Review.created_at.desc()).limit(10).all()
    current_user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    
    review_details = []
    for review in reviews:
        reviewer = User.query.get(review.reviewer_id)
        gig = Gig.query.get(review.gig_id)
        review_details.append({
            'rating': review.rating,
            'comment': review.comment,
            'reviewer_name': reviewer.full_name or reviewer.username if reviewer else 'Unknown',
            'gig_title': gig.title if gig else 'Unknown Gig',
            'created_at': review.created_at
        })
    
    return render_template('public_profile.html', profile_user=profile_user, portfolio_items=portfolio_items, reviews=review_details, user=current_user, active_page='profile', lang=get_user_language(), t=t)

# ============================================
# CHAT/MESSAGING ROUTES
# ============================================

@app.route('/support/message')
@login_required
def message_support():
    """Start a conversation with support"""
    try:
        user_id = session['user_id']
        
        support_user = User.query.filter_by(username='support').first()
        if not support_user:
            support_user = User(
                username='support',
                email='support@gighala.local',
                password_hash='disabled',
                full_name='GigHala Support',
                is_verified=True
            )
            db.session.add(support_user)
            db.session.flush()
        
        existing = Conversation.query.filter(
            ((Conversation.participant_1_id == user_id) & (Conversation.participant_2_id == support_user.id)) |
            ((Conversation.participant_1_id == support_user.id) & (Conversation.participant_2_id == user_id))
        ).first()
        
        if existing:
            conv_id = existing.id
        else:
            conv = Conversation(
                participant_1_id=user_id,
                participant_2_id=support_user.id
            )
            db.session.add(conv)
            db.session.commit()
            conv_id = conv.id
        
        db.session.commit()
        return redirect(f'/messages/{conv_id}')
    except Exception as e:
        app.logger.error(f"Error starting support conversation: {str(e)}")
        return redirect('/messages')

@app.route('/messages')
@page_login_required
def messages():
    """View all conversations"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    conversations = Conversation.query.filter(
        ((Conversation.participant_1_id == user_id) & (Conversation.is_archived_by_1 == False)) |
        ((Conversation.participant_2_id == user_id) & (Conversation.is_archived_by_2 == False))
    ).order_by(Conversation.last_message_at.desc()).all()
    
    conversation_list = []
    for conv in conversations:
        other_user_id = conv.participant_2_id if conv.participant_1_id == user_id else conv.participant_1_id
        other_user = User.query.get(other_user_id)
        last_message = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.desc()).first()
        unread_count = Message.query.filter_by(conversation_id=conv.id, is_read=False).filter(Message.sender_id != user_id).count()
        gig = Gig.query.get(conv.gig_id) if conv.gig_id else None
        
        conversation_list.append({
            'id': conv.id,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count,
            'gig': gig,
            'last_message_at': conv.last_message_at
        })
    
    return render_template('messages.html', user=user, conversations=conversation_list, active_page='messages', lang=get_user_language(), t=t)

@app.route('/messages/<int:conversation_id>')
@page_login_required
def view_conversation(conversation_id):
    """View a specific conversation"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    conv = Conversation.query.get_or_404(conversation_id)
    if conv.participant_1_id != user_id and conv.participant_2_id != user_id:
        return redirect('/messages')
    
    other_user_id = conv.participant_2_id if conv.participant_1_id == user_id else conv.participant_1_id
    other_user = User.query.get(other_user_id)
    
    messages_list = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at.asc()).all()
    
    Message.query.filter_by(conversation_id=conversation_id, is_read=False).filter(Message.sender_id != user_id).update({'is_read': True, 'read_at': datetime.utcnow()})
    db.session.commit()
    
    gig = Gig.query.get(conv.gig_id) if conv.gig_id else None
    
    return render_template('conversation.html', user=user, conversation=conv, other_user=other_user, messages=messages_list, gig=gig, active_page='messages', lang=get_user_language(), t=t)

@app.route('/api/messages/send', methods=['POST'])
@login_required
def send_message():
    """Send a new message"""
    try:
        user_id = session['user_id']
        data = request.json
        conversation_id = data.get('conversation_id')
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Check for blocked contact information (phone numbers, emails)
        is_blocked, block_reason = contains_blocked_contact_info(content)
        if is_blocked:
            return jsonify({'error': block_reason}), 400

        conv = Conversation.query.get(conversation_id)
        if not conv or (conv.participant_1_id != user_id and conv.participant_2_id != user_id):
            return jsonify({'error': 'Conversation not found'}), 404
        
        message = Message(
            conversation_id=conversation_id,
            sender_id=user_id,
            content=content
        )
        conv.last_message_at = datetime.utcnow()
        db.session.add(message)
        db.session.commit()
        
        other_user_id = conv.participant_2_id if conv.participant_1_id == user_id else conv.participant_1_id
        notification = Notification(
            user_id=other_user_id,
            notification_type='message',
            title='New Message',
            message=f'You have a new message',
            link=f'/messages/{conversation_id}',
            related_id=message.id
        )
        db.session.add(notification)
        db.session.commit()

        # Send email and SMS notifications for new message
        sender = User.query.get(message.sender_id)
        recipient = User.query.get(other_user_id)

        if sender and recipient:
            # Get gig context if available
            gig = Gig.query.get(conv.gig_id) if conv.gig_id else None

            try:
                subject = f"New Message from {sender.full_name or sender.username}"
                msg_preview = content[:100] + "..." if len(content) > 100 else content

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9f9f9; }}
                        .message-preview {{ background-color: #fff; border-left: 4px solid #3498db; padding: 15px; margin: 15px 0; font-style: italic; }}
                        .footer {{ padding: 20px; text-align: center; font-size: 12px; color: #777; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>New Message</h2>
                        </div>
                        <div class="content">
                            <p>Hi {recipient.full_name or recipient.username},</p>
                            <p>You have received a new message from <strong>{sender.full_name or sender.username}</strong>{f' regarding "{gig.title}"' if gig else ''}.</p>
                            <div class="message-preview">{msg_preview}</div>
                            <p>Login to your dashboard to read and reply to this message.</p>
                        </div>
                        <div class="footer">
                            <p>GigHala - Your Trusted Halal Gig Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
New Message

Hi {recipient.full_name or recipient.username},

You have received a new message from {sender.full_name or sender.username}{f' regarding "{gig.title}"' if gig else ''}.

Message Preview:
{msg_preview}

Login to your dashboard to read and reply.

---
GigHala - Your Trusted Halal Gig Platform
                """.strip()

                email_service.send_single_email(
                    to_email=recipient.email,
                    to_name=recipient.full_name or recipient.username,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                app.logger.info(f"Sent message notification email to user {recipient.id}")

            except Exception as e:
                app.logger.error(f"Failed to send message notification email: {str(e)}")

            # Send SMS notification if phone is verified
            if recipient.phone and recipient.phone_verified:
                sms_text = f"GigHala: New message from {sender.full_name or sender.username}{f' about {gig.title}' if gig else ''}. Login to reply."
                send_transaction_sms_notification(recipient.phone, sms_text)
                app.logger.info(f"Sent message notification SMS to user {recipient.id}")

        msg_data = message.to_dict()
        msg_data['sender_name'] = sender.full_name or sender.username if sender else 'Unknown'
        msg_data['sender_username'] = sender.username if sender else 'unknown'
        return jsonify({'success': True, 'message': msg_data}), 201
    except Exception as e:
        app.logger.error(f"Send message error: {str(e)}")
        return jsonify({'error': 'Failed to send message'}), 500

@app.route('/api/messages/start', methods=['POST'])
@login_required
def start_conversation():
    """Start a new conversation"""
    try:
        user_id = session['user_id']
        data = request.json
        other_user_id = data.get('user_id')
        gig_id = data.get('gig_id')
        initial_message = data.get('message', '').strip()

        if not other_user_id or other_user_id == user_id:
            return jsonify({'error': 'Invalid recipient'}), 400

        # Check for blocked contact information in initial message
        if initial_message:
            is_blocked, block_reason = contains_blocked_contact_info(initial_message)
            if is_blocked:
                return jsonify({'error': block_reason}), 400
        
        existing = Conversation.query.filter(
            ((Conversation.participant_1_id == user_id) & (Conversation.participant_2_id == other_user_id)) |
            ((Conversation.participant_1_id == other_user_id) & (Conversation.participant_2_id == user_id))
        ).first()
        
        if existing:
            if gig_id:
                existing.gig_id = gig_id
            if initial_message:
                message = Message(conversation_id=existing.id, sender_id=user_id, content=initial_message)
                existing.last_message_at = datetime.utcnow()
                db.session.add(message)
            db.session.commit()
            return jsonify({'success': True, 'conversation_id': existing.id}), 200
        
        conv = Conversation(
            participant_1_id=user_id,
            participant_2_id=other_user_id,
            gig_id=gig_id
        )
        db.session.add(conv)
        db.session.commit()
        
        if initial_message:
            message = Message(conversation_id=conv.id, sender_id=user_id, content=initial_message)
            db.session.add(message)
            db.session.commit()
        
        return jsonify({'success': True, 'conversation_id': conv.id}), 201
    except Exception as e:
        app.logger.error(f"Start conversation error: {str(e)}")
        return jsonify({'error': 'Failed to start conversation'}), 500

@app.route('/api/messages/message-admin', methods=['POST'])
@login_required
def message_admin():
    """Start a conversation with the first admin"""
    try:
        user_id = session['user_id']
        
        # Find the first admin user
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            return jsonify({'error': 'No admin available'}), 404
        
        if admin.id == user_id:
            return jsonify({'error': 'You are an admin'}), 400
        
        # Check if conversation already exists
        existing = Conversation.query.filter(
            ((Conversation.participant_1_id == user_id) & (Conversation.participant_2_id == admin.id)) |
            ((Conversation.participant_1_id == admin.id) & (Conversation.participant_2_id == user_id))
        ).first()
        
        if existing:
            return jsonify({'success': True, 'conversation_id': existing.id}), 200
        
        # Create new conversation
        conv = Conversation(
            participant_1_id=user_id,
            participant_2_id=admin.id
        )
        db.session.add(conv)
        db.session.commit()
        
        return jsonify({'success': True, 'conversation_id': conv.id}), 201
    except Exception as e:
        app.logger.error(f"Message admin error: {str(e)}")
        return jsonify({'error': 'Failed to start conversation'}), 500

@app.route('/api/messages/poll/<int:conversation_id>')
@login_required
def poll_messages(conversation_id):
    """Poll for new messages"""
    user_id = session['user_id']
    last_id = request.args.get('last_id', 0, type=int)
    
    conv = Conversation.query.get(conversation_id)
    if not conv or (conv.participant_1_id != user_id and conv.participant_2_id != user_id):
        return jsonify({'error': 'Conversation not found'}), 404
    
    new_messages = Message.query.filter(
        Message.conversation_id == conversation_id,
        Message.id > last_id
    ).order_by(Message.created_at.asc()).all()
    
    Message.query.filter_by(conversation_id=conversation_id, is_read=False).filter(Message.sender_id != user_id).update({'is_read': True, 'read_at': datetime.utcnow()})
    db.session.commit()
    
    return jsonify({'messages': [m.to_dict() for m in new_messages]})

# ============================================
# NOTIFICATION ROUTES
# ============================================

@app.route('/notifications')
@page_login_required
def notifications_page():
    """View all notifications"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(50).all()
    return render_template('notifications.html', user=user, notifications=notifications, active_page='notifications', lang=get_user_language(), t=t)

@app.route('/api/notifications')
@login_required
def get_notifications():
    """Get user notifications"""
    user_id = session['user_id']
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    
    notifications = query.order_by(Notification.created_at.desc()).limit(20).all()
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': unread_count
    })

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark notifications as read"""
    user_id = session['user_id']
    data = request.json
    notification_ids = data.get('ids', [])
    
    if notification_ids:
        Notification.query.filter(Notification.id.in_(notification_ids), Notification.user_id == user_id).update({'is_read': True, 'read_at': datetime.utcnow()}, synchronize_session=False)
    else:
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True, 'read_at': datetime.utcnow()})
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Get or update notification preferences"""
    user_id = session['user_id']
    
    prefs = NotificationPreference.query.filter_by(user_id=user_id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=user_id)
        db.session.add(prefs)
        db.session.commit()
    
    if request.method == 'GET':
        return jsonify({
            'push_enabled': prefs.push_enabled,
            'email_new_gig': prefs.email_new_gig,
            'email_message': prefs.email_message,
            'email_payment': prefs.email_payment,
            'email_review': prefs.email_review,
            'push_new_gig': prefs.push_new_gig,
            'push_message': prefs.push_message,
            'push_payment': prefs.push_payment,
            'push_review': prefs.push_review
        })
    
    data = request.json
    for key in ['push_enabled', 'email_new_gig', 'email_message', 'email_payment', 'email_review', 'push_new_gig', 'push_message', 'push_payment', 'push_review']:
        if key in data:
            setattr(prefs, key, data[key])
    
    db.session.commit()
    return jsonify({'success': True})

# ============================================
# IDENTITY VERIFICATION ROUTES
# ============================================

@app.route('/verification')
@page_login_required
def verification_page():
    """Identity verification page"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    verification = IdentityVerification.query.filter_by(user_id=user_id).order_by(IdentityVerification.created_at.desc()).first()
    return render_template('verification.html', user=user, verification=verification, active_page='verification', lang=get_user_language(), t=t)

@app.route('/api/verification/submit', methods=['POST'])
@login_required
def submit_verification():
    """Submit identity verification"""
    try:
        user_id = session['user_id']
        
        existing = IdentityVerification.query.filter_by(user_id=user_id, status='pending').first()
        if existing:
            return jsonify({'error': 'You already have a pending verification'}), 400
        
        ic_number = request.form.get('ic_number', '').strip()
        full_name = request.form.get('full_name', '').strip()
        
        if not ic_number or not full_name:
            return jsonify({'error': 'IC number and full name are required'}), 400
        
        if not re.match(r'^\d{12}$', ic_number):
            return jsonify({'error': 'Invalid IC number format (12 digits required)'}), 400
        
        verification_folder = os.path.join(UPLOAD_FOLDER, 'verification')
        os.makedirs(verification_folder, exist_ok=True)
        
        ic_front = ic_back = selfie = None
        
        for field, attr in [('ic_front', 'ic_front_image'), ('ic_back', 'ic_back_image'), ('selfie', 'selfie_image')]:
            if field in request.files:
                file = request.files[field]
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{user_id}_{field}_{uuid.uuid4().hex}_{file.filename}")
                    file_path = os.path.join(verification_folder, filename)
                    file.save(file_path)
                    if field == 'ic_front':
                        ic_front = f'/uploads/verification/{filename}'
                    elif field == 'ic_back':
                        ic_back = f'/uploads/verification/{filename}'
                    else:
                        selfie = f'/uploads/verification/{filename}'
        
        verification = IdentityVerification(
            user_id=user_id,
            ic_number=ic_number,
            full_name=full_name,
            ic_front_image=ic_front,
            ic_back_image=ic_back,
            selfie_image=selfie
        )
        db.session.add(verification)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Verification submitted successfully'}), 201
    except Exception as e:
        app.logger.error(f"Verification submit error: {str(e)}")
        return jsonify({'error': 'Failed to submit verification'}), 500

@app.route('/admin/verifications')
@page_login_required
def admin_verifications():
    """Admin page for reviewing verifications"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user.is_admin:
        return redirect('/dashboard')
    
    pending = IdentityVerification.query.filter_by(status='pending').order_by(IdentityVerification.created_at.asc()).all()
    recent = IdentityVerification.query.filter(IdentityVerification.status != 'pending').order_by(IdentityVerification.updated_at.desc()).limit(20).all()
    
    return render_template('admin_verifications.html', user=user, pending=pending, recent=recent, active_page='admin', lang=get_user_language(), t=t)

@app.route('/api/admin/verification/<int:verification_id>', methods=['POST'])
@admin_required
def review_verification(verification_id):
    """Approve or reject verification"""
    try:
        admin_id = session['user_id']
        data = request.json
        action = data.get('action')
        reason = data.get('reason', '')
        
        verification = IdentityVerification.query.get_or_404(verification_id)
        
        # Check if documents are uploaded before allowing approval
        if action == 'approve' and (not verification.ic_front_image or not verification.ic_back_image):
            return jsonify({'error': 'Cannot verify user without uploaded IC/passport documents (front and back).'}), 400
        
        if action == 'approve':
            verification.status = 'approved'
            verification.verified_at = datetime.utcnow()
            verification.verified_by = admin_id
            
            user = User.query.get(verification.user_id)
            user.is_verified = True
            user.ic_number = verification.ic_number
            
            notification = Notification(
                user_id=verification.user_id,
                notification_type='verification',
                title='Identity Verified',
                message='Your identity has been verified successfully!',
                link='/settings'
            )
            db.session.add(notification)
            
        elif action == 'reject':
            verification.status = 'rejected'
            verification.rejection_reason = reason
            
            notification = Notification(
                user_id=verification.user_id,
                notification_type='verification',
                title='Verification Rejected',
                message=f'Your verification was rejected: {reason}',
                link='/verification'
            )
            db.session.add(notification)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Verification review error: {str(e)}")
        return jsonify({'error': 'Failed to process verification'}), 500

# ============================================
# DISPUTE RESOLUTION ROUTES
# ============================================

@app.route('/disputes')
@page_login_required
def disputes_page():
    """View user's disputes"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    disputes = Dispute.query.filter(
        (Dispute.filed_by_id == user_id) | (Dispute.against_id == user_id)
    ).order_by(Dispute.created_at.desc()).all()
    
    dispute_list = []
    for d in disputes:
        gig = Gig.query.get(d.gig_id)
        other_user = User.query.get(d.against_id if d.filed_by_id == user_id else d.filed_by_id)
        dispute_list.append({
            'dispute': d,
            'gig': gig,
            'other_user': other_user,
            'is_filer': d.filed_by_id == user_id
        })
    
    return render_template('disputes.html', user=user, disputes=dispute_list, active_page='disputes', lang=get_user_language(), t=t)

@app.route('/dispute/<int:dispute_id>')
@page_login_required
def view_dispute(dispute_id):
    """View a specific dispute"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    dispute = Dispute.query.get_or_404(dispute_id)
    if dispute.filed_by_id != user_id and dispute.against_id != user_id and not user.is_admin:
        return redirect('/disputes')
    
    gig = Gig.query.get(dispute.gig_id)
    filer = User.query.get(dispute.filed_by_id)
    against = User.query.get(dispute.against_id)
    messages = DisputeMessage.query.filter_by(dispute_id=dispute_id).order_by(DisputeMessage.created_at.asc()).all()
    
    message_list = []
    for m in messages:
        sender = User.query.get(m.sender_id)
        message_list.append({
            'message': m,
            'sender': sender
        })
    
    return render_template('dispute_detail.html', user=user, dispute=dispute, gig=gig, filer=filer, against=against, messages=message_list, active_page='disputes', lang=get_user_language(), t=t)

@app.route('/dispute/new/<int:gig_id>')
@page_login_required
def new_dispute(gig_id):
    """File a new dispute"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    gig = Gig.query.get_or_404(gig_id)
    
    if gig.client_id != user_id and gig.freelancer_id != user_id:
        return redirect('/dashboard')
    
    other_user_id = gig.freelancer_id if gig.client_id == user_id else gig.client_id
    other_user = User.query.get(other_user_id)
    escrow = Escrow.query.filter_by(gig_id=gig_id).first()
    
    return render_template('dispute_new.html', user=user, gig=gig, other_user=other_user, escrow=escrow, active_page='disputes', lang=get_user_language(), t=t)

@app.route('/api/dispute/file', methods=['POST'])
@login_required
def file_dispute():
    """File a new dispute"""
    try:
        user_id = session['user_id']
        data = request.json
        
        gig_id = data.get('gig_id')
        dispute_type = data.get('dispute_type')
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not all([gig_id, dispute_type, title, description]):
            return jsonify({'error': 'All fields are required'}), 400
        
        gig = Gig.query.get(gig_id)
        if not gig or (gig.client_id != user_id and gig.freelancer_id != user_id):
            return jsonify({'error': 'Invalid gig'}), 400
        
        against_id = gig.freelancer_id if gig.client_id == user_id else gig.client_id
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        
        dispute_number = f"DIS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        dispute = Dispute(
            dispute_number=dispute_number,
            gig_id=gig_id,
            escrow_id=escrow.id if escrow else None,
            filed_by_id=user_id,
            against_id=against_id,
            dispute_type=dispute_type,
            title=title,
            description=description
        )
        db.session.add(dispute)
        
        if escrow:
            escrow.status = 'disputed'
        
        notification = Notification(
            user_id=against_id,
            notification_type='dispute',
            title='Dispute Filed Against You',
            message=f'A dispute has been filed regarding: {gig.title}',
            link=f'/dispute/{dispute.id}',
            related_id=dispute.id
        )
        db.session.add(notification)
        
        db.session.commit()
        return jsonify({'success': True, 'dispute_id': dispute.id}), 201
    except Exception as e:
        app.logger.error(f"File dispute error: {str(e)}")
        return jsonify({'error': 'Failed to file dispute'}), 500

@app.route('/api/dispute/<int:dispute_id>/message', methods=['POST'])
@login_required
def add_dispute_message(dispute_id):
    """Add a message to a dispute"""
    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        data = request.json
        message_text = data.get('message', '').strip()

        if not message_text:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Check for blocked contact information (phone numbers, emails)
        is_blocked, block_reason = contains_blocked_contact_info(message_text)
        if is_blocked:
            return jsonify({'error': block_reason}), 400

        dispute = Dispute.query.get_or_404(dispute_id)
        if dispute.filed_by_id != user_id and dispute.against_id != user_id and not user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        message = DisputeMessage(
            dispute_id=dispute_id,
            sender_id=user_id,
            message=message_text,
            is_admin=user.is_admin
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({'success': True}), 201
    except Exception as e:
        app.logger.error(f"Dispute message error: {str(e)}")
        return jsonify({'error': 'Failed to add message'}), 500

@app.route('/admin/disputes')
@page_login_required
def admin_disputes():
    """Admin page for managing disputes"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user.is_admin:
        return redirect('/dashboard')
    
    open_disputes = Dispute.query.filter(Dispute.status.in_(['open', 'under_review', 'awaiting_response'])).order_by(Dispute.created_at.asc()).all()
    resolved_disputes = Dispute.query.filter(Dispute.status.in_(['resolved', 'closed'])).order_by(Dispute.resolved_at.desc()).limit(20).all()
    
    return render_template('admin_disputes.html', user=user, open_disputes=open_disputes, resolved_disputes=resolved_disputes, active_page='admin', lang=get_user_language(), t=t)

@app.route('/api/admin/dispute/<int:dispute_id>/resolve', methods=['POST'])
@admin_required
def resolve_dispute(dispute_id):
    """Resolve a dispute"""
    try:
        admin_id = session['user_id']
        data = request.json
        
        resolution_type = data.get('resolution_type')
        resolution = data.get('resolution', '').strip()
        
        dispute = Dispute.query.get_or_404(dispute_id)
        
        dispute.status = 'resolved'
        dispute.resolution_type = resolution_type
        dispute.resolution = resolution
        dispute.resolved_by = admin_id
        dispute.resolved_at = datetime.utcnow()
        
        escrow = Escrow.query.get(dispute.escrow_id) if dispute.escrow_id else None
        
        if escrow:
            if resolution_type == 'refund_full':
                escrow.status = 'refunded'
                escrow.refunded_at = datetime.utcnow()
            elif resolution_type == 'release_payment':
                escrow.status = 'released'
                escrow.released_at = datetime.utcnow()

                # Create or update transaction record to track commission
                transaction = Transaction.query.filter_by(gig_id=escrow.gig_id).first()
                if not transaction:
                    transaction = Transaction(
                        gig_id=escrow.gig_id,
                        freelancer_id=escrow.freelancer_id,
                        client_id=escrow.client_id,
                        amount=escrow.amount,
                        commission=escrow.platform_fee,
                        net_amount=escrow.net_amount,
                        payment_method='escrow',
                        status='completed'
                    )
                    db.session.add(transaction)
                else:
                    # Update existing transaction
                    transaction.commission = escrow.platform_fee
                    transaction.status = 'completed'
        
        for user_id in [dispute.filed_by_id, dispute.against_id]:
            notification = Notification(
                user_id=user_id,
                notification_type='dispute',
                title='Dispute Resolved',
                message=f'Your dispute has been resolved.',
                link=f'/dispute/{dispute.id}'
            )
            db.session.add(notification)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Resolve dispute error: {str(e)}")
        return jsonify({'error': 'Failed to resolve dispute'}), 500

@app.route('/admin/feedback')
@page_login_required
def admin_feedback():
    """Admin page for managing platform feedback"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user.is_admin:
        return redirect('/dashboard')
    
    status_filter = request.args.get('status', 'all')
    
    query = PlatformFeedback.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    feedbacks = query.order_by(PlatformFeedback.created_at.desc()).all()
    
    feedback_list = []
    for fb in feedbacks:
        feedback_user = User.query.get(fb.user_id)
        feedback_list.append({
            'feedback': fb,
            'user': feedback_user
        })
    
    stats = {
        'total': PlatformFeedback.query.count(),
        'new': PlatformFeedback.query.filter_by(status='new').count(),
        'reviewed': PlatformFeedback.query.filter_by(status='reviewed').count(),
        'resolved': PlatformFeedback.query.filter_by(status='resolved').count()
    }
    
    return render_template('admin_feedback.html',
                         user=user,
                         feedbacks=feedback_list,
                         stats=stats,
                         current_filter=status_filter,
                         active_page='admin',
                         lang=get_user_language(),
                         t=t)

@app.route('/admin/accounting')
@page_login_required
def admin_accounting():
    """Admin page for accounting/billing management - requires billing or super_admin role"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    # Check if user has admin access
    if not user.is_admin:
        return redirect('/dashboard')

    # Check if user has billing or super_admin role
    if user.admin_role not in ['super_admin', 'billing']:
        return redirect('/dashboard')

    return render_template('accounting.html',
                         user=user,
                         active_page='accounting',
                         lang=get_user_language(),
                         t=t)

@app.route('/api/admin/feedback/<int:feedback_id>/respond', methods=['POST'])
@admin_required
def respond_to_feedback(feedback_id):
    """Respond to platform feedback"""
    try:
        admin_id = session['user_id']
        data = request.json
        
        response_text = data.get('response', '').strip()
        new_status = data.get('status', 'reviewed')
        
        feedback = PlatformFeedback.query.get_or_404(feedback_id)
        
        if response_text:
            feedback.admin_response = response_text
            feedback.responded_by = admin_id
            feedback.responded_at = datetime.utcnow()
        
        feedback.status = new_status
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Respond to feedback error: {str(e)}")
        return jsonify({'error': 'Failed to respond to feedback'}), 500

# ============================================
# ESCROW MILESTONE ROUTES
# ============================================

@app.route('/api/milestones/<int:escrow_id>')
@login_required
def get_milestones(escrow_id):
    """Get milestones for an escrow"""
    user_id = session['user_id']
    escrow = Escrow.query.get_or_404(escrow_id)
    
    if escrow.client_id != user_id and escrow.freelancer_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    milestones = Milestone.query.filter_by(escrow_id=escrow_id).order_by(Milestone.milestone_number).all()
    return jsonify({'milestones': [m.to_dict() for m in milestones]})

@app.route('/api/milestones/create', methods=['POST'])
@login_required
def create_milestones():
    """Create milestones for an escrow"""
    try:
        user_id = session['user_id']
        data = request.json
        
        escrow_id = data.get('escrow_id')
        milestones_data = data.get('milestones', [])
        
        escrow = Escrow.query.get_or_404(escrow_id)
        if escrow.client_id != user_id:
            return jsonify({'error': 'Only the client can create milestones'}), 403
        
        existing = Milestone.query.filter_by(escrow_id=escrow_id).count()
        if existing > 0:
            return jsonify({'error': 'Milestones already exist for this escrow'}), 400
        
        total_amount = sum(m.get('amount', 0) for m in milestones_data)
        if abs(total_amount - escrow.amount) > 0.01:
            return jsonify({'error': 'Milestone amounts must equal total escrow amount'}), 400
        
        for i, m_data in enumerate(milestones_data, 1):
            milestone = Milestone(
                escrow_id=escrow_id,
                gig_id=escrow.gig_id,
                milestone_number=i,
                title=m_data.get('title', f'Milestone {i}'),
                description=m_data.get('description', ''),
                amount=m_data.get('amount', 0),
                percentage=(m_data.get('amount', 0) / escrow.amount) * 100 if escrow.amount > 0 else 0,
                due_date=datetime.fromisoformat(m_data['due_date']) if m_data.get('due_date') else None
            )
            db.session.add(milestone)
        
        db.session.commit()
        return jsonify({'success': True}), 201
    except Exception as e:
        app.logger.error(f"Create milestones error: {str(e)}")
        return jsonify({'error': 'Failed to create milestones'}), 500

@app.route('/api/milestone/<int:milestone_id>/submit', methods=['POST'])
@login_required
def submit_milestone(milestone_id):
    """Submit work for a milestone"""
    try:
        user_id = session['user_id']
        milestone = Milestone.query.get_or_404(milestone_id)
        escrow = Escrow.query.get(milestone.escrow_id)
        
        if escrow.freelancer_id != user_id:
            return jsonify({'error': 'Only the freelancer can submit milestones'}), 403
        
        milestone.work_submitted = True
        milestone.submitted_at = datetime.utcnow()
        milestone.status = 'submitted'
        
        notification = Notification(
            user_id=escrow.client_id,
            notification_type='milestone',
            title='Milestone Submitted',
            message=f'Work has been submitted for: {milestone.title}',
            link=f'/gig/{escrow.gig_id}',
            related_id=milestone_id
        )
        db.session.add(notification)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Submit milestone error: {str(e)}")
        return jsonify({'error': 'Failed to submit milestone'}), 500

@app.route('/api/milestone/<int:milestone_id>/approve', methods=['POST'])
@login_required
def approve_milestone(milestone_id):
    """Approve and release a milestone"""
    try:
        user_id = session['user_id']
        milestone = Milestone.query.get_or_404(milestone_id)
        escrow = Escrow.query.get(milestone.escrow_id)
        
        if escrow.client_id != user_id:
            return jsonify({'error': 'Only the client can approve milestones'}), 403
        
        if not milestone.work_submitted:
            return jsonify({'error': 'Work has not been submitted yet'}), 400
        
        milestone.approved_at = datetime.utcnow()
        milestone.released_at = datetime.utcnow()
        milestone.status = 'released'
        
        freelancer_wallet = Wallet.query.filter_by(user_id=escrow.freelancer_id).first()
        if not freelancer_wallet:
            freelancer_wallet = Wallet(user_id=escrow.freelancer_id)
            db.session.add(freelancer_wallet)
        
        net_amount = milestone.amount * 0.95
        freelancer_wallet.balance += net_amount
        freelancer_wallet.total_earned += net_amount
        
        notification = Notification(
            user_id=escrow.freelancer_id,
            notification_type='payment',
            title='Milestone Payment Released',
            message=f'RM {net_amount:.2f} has been released for: {milestone.title}',
            link=f'/payments',
            related_id=milestone_id
        )
        db.session.add(notification)
        
        all_milestones = Milestone.query.filter_by(escrow_id=escrow.id).all()
        if all(m.status == 'released' for m in all_milestones):
            escrow.status = 'released'
            escrow.released_at = datetime.utcnow()

            # Create or update transaction record to track commission
            transaction = Transaction.query.filter_by(gig_id=escrow.gig_id).first()
            if not transaction:
                transaction = Transaction(
                    gig_id=escrow.gig_id,
                    freelancer_id=escrow.freelancer_id,
                    client_id=escrow.client_id,
                    amount=escrow.amount,
                    commission=escrow.platform_fee,
                    net_amount=escrow.net_amount,
                    payment_method='escrow',
                    status='completed'
                )
                db.session.add(transaction)
            else:
                # Update existing transaction
                transaction.commission = escrow.platform_fee
                transaction.status = 'completed'

            gig = Gig.query.get(escrow.gig_id)
            if gig:
                gig.status = 'completed'
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Approve milestone error: {str(e)}")
        return jsonify({'error': 'Failed to approve milestone'}), 500

# ============================================================================
# SEO ROUTES: SITEMAP & ROBOTS.TXT
# ============================================================================

@app.route('/sitemap.xml')
def sitemap():
    """
    Generate dynamic XML sitemap for SEO
    Includes: Homepage, static pages, all active gigs
    """
    try:
        from flask import make_response

        # Build sitemap URLs
        pages = []

        # Homepage - highest priority
        pages.append({
            'loc': 'https://gighala.calmic.com.my/',
            'lastmod': datetime.now().strftime('%Y-%m-%d'),
            'changefreq': 'daily',
            'priority': '1.0'
        })

        # Static pages
        static_pages = [
            {'url': '/gigs', 'priority': '0.9', 'changefreq': 'hourly'},
            {'url': '/about', 'priority': '0.7', 'changefreq': 'monthly'},
            {'url': '/contact', 'priority': '0.6', 'changefreq': 'monthly'},
            {'url': '/privacy', 'priority': '0.5', 'changefreq': 'yearly'},
            {'url': '/halal-compliance', 'priority': '0.8', 'changefreq': 'monthly'},
            {'url': '/gig-workers-bill', 'priority': '0.7', 'changefreq': 'monthly'},
        ]

        for page in static_pages:
            pages.append({
                'loc': f"https://gighala.calmic.com.my{page['url']}",
                'lastmod': datetime.now().strftime('%Y-%m-%d'),
                'changefreq': page['changefreq'],
                'priority': page['priority']
            })

        # All active gigs (open, in_progress, or recently updated)
        active_gigs = Gig.query.filter(
            Gig.status.in_(['open', 'in_progress', 'completed'])
        ).order_by(Gig.updated_at.desc()).limit(5000).all()

        for gig in active_gigs:
            # Determine priority based on status
            if gig.status == 'open':
                priority = '0.8'
                changefreq = 'daily'
            elif gig.status == 'in_progress':
                priority = '0.6'
                changefreq = 'weekly'
            else:  # completed
                priority = '0.4'
                changefreq = 'monthly'

            pages.append({
                'loc': f"https://gighala.calmic.com.my/gig/{gig.id}",
                'lastmod': gig.updated_at.strftime('%Y-%m-%d') if gig.updated_at else gig.created_at.strftime('%Y-%m-%d'),
                'changefreq': changefreq,
                'priority': priority
            })

        # Generate XML
        sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for page in pages:
            sitemap_xml += '  <url>\n'
            sitemap_xml += f'    <loc>{page["loc"]}</loc>\n'
            sitemap_xml += f'    <lastmod>{page["lastmod"]}</lastmod>\n'
            sitemap_xml += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
            sitemap_xml += f'    <priority>{page["priority"]}</priority>\n'
            sitemap_xml += '  </url>\n'

        sitemap_xml += '</urlset>'

        # Return with correct content type
        response = make_response(sitemap_xml)
        response.headers['Content-Type'] = 'application/xml; charset=utf-8'
        return response

    except Exception as e:
        app.logger.error(f"Sitemap generation error: {str(e)}")
        return 'Error generating sitemap', 500


@app.route('/robots.txt')
def robots():
    """
    Generate robots.txt for search engine crawlers
    Allows all bots to crawl the site and points to sitemap
    """
    from flask import make_response

    robots_txt = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /dashboard
Disallow: /admin
Disallow: /profile
Disallow: /logout

# Sitemaps
Sitemap: https://gighala.calmic.com.my/sitemap.xml

# Crawl delay (be nice to server)
Crawl-delay: 1

# Specific bot configurations
User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: DuckDuckBot
Allow: /
"""

    response = make_response(robots_txt)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    return response


# ============================================================================
# BOT DETECTION MIDDLEWARE FOR SEO
# ============================================================================

@app.before_request
def detect_search_bot():
    """
    Detect search engine bots and add flag to request context
    This helps serve optimized content to crawlers
    """
    user_agent = request.headers.get('User-Agent', '').lower()

    # List of known search engine bots
    bot_patterns = [
        'googlebot', 'bingbot', 'slurp', 'duckduckbot', 'baiduspider',
        'yandexbot', 'sogou', 'exabot', 'facebot', 'ia_archiver'
    ]

    # Check if any bot pattern matches
    request.is_bot = any(bot in user_agent for bot in bot_patterns)

    # Log bot visits for monitoring (optional)
    if request.is_bot and request.path.startswith('/gig/'):
        app.logger.info(f"Bot visit: {user_agent} -> {request.path}")


with app.app_context():
    init_database()

# Initialize scheduled jobs (email digests, etc.)
scheduler = init_scheduler(app, db, User, Gig, NotificationPreference, EmailDigestLog, email_service)

# Setup Google OAuth if credentials are available
# Note: Using Authlib OAuth routes in app.py instead of google_auth.py blueprint
# The /api/auth/google and /api/auth/google/callback routes are defined above
# Keeping this file for reference but not registering it to avoid conflicts

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
