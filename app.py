from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from email_validator import validate_email, EmailNotValidError
import os
import secrets
import json
import re

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gighalal.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql+psycopg://', 1)
elif app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Secure session configuration
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

db = SQLAlchemy(app)

# Secure CORS configuration - restrict to specific origins in production
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app,
     origins=allowed_origins,
     supports_credentials=True,
     max_age=3600)

# Rate limiting storage (in-memory, consider Redis for production)
login_attempts = {}
api_rate_limits = {}

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

def sanitize_input(text, max_length=1000):
    """Sanitize text input to prevent injection attacks"""
    if not text:
        return text
    # Remove any potentially harmful characters
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text

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

# Admin authentication decorator
def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized - Please login'}), 401

        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            return jsonify({'error': 'Forbidden - Admin access required'}), 403

        return f(*args, **kwargs)
    return decorated_function

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    full_name = db.Column(db.String(120))
    user_type = db.Column(db.String(20), default='freelancer')  # freelancer, client, both
    location = db.Column(db.String(100))
    skills = db.Column(db.Text)  # JSON string
    bio = db.Column(db.Text)
    rating = db.Column(db.Float, default=0.0)
    total_earnings = db.Column(db.Float, default=0.0)
    completed_gigs = db.Column(db.Integer, default=0)
    profile_video = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    halal_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

class Gig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    budget_min = db.Column(db.Float, nullable=False)
    budget_max = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(50))  # e.g., "1-3 days", "1 week"
    location = db.Column(db.String(100))
    is_remote = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='open')  # open, in_progress, completed, cancelled
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    halal_compliant = db.Column(db.Boolean, default=True)
    halal_verified = db.Column(db.Boolean, default=False)
    is_instant_payout = db.Column(db.Boolean, default=False)
    is_brand_partnership = db.Column(db.Boolean, default=False)
    skills_required = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime)
    views = db.Column(db.Integer, default=0)
    applications = db.Column(db.Integer, default=0)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cover_letter = db.Column(db.Text)
    proposed_price = db.Column(db.Float)
    video_pitch = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # ipay88, bank_transfer, touch_n_go
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

class Payout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payout_number = db.Column(db.String(50), unique=True, nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    fee = db.Column(db.Float, default=0.0)
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
    type = db.Column(db.String(30), nullable=False)  # deposit, withdrawal, payment, refund, commission, payout, hold, release
    amount = db.Column(db.Float, nullable=False)
    balance_before = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    reference_number = db.Column(db.String(100))
    payment_gateway = db.Column(db.String(50))
    gateway_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def index():
    stats = SiteStats.query.filter_by(key='visitor_count').first()
    if not stats:
        stats = SiteStats(key='visitor_count', value=0)
        db.session.add(stats)
    stats.value += 1
    db.session.commit()
    return render_template('index.html', visitor_count=stats.value)

@app.route('/api/register', methods=['POST'])
@rate_limit(max_attempts=10, window_minutes=60, lockout_minutes=15)
def register():
    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('email') or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400

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

        # Validate user_type
        user_type = data.get('user_type', 'freelancer')
        if user_type not in ['freelancer', 'client', 'both']:
            user_type = 'freelancer'

        new_user = User(
            username=data['username'],
            email=email,
            password_hash=generate_password_hash(data['password']),
            phone=data.get('phone'),
            full_name=full_name,
            user_type=user_type,
            location=location
        )

        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session.permanent = True

        # Reset rate limit on successful registration
        reset_rate_limit(request.remote_addr)

        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'user_type': new_user.user_type
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        # Log the error but don't expose details to user
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

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

        user = User.query.filter_by(email=email).first()

        # Use constant-time comparison to prevent timing attacks
        if user and check_password_hash(user.password_hash, data['password']):
            session['user_id'] = user.id
            session.permanent = True

            # Reset rate limit on successful login
            reset_rate_limit(request.remote_addr)

            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.user_type,
                    'total_earnings': user.total_earnings,
                    'rating': user.rating,
                    'is_admin': user.is_admin
                }
            }), 200

        # Generic error message to prevent user enumeration
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        # Log the error but don't expose details to user
        app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed. Please try again.'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/gigs', methods=['GET'])
