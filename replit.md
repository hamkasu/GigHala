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

## Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-configured)
- `SECRET_KEY`: Flask session secret (auto-generated if not set)

## Recent Changes
- December 11, 2025: Initial import and setup for Replit environment
