# GigHalal - Platform Gig Halal #1 Malaysia

## Overview
GigHalal is a Malaysian halal gig economy platform built with Flask. It connects freelancers with clients for halal-compliant freelance work opportunities.

## Project Structure
```
/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── app.js        # Frontend JavaScript
├── requirements.txt      # Python dependencies (auto-generated)
└── files/                # Original import files (can be removed)
```

## Tech Stack
- **Backend**: Flask (Python 3.11)
- **Database**: PostgreSQL (Replit-managed)
- **Frontend**: Vanilla JavaScript with CSS
- **ORM**: SQLAlchemy

## Running the Application
The application runs on port 5000 via the "Start application" workflow.

## Key Features
- User registration and login
- Gig posting and browsing
- Halal verification system
- Category filtering
- Location-based search

## Database Models
- **User**: Freelancers and clients
- **Gig**: Job postings
- **Application**: Gig applications
- **Transaction**: Payment records
- **Review**: User reviews
- **MicroTask**: Quick tasks
- **Referral**: Referral system
- **SiteStats**: Site statistics (visitor counter)
- **Category**: Gig categories (Design, Writing, Video, etc.)
- **Wallet**: User wallet balances
- **Invoice**: Payment invoices
- **Receipt**: Payment receipts (escrow funding, payments, refunds)
- **Payout**: Freelancer payouts
- **PaymentHistory**: Transaction history
- **PortfolioItem**: Freelancer portfolio showcase items
- **Conversation**: Chat conversations between users
- **Message**: Individual chat messages
- **Notification**: User notifications (with types: message, payment, review, application, dispute, verification, milestone)
- **NotificationPreference**: User notification settings
- **IdentityVerification**: IC/MyKad verification submissions
- **Dispute**: Dispute cases between users
- **DisputeMessage**: Messages in dispute discussions
- **Milestone**: Escrow payment milestones

## New Features (December 16, 2025)

### Portfolio Management
- `/portfolio` - View and manage portfolio items
- `/profile/<username>` - Public user profile with portfolio showcase
- Supports image uploads with categories

### Real-time Messaging
- `/messages` - View all conversations
- `/messages/<id>` - Individual conversation view with polling for new messages
- `/api/messages/send` - Send messages
- `/api/messages/start` - Start new conversations
- `/api/messages/poll/<id>` - Long-polling for real-time updates

### Notifications System
- `/notifications` - View all notifications
- `/api/notifications` - Get notifications (supports unread_only filter)
- `/api/notifications/mark-read` - Mark notifications as read
- `/api/notifications/preferences` - Get/update notification preferences
- Types: message, payment, review, application, dispute, verification, milestone

### Identity Verification (IC/MyKad)
- `/verification` - Submit verification documents
- `/admin/verifications` - Admin review page for verifications
- Requires: IC front photo, IC back photo, selfie with IC
- Secure file storage with access control

### Dispute Resolution
- `/disputes` - View all disputes
- `/dispute/<id>` - View dispute details and discussion
- `/dispute/new/<gig_id>` - File new dispute
- `/admin/disputes` - Admin dispute management
- Types: quality, non_delivery, payment, harassment, other

### Escrow Milestones
- `/api/milestones/<escrow_id>` - Get milestones for escrow
- `/api/milestones/create` - Create milestones (client only)
- `/api/milestone/<id>/submit` - Submit work (freelancer)
- `/api/milestone/<id>/approve` - Approve and release payment (client)
- Automatic wallet crediting with 5% platform fee

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-configured)
- `SECRET_KEY`: Flask session secret (auto-generated if not set)

## Deployment Notes
- Uses `psycopg[binary]` instead of `psycopg2-binary` for Python 3.13 compatibility
- Database connection string automatically converts to `postgresql+psycopg://` dialect for SQLAlchemy

