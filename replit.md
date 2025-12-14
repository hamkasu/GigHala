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
- **Payout**: Freelancer payouts
- **PaymentHistory**: Transaction history

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-configured)
- `SECRET_KEY`: Flask session secret (auto-generated if not set)

## Deployment Notes
- Uses `psycopg[binary]` instead of `psycopg2-binary` for Python 3.13 compatibility
- Database connection string automatically converts to `postgresql+psycopg://` dialect for SQLAlchemy

## Recent Changes
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
