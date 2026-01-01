"""Brevo Email Service for bulk admin emails"""
import os
import brevo_python
from brevo_python.rest import ApiException
from flask import current_app


class EmailService:
    """Service for sending emails via Brevo (formerly Sendinblue)"""

    def __init__(self):
        self.api_key = os.environ.get('BREVO_API_KEY')
        self.from_email = os.environ.get('BREVO_FROM_EMAIL')
        self.from_name = os.environ.get('BREVO_FROM_NAME', 'GigHala')

    def is_configured(self):
        """Check if Brevo is properly configured"""
        return bool(self.api_key and self.from_email)

    def send_bulk_email(self, to_emails, subject, html_content, text_content=None):
        """
        Send bulk email to multiple recipients individually (BCC-style privacy)

        Each recipient receives their own email without seeing other recipients' addresses.
        This ensures complete privacy and GDPR compliance.

        Args:
            to_emails: List of email addresses or list of (email, name) tuples
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)

        Returns:
            tuple: (success: bool, message: str, response_status: int or None, details: dict)
        """
        if not self.is_configured():
            error_details = {'successful_count': 0, 'failed_count': 0, 'total_count': 0, 'brevo_message_ids': [], 'failed_recipients': []}
            return False, "Brevo is not configured. Please add BREVO_API_KEY and BREVO_FROM_EMAIL.", None, error_details

        if not to_emails:
            error_details = {'successful_count': 0, 'failed_count': 0, 'total_count': 0, 'brevo_message_ids': [], 'failed_recipients': []}
            return False, "No recipients specified.", None, error_details

        # Configure Brevo API
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = self.api_key
        api_instance = brevo_python.TransactionalEmailsApi(brevo_python.ApiClient(configuration))

        # Normalize to_emails to list of (email, name) tuples
        recipient_list = []
        for recipient in to_emails:
            if isinstance(recipient, tuple):
                email, name = recipient
                recipient_list.append((email, name))
            else:
                recipient_list.append((recipient, None))

        # Track success and failures
        successful_sends = 0
        failed_sends = 0
        failed_recipients = []
        brevo_message_ids = []
        total_recipients = len(recipient_list)

        current_app.logger.info(f"[EMAIL_SEND] Starting to send {total_recipients} emails with subject: '{subject}'")

        for idx, (email, name) in enumerate(recipient_list, 1):
            try:
                # Log progress
                current_app.logger.info(f"[EMAIL_SEND] Sending email {idx}/{total_recipients} to {email}...")

                # Create email object for this recipient
                to_recipient = {"email": email}
                if name:
                    to_recipient["name"] = name

                send_smtp_email = brevo_python.SendSmtpEmail(
                    to=[to_recipient],
                    sender={"email": self.from_email, "name": self.from_name},
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )

                # Send email to this single recipient
                api_response = api_instance.send_transac_email(send_smtp_email)

                # Brevo returns a message ID if successful
                if api_response and hasattr(api_response, 'message_id'):
                    successful_sends += 1
                    brevo_message_ids.append(api_response.message_id)
                    current_app.logger.info(f"[EMAIL_SEND] ✓ Email {idx}/{total_recipients} sent successfully to {email} (Brevo ID: {api_response.message_id})")
                else:
                    failed_sends += 1
                    failed_recipients.append(email)
                    current_app.logger.error(f"[EMAIL_SEND] ✗ Email {idx}/{total_recipients} failed for {email}: No message ID returned")

            except ApiException as e:
                failed_sends += 1
                failed_recipients.append(email)
                current_app.logger.error(f"[EMAIL_SEND] ✗ Email {idx}/{total_recipients} error for {email}: API Error - {str(e)}")
            except Exception as e:
                failed_sends += 1
                failed_recipients.append(email)
                current_app.logger.error(f"[EMAIL_SEND] ✗ Email {idx}/{total_recipients} error for {email}: {str(e)}")

        # Log final summary
        current_app.logger.info(f"[EMAIL_SEND] Email sending complete: {successful_sends} succeeded, {failed_sends} failed out of {total_recipients} total")

        # Prepare detailed result
        result_details = {
            'successful_count': successful_sends,
            'failed_count': failed_sends,
            'total_count': total_recipients,
            'brevo_message_ids': brevo_message_ids,
            'failed_recipients': failed_recipients
        }

        # Prepare result message
        if successful_sends == total_recipients:
            message = f"Email sent successfully to all {successful_sends} recipients."
            current_app.logger.info(f"[EMAIL_SEND] SUCCESS: {message}")
            return True, message, 200, result_details
        elif successful_sends > 0:
            message = f"Email sent to {successful_sends}/{total_recipients} recipients. {failed_sends} failed."
            if failed_recipients:
                message += f" Failed: {', '.join(failed_recipients[:5])}"
                if len(failed_recipients) > 5:
                    message += f" and {len(failed_recipients) - 5} more"
            current_app.logger.warning(f"[EMAIL_SEND] PARTIAL: {message}")
            return True, message, 207, result_details  # 207 Multi-Status
        else:
            message = f"Failed to send email to all {total_recipients} recipients."
            current_app.logger.error(f"[EMAIL_SEND] FAILED: {message}")
            return False, message, None, result_details

    def send_single_email(self, to_email, to_name, subject, html_content, text_content=None):
        """Send email to a single recipient"""
        return self.send_bulk_email([(to_email, to_name)], subject, html_content, text_content)


# Global instance
email_service = EmailService()
