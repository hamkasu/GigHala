"""SendGrid Email Service for bulk admin emails"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
from flask import current_app


class EmailService:
    """Service for sending emails via SendGrid"""
    
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL')
        
    def is_configured(self):
        """Check if SendGrid is properly configured"""
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
            tuple: (success: bool, message: str, response_status: int or None)
        """
        if not self.is_configured():
            return False, "SendGrid is not configured. Please add SENDGRID_API_KEY and SENDGRID_FROM_EMAIL.", None

        if not to_emails:
            return False, "No recipients specified.", None

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

        # Send individual emails to each recipient
        sg = SendGridAPIClient(self.api_key)

        for email, name in recipient_list:
            try:
                # Create individual mail object for this recipient only
                message = Mail(
                    from_email=self.from_email,
                    to_emails=To(email=email, name=name) if name else email,
                    subject=subject,
                    plain_text_content=text_content,
                    html_content=html_content
                )

                # Send email to this single recipient
                response = sg.send(message)

                # Check if send was successful (2xx status codes)
                if 200 <= response.status_code < 300:
                    successful_sends += 1
                else:
                    failed_sends += 1
                    failed_recipients.append(email)
                    current_app.logger.warning(f"Non-success status {response.status_code} for {email}")

            except Exception as e:
                failed_sends += 1
                failed_recipients.append(email)
                current_app.logger.error(f"Error sending email to {email}: {str(e)}")

        # Prepare result message
        total_recipients = len(recipient_list)

        if successful_sends == total_recipients:
            return True, f"Email sent successfully to all {successful_sends} recipients.", 200
        elif successful_sends > 0:
            message = f"Email sent to {successful_sends}/{total_recipients} recipients. {failed_sends} failed."
            if failed_recipients:
                message += f" Failed: {', '.join(failed_recipients[:5])}"
                if len(failed_recipients) > 5:
                    message += f" and {len(failed_recipients) - 5} more"
            current_app.logger.warning(message)
            return True, message, 207  # 207 Multi-Status
        else:
            message = f"Failed to send email to all {total_recipients} recipients."
            current_app.logger.error(message)
            return False, message, None
    
    def send_single_email(self, to_email, to_name, subject, html_content, text_content=None):
        """Send email to a single recipient"""
        return self.send_bulk_email([(to_email, to_name)], subject, html_content, text_content)


# Global instance
email_service = EmailService()
