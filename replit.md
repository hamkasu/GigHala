# GigHala - Platform GigHala #1 Malaysia

## Overview
GigHala is a Malaysian halal gig economy platform built with Flask. Its main purpose is to connect freelancers with clients for halal-compliant freelance work opportunities, fostering a trusted marketplace for services. The platform aims to be the leading halal gig platform in Malaysia.

## User Preferences
I want iterative development. Ask before making major changes. I prefer detailed explanations. Do not make changes to the folder `files/`.

## Recent Changes (January 10, 2026)
- **Fixed mobile header visibility**: Optimized the top navigation bar for mobile devices. Logo size reduced, text size adjusted, and "Install" button styled to be fully visible on small screens (down to 360px width).
- **Database Fix**: Added missing `payment_type` column to the `gig` table to resolve Internal Server Error (500).
- **Mobile Splash Screen**: Implemented a modern splash screen for mobile users with a 2.5s display time.
- **Client Marketing**: Added "Unlock a world of skilled professionals" section to the landing page.
- **Stripe Live Mode**: Confirmed transition to live mode for real transactions.

## System Architecture
The application uses a Flask backend with PostgreSQL as the database, managed by Replit. SQLAlchemy is used as the ORM. The frontend is built with Vanilla JavaScript and CSS.

### UI/UX Decisions
The platform features a consistent dark-themed navigation bar (`#1F2937`) with a distinctive "GigHala" green branding (`#1DBF73`). It includes a mobile-first design with PWA support for installability on mobile devices and a mobile bottom navigation bar. All informational pages use a `static_page.html` template for consistent styling. Dual date display (Hijri and Gregorian) is integrated across all pages.

### Technical Implementations
- **User Management**: Registration, login, profile editing, password/email change, and bank account management.
- **Gig Management**: Posting, browsing, editing, and applying for gigs. Gigs support photo uploads.
- **Halal Verification**: System for verifying halal compliance of gigs.
- **Search & Filtering**: Category-based filtering and location-based search for gigs.
- **Payment & Escrow**: Secure escrow system with milestone-based payments, supporting Stripe and PayHalal payment gateways. Includes invoice and receipt generation.
- **Communication**: Real-time messaging and a comprehensive notification system with user preferences.
- **Ratings & Reviews**: A mutual rating system for clients and freelancers upon gig completion.
- **Portfolio Management**: Freelancers can manage and showcase their portfolio items on their public profiles.
- **Identity Verification**: Users can submit IC/MyKad documents for verification, with an admin review process.
- **Dispute Resolution**: A structured system for filing and resolving disputes between users, with admin oversight.
- **Platform Feedback**: Users can submit suggestions, complaints, and feature requests, which admins can review and respond to.
- **Admin Panels**: Dedicated interfaces for managing users, verifying identities, resolving disputes, and viewing platform feedback.

### Feature Specifications
- **Core Models**: User, Gig, Application, Transaction, Review, MicroTask, Referral, SiteStats, Category, Wallet, Invoice, Receipt, Payout, PaymentHistory, PortfolioItem, Conversation, Message, Notification, NotificationPreference, IdentityVerification, Dispute, DisputeMessage, Milestone, PlatformFeedback.
- **PWA Support**: Offline caching via service worker, install prompt, and app icons.
- **Secure File Handling**: For portfolio and verification document uploads, with access control.

## External Dependencies
- **Database**: PostgreSQL
- **Payment Gateways**:
    - Stripe (for `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`)
    - PayHalal (Malaysian Shariah-compliant payment gateway)
- **SMS Service**:
    - Twilio (for `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`)
- **Python Libraries**:
    - Flask
    - SQLAlchemy
    - `psycopg` (for PostgreSQL connectivity)
    - `hijri-converter` (for dual date display)
    - `twilio` (for SMS support)
- **Frontend Libraries**: None explicitly mentioned beyond Vanilla JS and CSS.

## SMS & WhatsApp Integration
SMS and WhatsApp support configured via Twilio. Use `sms_service.py` for both:

**SMS Functions:**
- `send_sms(to_phone, message)` - Send custom SMS
- `send_verification_sms(to_phone, code)` - Send verification code
- `send_notification_sms(to_phone, subject, message_text)` - Send notifications

**WhatsApp Functions:**
- `send_whatsapp(to_whatsapp, message)` - Send custom WhatsApp message
- `send_verification_whatsapp(to_whatsapp, code)` - Send verification code via WhatsApp
- `send_notification_whatsapp(to_whatsapp, subject, message_text)` - Send notifications via WhatsApp

Examples:
- `from sms_service import send_verification_sms; send_verification_sms('+60123456789', '123456')`
- `from sms_service import send_verification_whatsapp; send_verification_whatsapp('+60123456789', '123456')`

Credentials stored securely in environment variables: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
```