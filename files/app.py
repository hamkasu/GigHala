from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import secrets
import json
import uuid

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
database_url = os.environ.get('DATABASE_URL', 'sqlite:///gighala.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'work_photos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'gig_photos'), exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    status = db.Column(db.String(20), default='open')  # open, in_progress, pending_review, completed, cancelled
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
    work_submitted = db.Column(db.Boolean, default=False)  # Track if work has been submitted
    work_submission_date = db.Column(db.DateTime)  # When work was submitted
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
            'created_at': self.created_at.isoformat()
        }

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
            caption=caption[:500] if caption else None,
            photo_type=photo_type
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
        # Gig photos are public, anyone can view them
        return send_from_directory(os.path.join(UPLOAD_FOLDER, 'gig_photos'), filename)
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
            caption=caption[:500] if caption else None,
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

        # Check if user is authorized to view photos
        if not (gig.freelancer_id == user_id or gig.client_id == user_id):
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

        # Check if user is authorized to delete
        if work_photo.uploader_id != user_id:
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

        # Get the gig to check authorization
        gig = Gig.query.get(work_photo.gig_id)

        # Check if user is authorized to view
        if not (gig.freelancer_id == user_id or gig.client_id == user_id):
            return jsonify({'error': 'You are not authorized to view this photo'}), 403

        # Serve the file
        return send_from_directory(os.path.join(UPLOAD_FOLDER, 'work_photos'), filename)

    except Exception as e:
        app.logger.error(f"Serve work photo error: {str(e)}")
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

        # Assign freelancer to gig
        gig.freelancer_id = application.freelancer_id
        gig.status = 'in_progress'

        # Reject all other pending applications for this gig
        other_applications = Application.query.filter(
            Application.gig_id == gig.id,
            Application.id != application_id,
            Application.status == 'pending'
        ).all()

        for other_app in other_applications:
            other_app.status = 'rejected'

        db.session.commit()

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

        return jsonify({'message': 'Application rejected successfully'}), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Reject application error: {str(e)}")
        return jsonify({'error': 'Failed to reject application'}), 500

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

        db.session.commit()

        return jsonify({
            'message': 'Work submitted successfully. Waiting for client review.',
            'gig': {
                'id': gig.id,
                'status': gig.status,
                'work_photos_count': work_photos
            }
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

        db.session.commit()

        return jsonify({
            'message': 'Work approved! Gig marked as completed.',
            'gig': {
                'id': gig.id,
                'status': gig.status
            }
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

        db.session.commit()

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
    """Cancel a gig (client only, before work is completed)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.json
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']

        # Only client can cancel
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can cancel the gig'}), 403

        # Cannot cancel completed gigs
        if gig.status == 'completed':
            return jsonify({'error': 'Cannot cancel completed gigs'}), 400

        cancellation_reason = data.get('reason', '')

        gig.status = 'cancelled'

        db.session.commit()

        return jsonify({
            'message': 'Gig cancelled successfully',
            'gig': {
                'id': gig.id,
                'status': gig.status
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Cancel gig error: {str(e)}")
        return jsonify({'error': 'Failed to cancel gig'}), 500

# ============================================================================
# END GIG WORKFLOW
# ============================================================================

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
        {'id': 'design', 'name': 'Design & Kreatif', 'icon': '🎨'},
        {'id': 'writing', 'name': 'Penulisan & Terjemahan', 'icon': '✍️'},
        {'id': 'content', 'name': 'Penciptaan Kandungan', 'icon': '📸'},
        {'id': 'photography', 'name': 'Fotografi, Videografi & Animasi', 'icon': '📷'},
        {'id': 'web', 'name': 'Pembangunan Web', 'icon': '💻'},
        {'id': 'marketing', 'name': 'Pemasaran Digital', 'icon': '📱'},
        {'id': 'tutoring', 'name': 'Tunjuk Ajar', 'icon': '📚'},
        {'id': 'admin', 'name': 'Sokongan Admin & Pentadbiran Maya', 'icon': '📋'},
        {'id': 'general', 'name': 'Kerja Am', 'icon': '🔧'},
        {'id': 'delivery', 'name': 'Penghantaran & Logistik', 'icon': '🚚'},
        {'id': 'micro_tasks', 'name': 'Micro-Tasks & Tugasan', 'icon': '✅'},
        {'id': 'events', 'name': 'Pengurusan Acara', 'icon': '🎉'},
        {'id': 'caregiving', 'name': 'Penjagaan & Perkhidmatan', 'icon': '🏥'},
        {'id': 'creative_other', 'name': 'Lain-lain Kreatif', 'icon': '🎭'}
    ]

    return jsonify(categories)

# Initialize database
with app.app_context():
    db.create_all()
    
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
