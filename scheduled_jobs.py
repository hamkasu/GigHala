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


def send_matched_gigs_email(app, db, User, Gig, WorkerSpecialization, NotificationPreference, EmailDigestLog, EmailSendLog, email_service, calculate_distance):
    """
    Send AI-matched gigs to workers based on their skills, location, and preferences.
    This job runs twice daily at 9 AM and 9 PM (1 hour after the general digest).

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        User: User model
        Gig: Gig model
        WorkerSpecialization: WorkerSpecialization model
        NotificationPreference: NotificationPreference model
        EmailDigestLog: EmailDigestLog model
        EmailSendLog: EmailSendLog model
        email_service: EmailService instance
        calculate_distance: Function to calculate distance between coordinates
    """
    with app.app_context():
        try:
            logger.info("Starting AI-matched gigs email job...")

            # Import the matching service
            from gig_matching_service import GigMatchingService

            # Initialize the matching service
            matching_service = GigMatchingService(
                db=db,
                User=User,
                Gig=Gig,
                WorkerSpecialization=WorkerSpecialization,
                calculate_distance=calculate_distance
            )

            # Get the last digest send time
            last_digest = db.session.query(EmailDigestLog).filter_by(
                digest_type='matched_gigs'
            ).order_by(EmailDigestLog.sent_at.desc()).first()

            # If no previous digest, look for gigs from last 12 hours
            # Otherwise, look for gigs since the last digest
            if last_digest:
                hours_back = max(12, int((datetime.utcnow() - last_digest.sent_at).total_seconds() / 3600))
            else:
                hours_back = 12

            logger.info(f"Looking for gigs posted in the last {hours_back} hours")

            # Get all worker matches
            worker_matches = matching_service.get_all_worker_matches(
                hours_back=hours_back,
                min_score=0.3  # 30% minimum match threshold
            )

            logger.info(f"Found matches for {len(worker_matches)} workers")

            if not worker_matches:
                logger.info("No matched gigs to send")
                # Log the digest send even if no matches
                digest_log = EmailDigestLog(
                    digest_type='matched_gigs',
                    sent_at=datetime.utcnow(),
                    recipient_count=0,
                    gig_count=0,
                    success=True,
                    error_message="No matches found"
                )
                db.session.add(digest_log)
                db.session.commit()
                return

            # Get base URL for links in email
            base_url = os.getenv('BASE_URL', 'https://gighala.com')

            # Prepare emails for each worker
            emails_to_send = []
            total_matches_count = 0

            for user_id, matches in worker_matches.items():
                user = db.session.query(User).get(user_id)
                if not user or not user.email:
                    continue

                total_matches_count += len(matches)
                user_name = user.full_name or user.username or "User"

                # Render email template
                with app.test_request_context():
                    html_content = render_template(
                        'email_matched_gigs.html',
                        user_name=user_name,
                        matches=matches,
                        gig_count=len(matches),
                        base_url=base_url
                    )

                # Determine subject based on language preference
                if user.language == 'ms':
                    if len(matches) == 1:
                        subject = "GigHala - 1 Gig Yang Sesuai Untuk Anda!"
                    else:
                        subject = f"GigHala - {len(matches)} Gig Yang Sesuai Untuk Anda!"
                else:
                    if len(matches) == 1:
                        subject = "GigHala - 1 Gig Matched For You!"
                    else:
                        subject = f"GigHala - {len(matches)} Gigs Matched For You!"

                emails_to_send.append({
                    'to': user.email,
                    'subject': subject,
                    'html': html_content,
                    'user_id': user.id
                })

            # Send emails
            if emails_to_send:
                total_emails = len(emails_to_send)
                logger.info(f"Starting to send {total_emails} matched gig emails...")

                successful_sends = 0
                failed_sends = 0
                failed_recipients = []
                all_brevo_message_ids = []

                for idx, email_data in enumerate(emails_to_send, 1):
                    try:
                        logger.info(f"Sending email {idx}/{total_emails} to {email_data['to']}...")

                        success, message, status_code, details = email_service.send_single_email(
                            to_email=email_data['to'],
                            to_name=None,
                            subject=email_data['subject'],
                            html_content=email_data['html']
                        )

                        # Log individual email to database for archival
                        try:
                            import json
                            email_log = EmailSendLog(
                                email_type='digest',
                                subject=email_data['subject'],
                                html_content=email_data['html'],
                                recipient_emails=json.dumps([email_data['to']]),
                                recipient_user_id=email_data.get('user_id'),
                                recipient_count=1,
                                successful_count=1 if success else 0,
                                failed_count=0 if success else 1,
                                recipient_type='workers',
                                success=success,
                                error_message=message if not success else None,
                                brevo_message_ids=json.dumps(details.get('brevo_message_ids', [])),
                                failed_recipients=json.dumps(details.get('failed_recipients', []))
                            )
                            db.session.add(email_log)
                            db.session.commit()
                        except Exception as log_error:
                            logger.error(f"Failed to log email to database: {str(log_error)}")

                        if success:
                            successful_sends += 1
                            all_brevo_message_ids.extend(details.get('brevo_message_ids', []))
                            logger.info(f"✓ Email {idx}/{total_emails} sent successfully to {email_data['to']}")
                        else:
                            failed_sends += 1
                            failed_recipients.append(email_data['to'])
                            logger.error(f"✗ Email {idx}/{total_emails} failed for {email_data['to']}: {message}")

                    except Exception as e:
                        failed_sends += 1
                        failed_recipients.append(email_data['to'])
                        logger.error(f"✗ Email {idx}/{total_emails} error for {email_data['to']}: {str(e)}")

                # Log summary
                logger.info(f"Email sending complete: {successful_sends} succeeded, {failed_sends} failed out of {total_emails} total")
                logger.info(f"Total matched gigs sent: {total_matches_count}")

                # Log the digest send
                if successful_sends > 0:
                    digest_log = EmailDigestLog(
                        digest_type='matched_gigs',
                        sent_at=datetime.utcnow(),
                        recipient_count=successful_sends,
                        gig_count=total_matches_count,
                        success=True,
                        error_message=f"Failed: {failed_sends}" if failed_sends > 0 else None
                    )
                    db.session.add(digest_log)
                    db.session.commit()
                    logger.info(f"Successfully sent {successful_sends} matched gig emails")
                else:
                    error_msg = f"All {total_emails} emails failed"
                    digest_log = EmailDigestLog(
                        digest_type='matched_gigs',
                        sent_at=datetime.utcnow(),
                        recipient_count=0,
                        gig_count=total_matches_count,
                        success=False,
                        error_message=error_msg
                    )
                    db.session.add(digest_log)
                    db.session.commit()
                    logger.error(error_msg)

            logger.info("AI-matched gigs email job completed")

        except Exception as e:
            logger.error(f"Error in send_matched_gigs_email: {str(e)}", exc_info=True)
            try:
                digest_log = EmailDigestLog(
                    digest_type='matched_gigs',
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


def send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, EmailSendLog, email_service):
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
        EmailSendLog: EmailSendLog model
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

                # Render email template with test request context
                # This is needed because inject_translations() context processor requires session
                with app.test_request_context():
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
                    'html': html_content,
                    'user_id': user.id
                })

            # Send emails individually with progress tracking
            if emails_to_send:
                total_emails = len(emails_to_send)
                logger.info(f"Starting to send {total_emails} emails...")

                successful_sends = 0
                failed_sends = 0
                failed_recipients = []

                for idx, email_data in enumerate(emails_to_send, 1):
                    try:
                        # Log progress
                        logger.info(f"Sending email {idx}/{total_emails} to {email_data['to']}...")

                        # Send individual email
                        success, message, status_code, details = email_service.send_single_email(
                            to_email=email_data['to'],
                            to_name=None,  # Name is included in the email content
                            subject=email_data['subject'],
                            html_content=email_data['html']
                        )

                        # Log individual email to database for archival
                        try:
                            import json
                            email_log = EmailSendLog(
                                email_type='digest',
                                subject=email_data['subject'],
                                html_content=email_data['html'],
                                recipient_emails=json.dumps([email_data['to']]),
                                recipient_user_id=email_data.get('user_id'),
                                recipient_count=1,
                                successful_count=1 if success else 0,
                                failed_count=0 if success else 1,
                                recipient_type='opted_in_users',
                                success=success,
                                error_message=message if not success else None,
                                brevo_message_ids=json.dumps(details.get('brevo_message_ids', [])),
                                failed_recipients=json.dumps(details.get('failed_recipients', []))
                            )
                            db.session.add(email_log)
                            db.session.commit()
                        except Exception as log_error:
                            logger.error(f"Failed to log email to database: {str(log_error)}")

                        if success:
                            successful_sends += 1
                            logger.info(f"✓ Email {idx}/{total_emails} sent successfully to {email_data['to']}")
                        else:
                            failed_sends += 1
                            failed_recipients.append(email_data['to'])
                            logger.error(f"✗ Email {idx}/{total_emails} failed for {email_data['to']}: {message}")

                    except Exception as e:
                        failed_sends += 1
                        failed_recipients.append(email_data['to'])
                        logger.error(f"✗ Email {idx}/{total_emails} error for {email_data['to']}: {str(e)}")

                # Log final summary
                logger.info(f"Email sending complete: {successful_sends} succeeded, {failed_sends} failed out of {total_emails} total")

                # Log the digest send
                if successful_sends > 0:
                    digest_log = EmailDigestLog(
                        digest_type='new_gigs',
                        sent_at=datetime.utcnow(),
                        recipient_count=successful_sends,
                        gig_count=len(new_gigs),
                        success=True,
                        error_message=f"Failed: {failed_sends}" if failed_sends > 0 else None
                    )
                    db.session.add(digest_log)
                    db.session.commit()
                    logger.info(f"Successfully sent {successful_sends} emails")
                else:
                    # Log failed attempt
                    error_msg = f"All {total_emails} emails failed"
                    if failed_recipients:
                        error_msg += f". Recipients: {', '.join(failed_recipients[:5])}"
                    digest_log = EmailDigestLog(
                        digest_type='new_gigs',
                        sent_at=datetime.utcnow(),
                        recipient_count=0,
                        gig_count=len(new_gigs),
                        success=False,
                        error_message=error_msg
                    )
                    db.session.add(digest_log)
                    db.session.commit()
                    logger.error(error_msg)

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


