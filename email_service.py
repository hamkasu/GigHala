"""Brevo Email Service for bulk admin emails"""
import os
import re
from flask import current_app

try:
    import brevo
    BREVO_AVAILABLE = True
except ImportError:
    brevo = None
    BREVO_AVAILABLE = False


def _parse_brevo_error(exc):
    """
    Inspect a Brevo API exception and return (is_ip_blocked, human_message).

    Brevo returns HTTP 401 with code='unauthorized' and a message that
    mentions "unrecognised IP address" when the server IP is not whitelisted.
    We detect this pattern so we can abort the send loop immediately instead
    of repeating the same failure for every recipient.
    """
    err_str = str(exc)
    # Look for the fingerprint Brevo uses for IP-whitelist rejections
    if 'status_code: 401' in err_str and (
        'unrecognised IP' in err_str or
        'unauthorized' in err_str.lower()
    ):
        # Try to pull the IP out of the error body
        ip_match = re.search(r'unrecognised IP address ([\d.]+)', err_str)
        ip_hint = f" <code>{ip_match.group(1)}</code>" if ip_match else ""
        msg = (
            f"🚫 Brevo IP not whitelisted: server IP{ip_hint} was rejected. "
            f"Add it at <a href='https://app.brevo.com/security/authorised_ips' "
            f"target='_blank' style='color:#7c3aed;font-weight:600;'>"
            f"app.brevo.com/security/authorised_ips</a> then retry."
        )
        return True, msg
    return False, str(exc)


class EmailService:
    """Service for sending emails via Brevo (formerly Sendinblue)"""

    def __init__(self):
        self.api_key = os.environ.get('BREVO_API_KEY')
        self.from_email = os.environ.get('BREVO_FROM_EMAIL')
        self.from_name = os.environ.get('BREVO_FROM_NAME', 'GigHala')

    def is_configured(self):
        """Check if Brevo is properly configured"""
        return BREVO_AVAILABLE and bool(self.api_key and self.from_email)

    def send_bulk_email(self, to_emails, subject, html_content, text_content=None, attachments=None):
        """
        Send bulk email to multiple recipients individually (BCC-style privacy)

        Each recipient receives their own email without seeing other recipients' addresses.
        This ensures complete privacy and GDPR compliance.

        Args:
            to_emails: List of email addresses or list of (email, name) tuples
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            attachments: List of dicts with 'content' (base64 string) and 'name' (filename) (optional)

        Returns:
            tuple: (success: bool, message: str, response_status: int or None, details: dict)
        """
        if not self.is_configured():
            error_details = {'successful_count': 0, 'failed_count': 0, 'total_count': 0, 'brevo_message_ids': [], 'failed_recipients': []}
            return False, "Brevo is not configured. Please add BREVO_API_KEY and BREVO_FROM_EMAIL.", None, error_details

        if not to_emails:
            error_details = {'successful_count': 0, 'failed_count': 0, 'total_count': 0, 'brevo_message_ids': [], 'failed_recipients': []}
            return False, "No recipients specified.", None, error_details

        # Create Brevo client (v4 API)
        client = brevo.Brevo(api_key=self.api_key)

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
        successful_recipients = []
        failed_recipients = []
        brevo_message_ids = []
        total_recipients = len(recipient_list)

        current_app.logger.info(f"[EMAIL_SEND] Starting to send {total_recipients} emails with subject: '{subject}'")

        for idx, (email, name) in enumerate(recipient_list, 1):
            try:
                current_app.logger.info(f"[EMAIL_SEND] Sending email {idx}/{total_recipients} to {email}...")

                # Build to recipient
                to_item = {"email": email}
                if name:
                    to_item["name"] = name

                # Build sender
                sender = {"email": self.from_email, "name": self.from_name}

                send_kwargs = dict(
                    to=[to_item],
                    sender=sender,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                )
                if attachments:
                    send_kwargs['attachment'] = attachments

                api_response = client.transactional_emails.send_transac_email(**send_kwargs)

                if api_response and hasattr(api_response, 'message_id'):
                    successful_sends += 1
                    successful_recipients.append(email)
                    brevo_message_ids.append(api_response.message_id)
                    current_app.logger.info(f"[EMAIL_SEND] ✓ Email {idx}/{total_recipients} sent successfully to {email} (Brevo ID: {api_response.message_id})")
                else:
                    failed_sends += 1
                    failed_recipients.append(email)
                    current_app.logger.error(f"[EMAIL_SEND] ✗ Email {idx}/{total_recipients} failed for {email}: No message ID returned")

            except Exception as e:
                failed_sends += 1
                failed_recipients.append(email)

                is_ip_blocked, human_msg = _parse_brevo_error(e)
                current_app.logger.error(
                    f"[EMAIL_SEND] ✗ Email {idx}/{total_recipients} error for {email}: {str(e)}"
                )

                if is_ip_blocked:
                    # No point hammering Brevo with 100+ more requests —
                    # every one will get the same 401.  Abort now.
                    remaining = total_recipients - idx
                    failed_sends += remaining
                    failed_recipients += [r[0] for r in recipient_list[idx:]]
                    current_app.logger.error(
                        f"[EMAIL_SEND] Aborting send loop early — IP not whitelisted. "
                        f"Skipped remaining {remaining} recipients. {human_msg}"
                    )
                    error_details = {
                        'successful_count': successful_sends,
                        'failed_count': failed_sends,
                        'total_count': total_recipients,
                        'successful_recipients': successful_recipients,
                        'failed_recipients': failed_recipients,
                        'brevo_message_ids': brevo_message_ids
                    }
                    return False, human_msg, 401, error_details

        current_app.logger.info(
            f"[EMAIL_SEND] Email sending complete: {successful_sends} succeeded, "
            f"{failed_sends} failed out of {total_recipients} total"
        )

        result_details = {
            'successful_count': successful_sends,
            'failed_count': failed_sends,
            'total_count': total_recipients,
            'successful_recipients': successful_recipients,
            'failed_recipients': failed_recipients,
            'brevo_message_ids': brevo_message_ids
        }

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
            return True, message, 207, result_details
        else:
            message = f"Failed to send email to all {total_recipients} recipients."
            current_app.logger.error(f"[EMAIL_SEND] FAILED: {message}")
            return False, message, None, result_details

    def send_single_email(self, to_email, to_name, subject, html_content, text_content=None, attachments=None):
        """Send email to a single recipient"""
        return self.send_bulk_email([(to_email, to_name)], subject, html_content, text_content, attachments)

    def send_email(self, to_email, subject, html_content, text_content=None, to_name=None, attachments=None):
        """
        Send email to a single recipient (backward compatibility wrapper)

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
            to_name: Recipient name (optional)
            attachments: List of dicts with 'content' (base64 string) and 'name' (filename) (optional)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        success, message, status_code, details = self.send_single_email(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            attachments=attachments
        )
        return success


# Global instance
email_service = EmailService()
