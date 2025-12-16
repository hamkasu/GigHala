from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, flash
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
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
from hijri_converter import Hijri, Gregorian

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
PROCESSING_FEE_PERCENT = 0.029
PROCESSING_FEE_FIXED = 1.00

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

# Set secret key with fallback
app.secret_key = os.environ.get("SESSION_SECRET") or os.environ.get("SECRET_KEY")
if not app.secret_key:
    # Generate a random secret key for development if none is set
    # In production, always set SESSION_SECRET or SECRET_KEY environment variable
    app.secret_key = secrets.token_hex(32)
    print("⚠️  WARNING: Using auto-generated SECRET_KEY. Set SESSION_SECRET or SECRET_KEY environment variable in production!")

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///gighalal.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql+psycopg2://', 1)
elif app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgresql://', 'postgresql+psycopg2://', 1)
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

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
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
    """Run periodic cleanup on rate limit storage"""
    global _last_cleanup
    current_time = datetime.utcnow()
    # Run cleanup every 5 minutes
    if (current_time - _last_cleanup).total_seconds() > 300:
        cleanup_rate_limits()

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

        # Homepage - Navigation
        'find_gigs': 'Cari Gig',
        'categories': 'Kategori',
        'how_it_works': 'Cara Kerja',
        'login': 'Log Masuk',
        'register_free': 'Daftar Percuma',

        # Homepage - Hero Section
        'active_freelancers': '50,000+ Freelancers Aktif',
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
        'step_4_title': 'Terima Bayaran',
        'step_4_desc': 'Instant payout dalam 24 jam ke Touch \'n Go atau bank anda.',

        # Homepage - Testimonials
        'success_stories': 'Kisah Kejayaan',
        'success_subtitle': 'Ratusan freelancers berjaya jana pendapatan konsisten',
        'testimonial_1': '"Dalam 2 bulan, saya dah buat RM 4,500 dari video editing! Platform ni betul-betul game changer untuk ibu tunggal macam saya."',
        'testimonial_1_name': 'Nurul Huda',
        'testimonial_1_role': 'Video Editor • KL',
        'testimonial_1_earnings': 'Pendapatan: RM 4,500/bulan',
        'testimonial_2': '"Fresh grad cari kerja susah. GigHalal bagi peluang saya buat income sambil tunggu tawaran tetap. Sekarang side income saya RM 2,800!"',
        'testimonial_2_name': 'Ahmad Zaki',
        'testimonial_2_role': 'Graphic Designer • Penang',
        'testimonial_2_earnings': 'Pendapatan: RM 2,800/bulan',
        'testimonial_3': '"Saya tutor online part-time. Platform ni connect saya dengan pelajar SPM yang betul-betul perlukan bantuan. Win-win situation!"',
        'testimonial_3_name': 'Siti Aisyah',
        'testimonial_3_role': 'SPM Tutor • JB',
        'testimonial_3_earnings': 'Pendapatan: RM 1,900/bulan',

        # Homepage - CTA
        'ready_to_earn': 'Siap untuk mula jana pendapatan halal?',
        'join_freelancers': 'Join 50,000+ freelancers yang dah berjaya. Daftar percuma sekarang!',
        'register_now_free': 'Daftar Sekarang - 100% Percuma',
        'cta_benefits': '✓ Tiada bayaran tersembunyi  •  ✓ Bayaran instant  •  ✓ Halal verified',

        # Homepage - Footer
        'footer_description': 'Platform gig economy halal #1 di Malaysia. Jana pendapatan berkah dari rumah.',
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
        'rights_reserved': 'Hak cipta terpelihara. Berdaftar dengan SSM (Calmic Sdn Bhd)',
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
    },
    'en': {
        # Dashboard
        'welcome_back': 'Welcome back',
        'happening_today': "Here's what's happening with your account today",
        'wallet_balance': 'Wallet Balance',
        'available_withdraw': 'Available to withdraw',
        'completed_gigs': 'Completed Gigs',
        'successfully_finished': 'Successfully finished',
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

        # Homepage - Navigation
        'find_gigs': 'Find Gigs',
        'categories': 'Categories',
        'how_it_works': 'How It Works',
        'login': 'Login',
        'register_free': 'Sign Up Free',

        # Homepage - Hero Section
        'active_freelancers': '50,000+ Active Freelancers',
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
        'step_4_title': 'Receive Payment',
        'step_4_desc': 'Instant payout within 24 hours to your Touch \'n Go or bank account.',

        # Homepage - Testimonials
        'success_stories': 'Success Stories',
        'success_subtitle': 'Hundreds of freelancers successfully earning consistent income',
        'testimonial_1': '"In 2 months, I made RM 4,500 from video editing! This platform is a real game changer for single mothers like me."',
        'testimonial_1_name': 'Nurul Huda',
        'testimonial_1_role': 'Video Editor • KL',
        'testimonial_1_earnings': 'Earnings: RM 4,500/month',
        'testimonial_2': '"Fresh grad finding work is hard. GigHalal gave me the opportunity to earn income while waiting for permanent offers. Now my side income is RM 2,800!"',
        'testimonial_2_name': 'Ahmad Zaki',
        'testimonial_2_role': 'Graphic Designer • Penang',
        'testimonial_2_earnings': 'Earnings: RM 2,800/month',
        'testimonial_3': '"I tutor online part-time. This platform connects me with SPM students who really need help. Win-win situation!"',
        'testimonial_3_name': 'Siti Aisyah',
        'testimonial_3_role': 'SPM Tutor • JB',
        'testimonial_3_earnings': 'Earnings: RM 1,900/month',

        # Homepage - CTA
        'ready_to_earn': 'Ready to start earning halal income?',
        'join_freelancers': "Join 50,000+ freelancers who've already succeeded. Sign up free now!",
        'register_now_free': 'Sign Up Now - 100% Free',
        'cta_benefits': '✓ No hidden fees  •  ✓ Instant payments  •  ✓ Halal verified',

        # Homepage - Footer
        'footer_description': "Malaysia's #1 halal gig economy platform. Earn blessed income from home.",
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
        'rights_reserved': 'All rights reserved. Registered with SSM (Calmic Sdn Bhd)',
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
HIJRI_MONTHS = {
    'ms': ['Muharram', 'Safar', 'Rabiul Awal', 'Rabiul Akhir', 'Jamadil Awal', 'Jamadil Akhir',
           'Rejab', 'Syaaban', 'Ramadan', 'Syawal', 'Zulkaedah', 'Zulhijah'],
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
    
    # Convert to Hijri
    hijri = Gregorian(date_obj.year, date_obj.month, date_obj.day).to_hijri()
    hijri_month = HIJRI_MONTHS.get(lang, HIJRI_MONTHS['ms'])[hijri.month - 1]
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
    return dict(
        t=t, 
        lang=get_user_language(),
        today_gregorian=today_dual['gregorian'],
        today_hijri=today_dual['hijri'],
        today_dual=today_dual['full'],
        format_date_dual=format_date_dual
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

def create_escrow_receipt(escrow, gig, payment_method='fpx'):
    """Create a receipt for escrow funding (idempotent - only creates if none exists)"""
    existing_receipt = Receipt.query.filter_by(
        escrow_id=escrow.id,
        receipt_type='escrow_funding'
    ).first()
    
    if existing_receipt:
        app.logger.info(f"Receipt already exists for escrow {escrow.id}: {existing_receipt.receipt_number}")
        return existing_receipt
    
    receipt = Receipt(
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
    db.session.add(receipt)
    return receipt

# Login required decorator for API routes
def login_required(f):
    """Decorator to require user authentication for API routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized - Please login'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Login required decorator for page routes (redirects to home page)
def page_login_required(f):
    """Decorator to require user authentication for page routes - redirects to home"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

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
    review_count = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    completed_gigs = db.Column(db.Integer, default=0)
    profile_video = db.Column(db.String(255))
    language = db.Column(db.String(5), default='ms')  # ms (Malay) or en (English)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    halal_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    # IC Number (Malaysian Identity Card - 12 digits)
    ic_number = db.Column(db.String(12))
    # Bank account details for payment transfers
    bank_name = db.Column(db.String(100))
    bank_account_number = db.Column(db.String(30))
    bank_account_holder = db.Column(db.String(120))

class EmailHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_email = db.Column(db.String(120), nullable=False)
    new_email = db.Column(db.String(120), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))

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
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, default=0.0)
    net_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default='pending')
    payment_reference = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    funded_at = db.Column(db.DateTime)
    released_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    dispute_reason = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    
    def to_dict(self):
        """Convert escrow to dictionary for JSON response"""
        return {
            'id': self.id,
            'gig_id': self.gig_id,
            'client_id': self.client_id,
            'freelancer_id': self.freelancer_id,
            'amount': self.amount,
            'platform_fee': self.platform_fee,
            'net_amount': self.net_amount,
            'status': self.status,
            'status_label': self.get_status_label(),
            'status_color': self.get_status_color(),
            'payment_reference': self.payment_reference,
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

# Routes
@app.route('/')
def index():
    # If user is logged in, redirect to their personalized dashboard
    if 'user_id' in session:
        return redirect('/dashboard')

    # Show public homepage for visitors
    stats = SiteStats.query.filter_by(key='visitor_count').first()
    if not stats:
        stats = SiteStats(key='visitor_count', value=0)
        db.session.add(stats)
    stats.value += 1
    db.session.commit()
    return render_template('index.html', visitor_count=stats.value, lang=get_user_language(), t=t)

@app.route('/gigs')
@page_login_required
def browse_gigs():
    """Browse available gigs page"""
    user_id = session['user_id']
    user = User.query.get(user_id)
    categories = Category.query.all()
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
                        'freelancer_is_verified': freelancer.is_verified,
                        'proposed_price': app_item.proposed_price,
                        'cover_letter': app_item.cover_letter,
                        'status': app_item.status,
                        'created_at': app_item.created_at
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

    categories = Category.query.all()
    
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
                if budget_min < 0 or budget_max < 0 or budget_min > budget_max:
                    flash('Nilai budget tidak sah.', 'error')
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
            
            new_gig = Gig(
                title=title,
                description=description,
                category=category,
                budget_min=budget_min,
                budget_max=budget_max,
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
            db.session.commit()
            
            # Handle photo uploads
            photos = request.files.getlist('photos')
            if photos:
                allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
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
                            filename=unique_filename,
                            original_filename=photo.filename,
                            photo_type='reference'
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
    
    categories = Category.query.all()
    
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
                if budget_min < 0 or budget_max < 0 or budget_min > budget_max:
                    flash('Nilai budget tidak sah.', 'error')
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
    total_gigs_completed = Gig.query.filter_by(freelancer_id=user_id, status='completed').count() if user.user_type in ['freelancer', 'both'] else 0
    total_applications = Application.query.filter_by(freelancer_id=user_id).count() if user.user_type in ['freelancer', 'both'] else 0

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

    return render_template('dashboard.html',
                         user=user,
                         wallet=wallet,
                         posted_gigs=posted_gigs,
                         active_gigs=active_gigs,
                         applications=applications,
                         total_gigs_posted=total_gigs_posted,
                         total_gigs_completed=total_gigs_completed,
                         total_applications=total_applications,
                         recent_transactions=recent_transactions,
                         gigs_to_review=gigs_to_review,
                         recent_reviews=recent_reviews,
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
    
    # Only the receipt owner can view
    if receipt.user_id != user_id:
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
    return render_template('settings.html', user=user, lang=get_user_language(), t=t)

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

@app.route('/api/register', methods=['POST'])
@rate_limit(max_attempts=10, window_minutes=60, lockout_minutes=15)
def register():
    try:
        data = request.json

        # Validate required fields
        if not data or not data.get('email') or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate privacy consent (PDPA 2010 requirement)
        if not data.get('privacy_consent'):
            return jsonify({'error': 'You must agree to the Privacy Policy to register'}), 400

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

@app.route('/api/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    # For GET requests (direct link clicks), redirect to homepage
    if request.method == 'GET':
        return redirect('/')
    # For POST requests (JavaScript calls), return JSON
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/gigs', methods=['GET'])
@api_rate_limit(requests_per_minute=120)
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
                'location': g.location,
                'is_remote': g.is_remote,
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

        gig.applications += 1

        db.session.add(application)
        db.session.commit()

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

        # Serve the file
        return send_from_directory(os.path.join(UPLOAD_FOLDER, 'work_photos'), filename)

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
        
        if not gig_id or amount <= 0:
            return jsonify({'error': 'Invalid gig_id or amount'}), 400
        
        gig = Gig.query.get_or_404(gig_id)
        user_id = session['user_id']
        
        # Only client can create escrow
        if gig.client_id != user_id:
            return jsonify({'error': 'Only the client can fund the escrow'}), 403
        
        # Gig must have an assigned freelancer
        if not gig.freelancer_id:
            return jsonify({'error': 'Gig must have an assigned freelancer'}), 400
        
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
        if client_wallet:
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
        app.logger.error(f"Create escrow error: {str(e)}")
        return jsonify({'error': 'Failed to create escrow'}), 500

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
        
        escrow = Escrow.query.filter_by(gig_id=gig_id).first()
        
        if not escrow:
            return jsonify({'error': 'No escrow found'}), 404
        
        if escrow.status != 'funded':
            return jsonify({'error': f'Escrow cannot be released (status: {escrow.status})'}), 400
        
        # Release escrow
        escrow.status = 'released'
        escrow.released_at = datetime.utcnow()
        
        # Update wallets
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        freelancer_wallet = Wallet.query.filter_by(user_id=gig.freelancer_id).first()
        
        if client_wallet:
            client_wallet.held_balance -= escrow.amount
            client_wallet.total_spent += escrow.amount
        
        if not freelancer_wallet:
            freelancer_wallet = Wallet(user_id=gig.freelancer_id)
            db.session.add(freelancer_wallet)
        
        freelancer_wallet.balance += escrow.net_amount
        freelancer_wallet.total_earned += escrow.net_amount
        
        # Record payment history
        payment_history = PaymentHistory(
            user_id=gig.freelancer_id,
            type='release',
            amount=escrow.net_amount,
            balance_before=freelancer_wallet.balance - escrow.net_amount,
            balance_after=freelancer_wallet.balance,
            description=f"Escrow released for gig: {gig.title}",
            reference_number=escrow.payment_reference
        )
        db.session.add(payment_history)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Escrow released successfully! Funds transferred to freelancer.',
            'escrow': escrow.to_dict()
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
        
        if escrow.status not in ['funded', 'disputed']:
            return jsonify({'error': f'Escrow cannot be refunded (status: {escrow.status})'}), 400
        
        # Refund escrow
        escrow.status = 'refunded'
        escrow.refunded_at = datetime.utcnow()
        escrow.admin_notes = data.get('reason', '')
        
        # Update client wallet
        client_wallet = Wallet.query.filter_by(user_id=gig.client_id).first()
        if client_wallet:
            client_wallet.held_balance -= escrow.amount
            client_wallet.balance += escrow.amount
        
        # Record payment history
        payment_history = PaymentHistory(
            user_id=gig.client_id,
            type='refund',
            amount=escrow.amount,
            balance_before=client_wallet.balance - escrow.amount if client_wallet else 0,
            balance_after=client_wallet.balance if client_wallet else escrow.amount,
            description=f"Escrow refunded for gig: {gig.title}",
            reference_number=escrow.payment_reference
        )
        db.session.add(payment_history)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Escrow refunded successfully',
            'escrow': escrow.to_dict()
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
        
        # Get amount from request or use gig budget
        data = request.json or {}
        amount = float(data.get('amount', gig.budget or 0))
        
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
                    'account_name': 'GigHalal Sdn Bhd',
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


@app.route('/api/payhalal/escrow-webhook', methods=['POST'])
def payhalal_escrow_webhook():
    """Handle PayHalal payment webhook for escrow funding"""
    try:
        from payhalal import get_payhalal_client
        
        data = request.json or {}
        signature = request.headers.get('X-PayHalal-Signature', '')
        
        client = get_payhalal_client()
        
        # Verify webhook signature if available
        if signature and not client.verify_webhook_signature(data, signature):
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
@page_login_required
def billing_page():
    """Billing dashboard page"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    return render_template('billing.html', user=user, active_page='billing', lang=get_user_language(), t=t)

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
            'user_id': user_id,
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

        return jsonify(transactions), 200
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
                'gig_id': inv.gig_id,
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
                'issue_date': inv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'paid_at': inv.paid_at.strftime('%Y-%m-%d %H:%M:%S') if inv.paid_at else None,
                'due_date': inv.due_date.strftime('%Y-%m-%d') if inv.due_date else None,
                'role': 'client' if inv.client_id == user_id else 'freelancer'
            })

        return jsonify(invoices), 200
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
                'payout_method': p.payment_method,  # Alias for frontend compatibility
                'bank_name': p.bank_name,
                'account_number': p.account_number[-4:] if p.account_number else None,  # Last 4 digits
                'status': p.status,
                'requested_at': p.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': p.completed_at.strftime('%Y-%m-%d %H:%M:%S') if p.completed_at else None,
                'failure_reason': p.failure_reason
            })

        return jsonify(payouts), 200
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

        # Create invoice
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

        # Create invoice
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
        if Category.query.count() == 0:
            default_categories = [
                Category(name='Design', slug='design', description='Logo design, graphic design, UI/UX', icon='palette'),
                Category(name='Writing & Translation', slug='writing', description='Content writing, translation, copywriting', icon='edit'),
                Category(name='Video & Animation', slug='video', description='Video editing, animation, motion graphics', icon='video'),
                Category(name='Tutoring & Education', slug='tutoring', description='Online tutoring, teaching, coaching', icon='book'),
                Category(name='Content Creation', slug='content', description='Social media content, TikTok, Instagram Reels', icon='camera'),
                Category(name='Web Development', slug='web', description='Website development, web apps', icon='code'),
                Category(name='Digital Marketing', slug='marketing', description='SEO, social media marketing, ads', icon='trending-up'),
                Category(name='Admin & Virtual Assistant', slug='admin', description='Data entry, virtual assistance, admin tasks', icon='clipboard'),
                Category(name='General Works', slug='general', description='General tasks, miscellaneous work, other services', icon='briefcase'),
            ]
            for cat in default_categories:
                db.session.add(cat)
            db.session.commit()
            print("Default categories added successfully!")

        # Add General Works category if it doesn't exist (for existing databases)
        if not Category.query.filter_by(slug='general').first():
            general_cat = Category(
                name='General Works',
                slug='general',
                description='General tasks, miscellaneous work, other services',
                icon='briefcase'
            )
            db.session.add(general_cat)
            db.session.commit()
            print("General Works category added!")

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
        <h2><span class="icon">🚀</span> Bagaimana GigHalal Berfungsi</h2>
        <p>GigHalal menghubungkan freelancers dengan klien yang mencari perkhidmatan berkualiti. Platform kami memastikan semua transaksi adalah telus, selamat dan mematuhi prinsip halal.</p>
        
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
                         page_subtitle='Ketahui bagaimana platform GigHalal berfungsi untuk freelancers dan klien',
                         content=content)

@app.route('/pricing')
def pricing():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">💰</span> Harga Telus & Berpatutan</h2>
        <p>GigHalal menawarkan struktur harga yang telus tanpa bayaran tersembunyi. Kami menggunakan sistem komisyen berperingkat yang memberi ganjaran kepada freelancers dengan projek bernilai tinggi.</p>
        
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
                    <li>Akses ke 50,000+ freelancers</li>
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
    categories_list = Category.query.all()
    
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
        <p>Terokai pelbagai kategori gig yang tersedia di GigHalal. Sama ada anda mahir dalam design, penulisan, video editing atau tutoring - pasti ada peluang untuk anda!</p>
        
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
                <div class="blog-card-title">Mengapa Penting Memilih Gig Halal</div>
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
        <p>Selamat datang ke dunia freelancing! Panduan ini akan membantu anda memulakan perjalanan sebagai freelancer di GigHalal.</p>
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
                         page_subtitle='Panduan lengkap untuk berjaya sebagai freelancer di GigHalal',
                         content=content)

@app.route('/faq')
def faq():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">❓</span> Soalan Lazim (FAQ)</h2>
        
        <div class="faq-item">
            <div class="faq-question">Apakah GigHalal?</div>
            <div class="faq-answer">GigHalal adalah platform gig economy #1 di Malaysia yang menghubungkan freelancers dengan klien. Kami fokus kepada peluang kerja yang halal dan berkah.</div>
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
            <div class="faq-answer">Anda boleh menghubungi kami melalui email di support@gighalal.com atau WhatsApp di +60 12-345 6789. Waktu operasi: Isnin-Jumaat, 9am-6pm.</div>
        </div>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='faq',
                         page_title='FAQ',
                         page_subtitle='Jawapan kepada soalan-soalan lazim tentang GigHalal',
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
                <p>support@gighalal.com</p>
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
            <li><a href="/cara-kerja" style="color: var(--primary);">Cara GigHalal Berfungsi</a></li>
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

@app.route('/syarat-terma')
def syarat_terma():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    content = '''
    <div class="content-section">
        <h2><span class="icon">📜</span> Syarat & Terma Perkhidmatan</h2>
        <p><em>Kemas kini terakhir: 15 Disember 2025</em></p>
        
        <h3>1. Penerimaan Terma</h3>
        <p>Dengan mengakses atau menggunakan platform GigHalal, anda bersetuju untuk mematuhi Syarat & Terma ini. Jika anda tidak bersetuju dengan mana-mana bahagian terma ini, anda tidak boleh menggunakan perkhidmatan kami.</p>
        
        <h3>2. Kelayakan</h3>
        <p>Untuk menggunakan GigHalal, anda mestilah:</p>
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
        <p>GigHalal mengenakan yuran berikut:</p>
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
        <p>Sebarang pertikaian antara pengguna akan diselesaikan melalui proses mediasi GigHalal terlebih dahulu. Keputusan kami adalah muktamad.</p>
        
        <h3>8. Penamatan</h3>
        <p>GigHalal berhak untuk menggantung atau menamatkan akaun anda atas sebarang pelanggaran Syarat & Terma ini.</p>
        
        <h3>9. Penafian</h3>
        <p>Platform disediakan "sebagaimana adanya". GigHalal tidak menjamin ketersediaan berterusan atau bebas ralat.</p>
        
        <h3>10. Undang-undang Yang Mentadbir</h3>
        <p>Terma ini ditadbir oleh undang-undang Malaysia. Sebarang pertikaian akan diselesaikan di mahkamah Malaysia.</p>
    </div>
    '''
    return render_template('static_page.html', 
                         user=user, 
                         active_page='syarat-terma',
                         page_title='Syarat & Terma',
                         page_subtitle='Terma perkhidmatan GigHalal',
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
            <li>Email: dpo@gighalal.com</li>
            <li>Telefon: +60 3-XXXX XXXX</li>
        </ul>
        
        <h3>14. Hubungi Kami</h3>
        <p>Untuk soalan tentang privasi, hubungi: privacy@gighalal.com</p>
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
        <p>GigHalal komited untuk menyediakan platform yang mematuhi prinsip-prinsip Islam. Berikut adalah garis panduan pematuhan halal kami.</p>
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
        
        <p>Kami bekerjasama dengan penasihat syariah untuk memastikan platform kami terus mematuhi garis panduan Islam. Jika anda mempunyai sebarang soalan atau kebimbangan tentang pematuhan halal, sila hubungi kami di halal@gighalal.com.</p>
    </div>
    
    <div class="content-section">
        <h2><span class="icon">📣</span> Laporkan Pelanggaran</h2>
        <p>Jika anda menjumpai gig yang tidak mematuhi prinsip halal, sila laporkan kepada kami. Kami akan menyiasat dan mengambil tindakan yang sewajarnya.</p>
        <p>Email: halal@gighalal.com</p>
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
        <p>GigHalal menyokong hak-hak pekerja gig dan mematuhi peraturan yang ditetapkan oleh kerajaan Malaysia.</p>
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
        <p>Sebagai pekerja gig di GigHalal, anda menikmati:</p>
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
            <p><strong>💡 Nota:</strong> GigHalal menyediakan penyata pendapatan tahunan untuk membantu anda dengan pengisytiharan cukai.</p>
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
        <p style="margin-top: 16px;">Atau hubungi kami di: legal@gighalal.com</p>
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
    categories = Category.query.all()
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
        
        return jsonify({'success': True, 'message': message.to_dict()}), 201
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
            
            gig = Gig.query.get(escrow.gig_id)
            if gig:
                gig.status = 'completed'
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Approve milestone error: {str(e)}")
        return jsonify({'error': 'Failed to approve milestone'}), 500

with app.app_context():
    init_database()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')