def init_scheduler(app, db, User, Gig, WorkerSpecialization, NotificationPreference, EmailDigestLog, EmailSendLog, email_service, calculate_distance):
    """
    Initialize APScheduler with all scheduled jobs

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        User: User model
        Gig: Gig model
        WorkerSpecialization: WorkerSpecialization model
        NotificationPreference: NotificationPreference model
        EmailDigestLog: EmailDigestLog model
        EmailSendLog: EmailSendLog model
        email_service: EmailService instance
        calculate_distance: Function to calculate distance between coordinates

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
        func=lambda: send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, EmailSendLog, email_service),
        trigger=CronTrigger(hour=8, minute=0, timezone=timezone),
        id='new_gigs_digest_morning',
        name='Send new gigs email digest (8 AM)',
        replace_existing=True
    )

    # Schedule new gigs digest at 8 PM daily
    scheduler.add_job(
        func=lambda: send_new_gigs_digest(app, db, User, Gig, NotificationPreference, EmailDigestLog, EmailSendLog, email_service),
        trigger=CronTrigger(hour=20, minute=0, timezone=timezone),
        id='new_gigs_digest_evening',
        name='Send new gigs email digest (8 PM)',
        replace_existing=True
    )

    # Schedule AI-matched gigs at 9 AM daily (1 hour after general digest)
    scheduler.add_job(
        func=lambda: send_matched_gigs_email(app, db, User, Gig, WorkerSpecialization, NotificationPreference, EmailDigestLog, EmailSendLog, email_service, calculate_distance),
        trigger=CronTrigger(hour=9, minute=0, timezone=timezone),
        id='matched_gigs_morning',
        name='Send AI-matched gigs email (9 AM)',
        replace_existing=True
    )

    # Schedule AI-matched gigs at 9 PM daily (1 hour after general digest)
    scheduler.add_job(
        func=lambda: send_matched_gigs_email(app, db, User, Gig, WorkerSpecialization, NotificationPreference, EmailDigestLog, EmailSendLog, email_service, calculate_distance),
        trigger=CronTrigger(hour=21, minute=0, timezone=timezone),
        id='matched_gigs_evening',
        name='Send AI-matched gigs email (9 PM)',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started with timezone: {timezone}")
    logger.info("Scheduled jobs:")
    logger.info("  - New gigs email digest at 8:00 AM")
    logger.info("  - New gigs email digest at 8:00 PM")
    logger.info("  - AI-matched gigs email at 9:00 AM")
    logger.info("  - AI-matched gigs email at 9:00 PM")

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())

    return scheduler
