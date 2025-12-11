from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import json

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gighalal.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 400
    
    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        phone=data.get('phone'),
        full_name=data.get('full_name'),
        user_type=data.get('user_type', 'freelancer'),
        location=data.get('location')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    
    return jsonify({
        'message': 'Registration successful',
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'user_type': new_user.user_type
        }
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'total_earnings': user.total_earnings,
                'rating': user.rating
            }
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/gigs', methods=['GET'])
def get_gigs():
    category = request.args.get('category')
    location = request.args.get('location')
    halal_only = request.args.get('halal_only', 'true').lower() == 'true'
    search = request.args.get('search', '')
    
    query = Gig.query.filter_by(status='open')
    
    if category:
        query = query.filter_by(category=category)
    if location:
        query = query.filter_by(location=location)
    if halal_only:
        query = query.filter_by(halal_compliant=True)
    if search:
        query = query.filter(Gig.title.contains(search) | Gig.description.contains(search))
    
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

@app.route('/api/gigs', methods=['POST'])
def create_gig():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    
    new_gig = Gig(
        title=data['title'],
        description=data['description'],
        category=data['category'],
        budget_min=data['budget_min'],
        budget_max=data['budget_max'],
        duration=data.get('duration'),
        location=data.get('location'),
        is_remote=data.get('is_remote', True),
        client_id=session['user_id'],
        halal_compliant=data.get('halal_compliant', True),
        is_instant_payout=data.get('is_instant_payout', False),
        is_brand_partnership=data.get('is_brand_partnership', False),
        skills_required=json.dumps(data.get('skills_required', [])),
        deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None
    )
    
    db.session.add(new_gig)
    db.session.commit()
    
    return jsonify({
        'message': 'Gig created successfully',
        'gig_id': new_gig.id
    }), 201

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
    
    data = request.json
    gig = Gig.query.get_or_404(gig_id)
    
    # Check if already applied
    existing = Application.query.filter_by(gig_id=gig_id, freelancer_id=session['user_id']).first()
    if existing:
        return jsonify({'error': 'Already applied to this gig'}), 400
    
    application = Application(
        gig_id=gig_id,
        freelancer_id=session['user_id'],
        cover_letter=data.get('cover_letter'),
        proposed_price=data.get('proposed_price'),
        video_pitch=data.get('video_pitch')
    )
    
    gig.applications += 1
    
    db.session.add(application)
    db.session.commit()
    
    return jsonify({'message': 'Application submitted successfully'}), 201

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
    
    user = User.query.get(session['user_id'])
    data = request.json
    
    user.full_name = data.get('full_name', user.full_name)
    user.phone = data.get('phone', user.phone)
    user.location = data.get('location', user.location)
    user.bio = data.get('bio', user.bio)
    user.skills = json.dumps(data.get('skills', [])) if data.get('skills') else user.skills
    
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully'})

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

# Dashboard endpoints
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])

    # Get user's posted gigs (if client)
    posted_gigs = []
    if user.user_type in ['client', 'both']:
        gigs = Gig.query.filter_by(client_id=user.id).order_by(Gig.created_at.desc()).all()
        posted_gigs = [{
            'id': g.id,
            'title': g.title,
            'status': g.status,
            'budget_min': g.budget_min,
            'budget_max': g.budget_max,
            'applications': g.applications,
            'created_at': g.created_at.isoformat()
        } for g in gigs]

    # Get user's applications (if freelancer)
    applications = []
    if user.user_type in ['freelancer', 'both']:
        apps = Application.query.filter_by(freelancer_id=user.id).order_by(Application.created_at.desc()).all()
        for app in apps:
            gig = Gig.query.get(app.gig_id)
            applications.append({
                'id': app.id,
                'gig_title': gig.title,
                'gig_id': gig.id,
                'status': app.status,
                'proposed_price': app.proposed_price,
                'created_at': app.created_at.isoformat()
            })

    # Get transactions
    transactions = Transaction.query.filter(
        (Transaction.freelancer_id == user.id) | (Transaction.client_id == user.id)
    ).order_by(Transaction.transaction_date.desc()).limit(10).all()

    transaction_list = [{
        'id': t.id,
        'amount': t.amount,
        'status': t.status,
        'payment_method': t.payment_method,
        'transaction_date': t.transaction_date.isoformat()
    } for t in transactions]

    return jsonify({
        'user': {
            'username': user.username,
            'user_type': user.user_type,
            'rating': user.rating,
            'total_earnings': user.total_earnings,
            'completed_gigs': user.completed_gigs
        },
        'posted_gigs': posted_gigs,
        'applications': applications,
        'transactions': transaction_list
    })