def get_gigs():
    try:
        category = sanitize_input(request.args.get('category', ''), max_length=50)
        location = sanitize_input(request.args.get('location', ''), max_length=100)
        halal_only = request.args.get('halal_only', 'true').lower() == 'true'
        search = sanitize_input(request.args.get('search', ''), max_length=200)

        query = Gig.query.filter_by(status='open')

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

        return jsonify([{
            'id': g.id,
            'title': g.title,
            'description': g.description,
            'category': g.category,
            'budget_min': g.budget_min,
            'budget_max': g.budget_max,
            'location': g.location,
            'is_remote': g.is_remote,
            'halal_compliant': g.halal_compliant,
            'halal_verified': g.halal_verified,
            'is_instant_payout': g.is_instant_payout,
            'is_brand_partnership': g.is_brand_partnership,
            'duration': g.duration,
            'views': g.views,
            'applications': g.applications,
            'created_at': g.created_at.isoformat()
        } for g in gigs])
    except Exception as e:
        app.logger.error(f"Get gigs error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve gigs'}), 500

@app.route('/api/gigs', methods=['POST'])
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
            if budget_min < 0 or budget_max < 0 or budget_min > budget_max:
                return jsonify({'error': 'Invalid budget values'}), 400
            if budget_min > 1000000 or budget_max > 1000000:
                return jsonify({'error': 'Budget values too high'}), 400
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

        new_gig = Gig(
            title=title,
            description=description,
            category=category,
            budget_min=budget_min,
            budget_max=budget_max,
            duration=duration,
            location=location,
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
    gig.views += 1
    db.session.commit()
    
    client = User.query.get(gig.client_id)
    
    return jsonify({
        'id': gig.id,
        'title': gig.title,
        'description': gig.description,
        'category': gig.category,
        'budget_min': gig.budget_min,
        'budget_max': gig.budget_max,
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

        gig.applications += 1

        db.session.add(application)
        db.session.commit()

        return jsonify({'message': 'Application submitted successfully'}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Apply to gig error: {str(e)}")
        return jsonify({'error': 'Failed to submit application. Please try again.'}), 500

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
        'total_earnings': user.total_earnings,
        'completed_gigs': user.completed_gigs,
        'is_verified': user.is_verified,
        'halal_verified': user.halal_verified,
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
    categories = [
        {'id': 'design', 'name': 'Graphic Design', 'icon': '🎨'},
        {'id': 'writing', 'name': 'Writing & Translation', 'icon': '✍️'},
        {'id': 'video', 'name': 'Video Editing', 'icon': '🎬'},
        {'id': 'tutoring', 'name': 'Tutoring & Education', 'icon': '📚'},
        {'id': 'tech', 'name': 'Tech & Programming', 'icon': '💻'},
        {'id': 'marketing', 'name': 'Digital Marketing', 'icon': '📱'},
        {'id': 'admin', 'name': 'Virtual Assistant', 'icon': '📋'},
        {'id': 'content', 'name': 'Content Creation', 'icon': '📸'},
        {'id': 'voice', 'name': 'Voice Over', 'icon': '🎤'},
        {'id': 'data', 'name': 'Data Entry', 'icon': '📊'}
    ]
    
    return jsonify(categories)

# Admin Routes
@app.route('/admin')
def admin_page():
    """Serve admin dashboard page"""
    if 'user_id' not in session:
        return render_template('index.html')

    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return render_template('index.html')

    return render_template('admin.html')

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

        total_transactions = Transaction.query.count()
        total_revenue = db.session.query(db.func.sum(Transaction.amount)).scalar() or 0
        total_commission = db.session.query(db.func.sum(Transaction.commission)).scalar() or 0

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
                'recent_week': recent_users
            },
            'gigs': {
                'total': total_gigs,
                'open': open_gigs,
                'in_progress': in_progress_gigs,
                'completed': completed_gigs,
                'halal_compliant': halal_gigs,
                'recent_week': recent_gigs
            },
            'applications': {
                'total': total_applications,
                'pending': pending_applications
            },
            'transactions': {
                'total': total_transactions,
                'revenue': float(total_revenue),
                'commission': float(total_commission)
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Admin stats error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500

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
            result.append({
                'id': g.id,
                'title': g.title,
                'description': g.description,
                'category': g.category,
                'budget_min': g.budget_min,
                'budget_max': g.budget_max,
                'status': g.status,
                'halal_compliant': g.halal_compliant,
                'halal_verified': g.halal_verified,
                'views': g.views,
                'applications': g.applications,
                'created_at': g.created_at.isoformat(),
                'client': {
                    'id': client.id,
                    'username': client.username,
                    'email': client.email
                } if client else None
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
    """Delete a gig"""
    try:
        gig = Gig.query.get_or_404(gig_id)

        # Delete associated applications
        Application.query.filter_by(gig_id=gig_id).delete()

        db.session.delete(gig)
        db.session.commit()

        return jsonify({'message': 'Gig deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin delete gig error: {str(e)}")
        return jsonify({'error': 'Failed to delete gig'}), 500

# ==================== BILLING ROUTES ====================

@app.route('/billing')
@login_required
def billing_page():
    """Billing dashboard page"""
    return render_template('billing.html')

@app.route('/api/billing/wallet', methods=['GET'])
@login_required
def get_wallet():
    """Get user's wallet information"""
    try:
        user_id = session['user_id']
        wallet = Wallet.query.filter_by(user_id=user_id).first()

        # Create wallet if it doesn't exist
        if not wallet:
            wallet = Wallet(user_id=user_id)
            db.session.add(wallet)
            db.session.commit()

        return jsonify({
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

        # Build query
        if transaction_type == 'sent':
            query = Transaction.query.filter_by(client_id=user_id)
        elif transaction_type == 'received':
            query = Transaction.query.filter_by(freelancer_id=user_id)
        else:
            query = Transaction.query.filter(
                (Transaction.client_id == user_id) | (Transaction.freelancer_id == user_id)
            )

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
                'gig_title': gig.title if gig else 'N/A',
                'client_name': client.username if client else 'N/A',
                'freelancer_name': freelancer.username if freelancer else 'N/A',
                'amount': t.amount,
                'commission': t.commission,
                'net_amount': t.net_amount,
                'payment_method': t.payment_method,
                'status': t.status,
                'date': t.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'sent' if t.client_id == user_id else 'received'
            })

        return jsonify({
            'transactions': transactions,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        }), 200
    except Exception as e:
        app.logger.error(f"Get transactions error: {str(e)}")
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

        # Build query
        query = Invoice.query.filter(
            (Invoice.client_id == user_id) | (Invoice.freelancer_id == user_id)
        )

        if status != 'all':
            query = query.filter_by(status=status)

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
                'gig_title': gig.title if gig else 'N/A',
                'client_name': client.username if client else 'N/A',
                'freelancer_name': freelancer.username if freelancer else 'N/A',
                'amount': inv.amount,
                'platform_fee': inv.platform_fee,
                'tax_amount': inv.tax_amount,
                'total_amount': inv.total_amount,
                'status': inv.status,
                'payment_method': inv.payment_method,
                'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'paid_at': inv.paid_at.strftime('%Y-%m-%d %H:%M:%S') if inv.paid_at else None,
                'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else None,
                'role': 'client' if inv.client_id == user_id else 'freelancer'
            })

        return jsonify({
            'invoices': invoices,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        }), 200
    except Exception as e:
        app.logger.error(f"Get invoices error: {str(e)}")
        return jsonify({'error': 'Failed to get invoices'}), 500

@app.route('/api/billing/payouts', methods=['GET'])
@login_required
def get_payouts():
    """Get user's payout history"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

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
                'bank_name': p.bank_name,
                'account_number': p.account_number[-4:] if p.account_number else None,  # Last 4 digits
                'status': p.status,
                'requested_at': p.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': p.completed_at.strftime('%Y-%m-%d %H:%M:%S') if p.completed_at else None,
                'failure_reason': p.failure_reason
            })

        return jsonify({
            'payouts': payouts,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page
        }), 200
    except Exception as e:
        app.logger.error(f"Get payouts error: {str(e)}")
        return jsonify({'error': 'Failed to get payouts'}), 500

@app.route('/api/billing/payouts', methods=['POST'])
@login_required
def request_payout():
    """Request a payout"""
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

        if amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400

        # Check wallet balance
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet or wallet.balance < amount:
            return jsonify({'error': 'Insufficient balance'}), 400

        # Calculate fee (2% platform fee)
        fee = amount * 0.02
        net_amount = amount - fee

        # Generate payout number
        import random
        payout_number = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"

        # Create payout request
        payout = Payout(
            payout_number=payout_number,
            freelancer_id=user_id,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            payment_method=payment_method,
            account_number=account_number,
            account_name=account_name,
            bank_name=bank_name,
            status='pending'
        )

        # Hold the balance
        wallet.balance -= amount
        wallet.held_balance += amount

        # Create payment history
        history = PaymentHistory(
            user_id=user_id,
            payout_id=payout.id,
            type='hold',
            amount=amount,
            balance_before=wallet.balance + amount,
            balance_after=wallet.balance,
            description=f'Payout request {payout_number}'
        )

        db.session.add(payout)
        db.session.add(history)
        db.session.commit()

        return jsonify({
            'message': 'Payout request submitted successfully',
            'payout_number': payout_number,
            'status': 'pending'
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

# Initialize database
with app.app_context():
    db.create_all()
    
    # Add sample data if database is empty
    if User.query.count() == 0:
        # Sample users
        sample_user = User(
            username='demo_freelancer',
            email='freelancer@gighalal.com',
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
            email='client@gighalal.com',
            password_hash=generate_password_hash('password123'),
            full_name='Siti Nurhaliza',
            user_type='client',
            location='Penang',
            is_verified=True
        )

        # Admin user
        admin_user = User(
            username='admin',
            email='admin@gighalal.com',
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
                category='design',
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
                category='writing',
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
                category='video',
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
                category='content',
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
                title='Share GigHalal Post on Social Media',
                description='Share our promotional post and tag 3 friends',
                reward=5.0,
                task_type='content_creation'
            )
        ]
        
        for task in microtasks:
            db.session.add(task)
        
        db.session.commit()
        print("Sample data added successfully!")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
