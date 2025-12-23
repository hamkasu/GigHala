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
        Send bulk email to multiple recipients
        
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
        
        try:
            # Normalize to_emails to list of To objects
            to_list = []
            for recipient in to_emails:
                if isinstance(recipient, tuple):
                    email, name = recipient
                    to_list.append(To(email=email, name=name))
                else:
                    to_list.append(To(email=recipient))
            
            # Create mail object
            message = Mail(
                from_email=self.from_email,
                to_emails=to_list,
                subject=subject,
                plain_text_content=text_content,
                html_content=html_content
            )
            
            # Send email
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            return True, f"Email sent successfully to {len(to_list)} recipients.", response.status_code
            
        except Exception as e:
            error_message = f"Error sending email: {str(e)}"
            current_app.logger.error(error_message)
            return False, error_message, None
    
    def send_single_email(self, to_email, to_name, subject, html_content, text_content=None):
        """Send email to a single recipient"""
        return self.send_bulk_email([(to_email, to_name)], subject, html_content, text_content)


# Global instance
email_service = EmailService()