@app.route('/api/gigs/<int:gig_id>/applications', methods=['GET'])
def get_gig_applications(gig_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    gig = Gig.query.get_or_404(gig_id)

    # Only the gig owner can see applications
    if gig.client_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403

    applications = Application.query.filter_by(gig_id=gig_id).order_by(Application.created_at.desc()).all()

    app_list = []
    for app in applications:
        freelancer = User.query.get(app.freelancer_id)
        app_list.append({
            'id': app.id,
            'freelancer': {
                'id': freelancer.id,
                'username': freelancer.username,
                'rating': freelancer.rating,
                'completed_gigs': freelancer.completed_gigs,
                'skills': json.loads(freelancer.skills) if freelancer.skills else []
            },
            'cover_letter': app.cover_letter,
            'proposed_price': app.proposed_price,
            'status': app.status,
            'created_at': app.created_at.isoformat()
        })

    return jsonify(app_list)

@app.route('/api/applications/<int:app_id>/accept', methods=['POST'])
def accept_application(app_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    application = Application.query.get_or_404(app_id)
    gig = Gig.query.get(application.gig_id)

    # Only the gig owner can accept applications
    if gig.client_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403

    # Update application status
    application.status = 'accepted'

    # Update gig
    gig.freelancer_id = application.freelancer_id
    gig.status = 'in_progress'

    # Reject other applications
    Application.query.filter(
        Application.gig_id == gig.id,
        Application.id != app_id
    ).update({'status': 'rejected'})

    db.session.commit()

    return jsonify({'message': 'Application accepted successfully'})

@app.route('/api/applications/<int:app_id>/reject', methods=['POST'])
def reject_application(app_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    application = Application.query.get_or_404(app_id)
    gig = Gig.query.get(application.gig_id)

    # Only the gig owner can reject applications
    if gig.client_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403

    application.status = 'rejected'
    db.session.commit()

    return jsonify({'message': 'Application rejected'})

# Payment endpoints
@app.route('/api/payment/initiate', methods=['POST'])
def initiate_payment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    gig_id = data.get('gig_id')
    payment_method = data.get('payment_method', 'stripe')

    gig = Gig.query.get_or_404(gig_id)

    # Calculate amounts
    amount = float(data.get('amount', gig.budget_max))
    commission = amount * 0.10  # 10% commission
    net_amount = amount - commission

    # Create transaction record
    transaction = Transaction(
        gig_id=gig_id,
        freelancer_id=gig.freelancer_id,
        client_id=gig.client_id,
        amount=amount,
        commission=commission,
        net_amount=net_amount,
        payment_method=payment_method,
        status='pending'
    )

    db.session.add(transaction)
    db.session.commit()

    # In a real app, this would integrate with Stripe/payment gateway
    # For now, return a mock payment intent
    return jsonify({
        'transaction_id': transaction.id,
        'amount': amount,
        'client_secret': 'mock_client_secret_' + str(transaction.id),
        'status': 'pending'
    }), 201

@app.route('/api/payment/<int:transaction_id>/complete', methods=['POST'])
def complete_payment(transaction_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    transaction = Transaction.query.get_or_404(transaction_id)

    # Update transaction status
    transaction.status = 'completed'

    # Update gig status
    gig = Gig.query.get(transaction.gig_id)
    gig.status = 'completed'

    # Update freelancer earnings
    freelancer = User.query.get(transaction.freelancer_id)
    freelancer.total_earnings += transaction.net_amount
    freelancer.completed_gigs += 1

    db.session.commit()

    return jsonify({'message': 'Payment completed successfully'})

# Admin endpoints
@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Check if user is admin (you'd implement proper admin checking)
    user = User.query.get(session['user_id'])
    if user.email not in ['admin@gighalal.com', 'client@gighalal.com']:  # Simple admin check
        return jsonify({'error': 'Forbidden - Admin only'}), 403

    users = User.query.order_by(User.created_at.desc()).all()

    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'user_type': u.user_type,
        'rating': u.rating,
        'total_earnings': u.total_earnings,
        'completed_gigs': u.completed_gigs,
        'is_verified': u.is_verified,
        'created_at': u.created_at.isoformat()
    } for u in users])

@app.route('/api/admin/gigs', methods=['GET'])
def admin_get_gigs():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if user.email not in ['admin@gighalal.com', 'client@gighalal.com']:
        return jsonify({'error': 'Forbidden - Admin only'}), 403

    gigs = Gig.query.order_by(Gig.created_at.desc()).all()

    return jsonify([{
        'id': g.id,
        'title': g.title,
        'category': g.category,
        'status': g.status,
        'budget_min': g.budget_min,
        'budget_max': g.budget_max,
        'applications': g.applications,
        'views': g.views,
        'created_at': g.created_at.isoformat()
    } for g in gigs])

@app.route('/api/admin/stats', methods=['GET'])
def admin_get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    if user.email not in ['admin@gighalal.com', 'client@gighalal.com']:
        return jsonify({'error': 'Forbidden - Admin only'}), 403

    total_users = User.query.count()
    total_gigs = Gig.query.count()
    active_gigs = Gig.query.filter_by(status='open').count()
    completed_gigs = Gig.query.filter_by(status='completed').count()
    total_applications = Application.query.count()
    total_transactions = Transaction.query.filter_by(status='completed').count()
    total_revenue = db.session.query(db.func.sum(Transaction.commission)).filter_by(status='completed').scalar() or 0
    total_paid_out = db.session.query(db.func.sum(Transaction.net_amount)).filter_by(status='completed').scalar() or 0

    return jsonify({
        'total_users': total_users,
        'total_gigs': total_gigs,
        'active_gigs': active_gigs,
        'completed_gigs': completed_gigs,
        'total_applications': total_applications,
        'total_transactions': total_transactions,
        'total_revenue': float(total_revenue),
        'total_paid_out': float(total_paid_out)
    })

@app.route('/api/admin/users/<int:user_id>/verify', methods=['POST'])
def admin_verify_user(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    admin = User.query.get(session['user_id'])
    if admin.email not in ['admin@gighalal.com', 'client@gighalal.com']:
        return jsonify({'error': 'Forbidden - Admin only'}), 403

    user = User.query.get_or_404(user_id)
    user.is_verified = not user.is_verified
    db.session.commit()

    return jsonify({'message': f'User verification toggled', 'is_verified': user.is_verified})

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
        
        db.session.add(sample_user)
        db.session.add(sample_client)
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