## Recent Changes
- December 16, 2025: Added 7 major new features: Portfolio Management (/portfolio, /profile/<username>), Real-time Messaging (/messages with polling), Notifications System (/notifications with preferences), Identity Verification (/verification with IC/MyKad upload), Dispute Resolution (/disputes, /dispute/new), Escrow Milestones (milestone-based payments), and Admin panels for verification/dispute review
- December 16, 2025: Added database models for PortfolioItem, Conversation, Message, Notification, NotificationPreference, IdentityVerification, Dispute, DisputeMessage, and Milestone
- December 16, 2025: Created SQL migration file (migrations/add_new_features.sql) for manual database schema updates
- December 16, 2025: Added secure file serving for portfolio and verification uploads with proper access control
- December 16, 2025: Added Documents page (/documents) - displays all invoices and receipts with tabs, links to view individual documents; Receipt model for escrow funding with collision-resistant receipt number generation (UUID-based), idempotent receipt creation to prevent duplicates on webhook retries; view routes /invoice/<id> and /receipt/<id> with printable templates
- December 16, 2025: Added Accepted Gigs page (/accepted-gigs) - displays all gigs where the user has an accepted application (as freelancer) or has accepted a freelancer (as client); shows gig title, role, other party info, price, status, and date; navigation link added to user dropdown menu
- December 16, 2025: Added PayHalal escrow integration - new /escrow page for clients to view and fund escrows via PayHalal (FPX/Card/E-Wallet) or manual bank transfer; includes /api/escrow/<gig_id>/pay endpoint for payment initiation, /api/payhalal/escrow-webhook for payment confirmation, /api/escrow/my-escrows for listing user escrows, and /api/escrow/<gig_id>/confirm-manual for manual transfer verification; navigation link added to user dropdown menu
- December 16, 2025: Made posted gigs on dashboard clickable - gig cards in "Your Posted Gigs" section now link to gig detail page
- December 16, 2025: Added applications management UI for gig owners - on gig detail page, owners can see all applications with freelancer info, proposed price, and Accept/Reject buttons; uses existing API endpoints /api/applications/{id}/accept and /api/applications/{id}/reject
- December 16, 2025: Added photo upload feature for gig postings - drag-and-drop UI in post_gig.html (max 5 photos, 5MB each, PNG/JPG/WEBP), secure file handling with werkzeug secure_filename, photo gallery display on gig_detail.html with fullscreen modal viewer
- December 16, 2025: Removed all JAKIM Verified references from the application - removed from translation strings (Malay/English), hero trust section, and footer badges in both index.html and base.html templates
- December 16, 2025: Enhanced Privacy Policy (/privasi) with PDPA compliance - added 5 new sections: data collection sources, obligatory data provision, cross-border data transfers, sensitive personal data consent, and Data Protection Officer (DPO) appointment details
- December 15, 2025: Added Edit Gig functionality - gig owners can now edit their posted gigs via /edit-gig/<id> route. Edit button appears on gig detail page for owners (only for open/in_progress gigs). Reuses post_gig.html template with edit_mode flag.
- December 15, 2025: Updated Pricing page to show accurate tiered commission structure (15%/10%/5%) matching the billing system - includes processing fees (2.9% + RM1) and payout fees (2%)
- December 15, 2025: Removed green HALAL badge and star/crescent icon from header navigation across all templates (base.html, index.html, gigs.html) - logo now shows just "GigHalal" text
- December 15, 2025: Added all footer static pages - Platform (Cari Gig, Kategori, Cara Kerja, Pricing), Resources (Blog, Panduan Freelancer, FAQ, Support), and Legal (Syarat & Terma, Privasi Policy, Halal Compliance, Gig Workers Bill) with full content in Bahasa Malaysia
- December 15, 2025: Created static_page.html template for consistent styling across all informational pages
- December 15, 2025: Updated footer links in base.html to connect to all new pages
- December 15, 2025: Added PWA (Progressive Web App) support - app can now be installed on iOS/Android devices from the browser, includes service worker for offline caching, mobile bottom navigation bar, install prompt banner, and app icons
- December 15, 2025: Categories navigation bar now only shows on Browse Gigs page (hidden on homepage and other pages)
- December 15, 2025: Fixed logout route to accept GET requests (redirects to homepage) in addition to POST requests
- December 15, 2025: Fixed gig detail page error handling - added null safety checks for client/escrow and proper HTTPException handling for 404s
- December 15, 2025: Enhanced dashboard applications section to show gig title, status (Menunggu/Diterima/Ditolak), and link to gig detail page
- December 15, 2025: Added error.html template for graceful error handling
- December 15, 2025: Added Escrow system for secure payments - Escrow model with status tracking (pending, funded, released, refunded, disputed), API endpoints for create/release/refund/dispute, and frontend UI with progress visualization on gig detail page
- December 14, 2025: Fixed admin Edit User functionality - saveUserChanges() now properly calls PUT API to save changes
- December 14, 2025: Added View Details button in admin Users table - shows complete user data (IC, phone, bank info, ratings, earnings)
- December 14, 2025: Added GET /api/admin/users/<user_id> endpoint for fetching complete user details
- December 14, 2025: Added User Settings page (/settings) with profile editing, password/email change, IC number, and bank account management
- December 14, 2025: Added EmailHistory model to track email changes with timestamps and IP address
- December 14, 2025: Added user dropdown menu in navigation for quick access to Dashboard, Settings, and Logout
- December 14, 2025: Added new User fields: ic_number, bank_name, bank_account_number, bank_account_holder
- December 14, 2025: Added Payment Gateway Settings in Admin page - clickable cards to select PayHalal or Stripe, with SiteSettings model and API endpoints
- December 14, 2025: Created PayHalal integration module (payhalal.py) - Malaysian Shariah-compliant payment gateway client
- December 14, 2025: Fixed admin page navigation to show logged-in user menu instead of login/register buttons
- December 14, 2025: Added gig detail page template (gig_detail.html) with full gig information display, client details, skills required, application modal form, and proper navigation for authenticated/unauthenticated users
- December 14, 2025: Added Flask route /gig/<gig_id> for viewing individual gig details with view counting (authenticated users only)
- December 13, 2025: Added 7 new categories (Pentadbiran Maya, Penghantaran & Logistik, Micro-Tasks, Pengurusan Acara, Penjagaan & Perkhidmatan, Fotografi & Videografi, Lain-lain Kreatif), fixed Kerja Am category visibility, added sample gigs for all new categories
- December 13, 2025: Fixed post gig form hanging issue - converted from JavaScript fetch to traditional server-side form submission with PRG pattern, form data preservation on errors, and deadline validation
- December 12, 2025: Updated dashboard.html, billing.html, and admin.html to extend base.html template for consistent styling
- December 12, 2025: Applied new dark navbar design (#1F2937) with "GigHalal" green branding (#1DBF73) across all pages
- December 12, 2025: Added Category model to fix Internal Server Error on /gigs and /post-gig pages
- December 11, 2025: Added Calmic logo and visitor counter to footer
- December 11, 2025: Fixed Railway deployment - replaced psycopg2-binary with psycopg for Python 3.13 compatibility
- December 11, 2025: Initial import and setup for Replit environment
