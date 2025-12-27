"""
Scheduled Jobs Module for GigHala
Handles periodic tasks like sending email digests for new gigs
"""

import os
from datetime import datetime, timedelta
from flask import render_template
from sqlalchemy import and_
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, email_service):
    """
    Send email digest of new gigs to all users who have opted in
    This job runs twice daily at 8 AM and 8 PM

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        User: User model
        Gig: Gig model
        NotificationPreference: NotificationPreference model
        EmailDigestLog: EmailDigestLog model
        email_service: EmailService instance
    """
    with app.app_context():
        try:
            logger.info("Starting new gigs email digest job...")

            # Get the last digest send time from the log
            last_digest = db.session.query(EmailDigestLog).order_by(
                EmailDigestLog.sent_at.desc()
            ).first()

            # If no previous digest, look for gigs from last 12 hours
            # Otherwise, look for gigs since the last digest
            if last_digest:
                cutoff_time = last_digest.sent_at
            else:
                cutoff_time = datetime.utcnow() - timedelta(hours=12)

            logger.info(f"Looking for gigs posted since: {cutoff_time}")

            # Query new gigs posted since the last digest
            new_gigs = db.session.query(Gig).filter(
                and_(
                    Gig.created_at > cutoff_time,
                    Gig.status == 'open'
                )
            ).order_by(Gig.created_at.desc()).all()

            logger.info(f"Found {len(new_gigs)} new gigs")

            # Get all users who have email notifications enabled for new gigs
            # Join User with NotificationPreference
            users_query = db.session.query(User).outerjoin(
                NotificationPreference,
                User.id == NotificationPreference.user_id
            ).filter(
                User.email.isnot(None)
            )

            # Filter for users with email_new_gig enabled OR no preference set (default to True)
            users = []
            for user in users_query.all():
                pref = db.session.query(NotificationPreference).filter_by(
                    user_id=user.id
                ).first()

                # If no preference exists, or if email_new_gig is True
                if not pref or pref.email_new_gig:
                    users.append(user)

            logger.info(f"Sending digest to {len(users)} users")

            if not users:
                logger.info("No users to send emails to")
                return

            # Get base URL for links in email
            base_url = os.getenv('BASE_URL', 'https://gighala.com')

            # Prepare email list
            emails_to_send = []

            for user in users:
                # Prepare personalized email content
                user_name = user.full_name or user.username or "User"

                # Render email template
                html_content = render_template(
                    'email_new_gigs_digest.html',
                    user_name=user_name,
                    gigs=new_gigs,
                    gig_count=len(new_gigs),
                    base_url=base_url
                )

                # Determine subject based on language preference
                if user.language == 'ms':
                    if len(new_gigs) == 0:
                        subject = "GigHala - Tiada Gig Baharu"
                    elif len(new_gigs) == 1:
                        subject = "GigHala - 1 Gig Baharu Tersedia!"
                    else:
                        subject = f"GigHala - {len(new_gigs)} Gig Baharu Tersedia!"
                else:
                    if len(new_gigs) == 0:
                        subject = "GigHala - No New Gigs"
                    elif len(new_gigs) == 1:
                        subject = "GigHala - 1 New Gig Available!"
                    else:
                        subject = f"GigHala - {len(new_gigs)} New Gigs Available!"

                emails_to_send.append({
                    'to': user.email,
                    'subject': subject,
                    'html': html_content
                })

            # Send bulk emails
            if emails_to_send:
                logger.info(f"Sending {len(emails_to_send)} emails...")
                success = email_service.send_bulk_email(emails_to_send)

                if success:
                    # Log the digest send
                    digest_log = EmailDigestLog(
                        digest_type='new_gigs',
                        sent_at=datetime.utcnow(),
                        recipient_count=len(emails_to_send),
                        gig_count=len(new_gigs),
                        success=True
                    )
                    db.session.add(digest_log)
                    db.session.commit()
                    logger.info(f"Successfully sent {len(emails_to_send)} emails")
                else:
                    # Log failed attempt
                    digest_log = EmailDigestLog(
                        digest_type='new_gigs',
                        sent_at=datetime.utcnow(),
                        recipient_count=len(emails_to_send),
                        gig_count=len(new_gigs),
                        success=False,
                        error_message="Email service returned failure"
                    )
                    db.session.add(digest_log)
                    db.session.commit()
                    logger.error("Failed to send emails")

            logger.info("New gigs email digest job completed")

        except Exception as e:
            logger.error(f"Error in send_new_gigs_digest: {str(e)}", exc_info=True)
            # Log the error
            try:
                digest_log = EmailDigestLog(
                    digest_type='new_gigs',
                    sent_at=datetime.utcnow(),
                    recipient_count=0,
                    gig_count=0,
                    success=False,
                    error_message=str(e)
                )
                db.session.add(digest_log)
                db.session.commit()
            except Exception as log_error:
                logger.error(f"Failed to log error: {str(log_error)}")


def init_scheduler(app, db, User, Gig, NotificationPreference, EmailDigestLog, email_service):
    """
    Initialize APScheduler with all scheduled jobs

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        User: User model
        Gig: Gig model
        NotificationPreference: NotificationPreference model
        EmailDigestLog: EmailDigestLog model
        email_service: EmailService instance

    Returns:
        scheduler: Configured APScheduler instance
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    import atexit

    # Create scheduler
    scheduler = BackgroundScheduler(daemon=True)

    # Get timezone from environment or default to Asia/Kuala_Lumpur (Malaysia)
    timezone = os.getenv('TIMEZONE', 'Asia/Kuala_Lumpur')

    # Schedule new gigs digest at 8 AM daily
    scheduler.add_job(
        func=lambda: send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, email_service),
        trigger=CronTrigger(hour=8, minute=0, timezone=timezone),
        id='new_gigs_digest_morning',
        name='Send new gigs email digest (8 AM)',
        replace_existing=True
    )

    # Schedule new gigs digest at 8 PM daily
    scheduler.add_job(
        func=lambda: send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, email_service),
        trigger=CronTrigger(hour=20, minute=0, timezone=timezone),
        id='new_gigs_digest_evening',
        name='Send new gigs email digest (8 PM)',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started with timezone: {timezone}")
    logger.info("Scheduled jobs:")
    logger.info("  - New gigs email digest at 8:00 AM")
    logger.info("  - New gigs email digest at 8:00 PM")

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    return scheduler
