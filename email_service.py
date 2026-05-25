"""
GigHala Email Service — multi-provider

Active provider is selected by the EMAIL_PROVIDER environment variable
(default: ses):

  ses       (default)  — Amazon SES
                         requires AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
                         optional: AWS_SES_REGION (default ap-southeast-1)
  sendgrid             — Twilio SendGrid
                         requires SENDGRID_API_KEY
  brevo     (legacy)   — Brevo / Sendinblue
                         requires BREVO_API_KEY

FROM address is always taken from:
  EMAIL_FROM_ADDRESS  (e.g. noreply@gighala.com)
  EMAIL_FROM_NAME     (default: GigHala)

Public interface is identical for all providers — no other file needs changing.
"""

import os
import re
from flask import current_app

# ---------------------------------------------------------------------------
# Optional provider SDKs — imported lazily so missing packages only fail
# when that specific provider is actually used.
# ---------------------------------------------------------------------------
try:
    import brevo
    BREVO_AVAILABLE = True
except ImportError:
    brevo = None
    BREVO_AVAILABLE = False

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import (
        Mail, To, From as SGFrom, ReplyTo,
        Attachment, FileContent, FileName, FileType, Disposition
    )
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    import boto3
    from botocore.exceptions import ClientError as BotoClientError
    SES_AVAILABLE = True
except ImportError:
    boto3 = None
    SES_AVAILABLE = False


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _empty_details(total=0):
    return {
        'successful_count': 0,
        'failed_count': total,
        'total_count': total,
        'successful_recipients': [],
        'failed_recipients': [],
        'message_ids': [],
        # keep legacy key name so existing callers don't break
        'brevo_message_ids': [],
    }


def _parse_brevo_error(exc):
    """Detect Brevo's IP-whitelist 401 and return an actionable message."""
    err_str = str(exc)
    if 'status_code: 401' in err_str and (
        'unrecognised IP' in err_str or 'unauthorized' in err_str.lower()
    ):
        ip_match = re.search(r'unrecognised IP address ([\d.]+)', err_str)
        ip_hint = f" <code>{ip_match.group(1)}</code>" if ip_match else ""
        msg = (
            f"🚫 Brevo IP not whitelisted: server IP{ip_hint} was rejected. "
            f"Add it at <a href='https://app.brevo.com/security/authorised_ips' "
            f"target='_blank' style='color:#7c3aed;font-weight:600;'>"
            f"app.brevo.com/security/authorised_ips</a> then retry."
        )
        return True, msg
    return False, err_str


# ---------------------------------------------------------------------------
# EmailService
# ---------------------------------------------------------------------------

class EmailService:
    """
    Provider-agnostic email service.

    All send methods return:
        (success: bool, message: str, http_status: int|None, details: dict)
    """

    def __init__(self):
        self.provider    = os.environ.get('EMAIL_PROVIDER', 'ses').lower()
        self.from_email  = (
            os.environ.get('EMAIL_FROM_ADDRESS') or
            os.environ.get('BREVO_FROM_EMAIL', '')
        )
        self.from_name   = (
            os.environ.get('EMAIL_FROM_NAME') or
            os.environ.get('BREVO_FROM_NAME', 'GigHala')
        )

        # Provider-specific keys
        self.sendgrid_key = os.environ.get('SENDGRID_API_KEY', '')
        self.brevo_key    = os.environ.get('BREVO_API_KEY', '')
        self.ses_region   = os.environ.get('AWS_SES_REGION', 'ap-southeast-2')
        self.ses_access   = os.environ.get('AWS_ACCESS_KEY_ID', '')
        self.ses_secret   = os.environ.get('AWS_SECRET_ACCESS_KEY', '')

    # ------------------------------------------------------------------
    # Configuration check
    # ------------------------------------------------------------------

    def is_configured(self):
        if self.provider == 'sendgrid':
            return SENDGRID_AVAILABLE and bool(self.sendgrid_key and self.from_email)
        if self.provider == 'ses':
            return SES_AVAILABLE and bool(self.ses_access and self.ses_secret and self.from_email)
        # brevo (default / legacy)
        return BREVO_AVAILABLE and bool(self.brevo_key and self.from_email)

    def _not_configured_error(self, total):
        msgs = {
            'sendgrid': 'Set SENDGRID_API_KEY and EMAIL_FROM_ADDRESS.',
            'ses':      'Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and EMAIL_FROM_ADDRESS.',
            'brevo':    'Set BREVO_API_KEY and EMAIL_FROM_ADDRESS (or BREVO_FROM_EMAIL).',
        }
        hint = msgs.get(self.provider, 'Check EMAIL_PROVIDER and related env vars.')
        return False, f'Email provider "{self.provider}" is not configured. {hint}', None, _empty_details(total)

    # ------------------------------------------------------------------
    # Public API — identical interface for all call sites
    # ------------------------------------------------------------------

    def send_bulk_email(self, to_emails, subject, html_content,
                        text_content=None, attachments=None):
        """
        Send one email per recipient (BCC-style privacy).

        to_emails: list of email strings or (email, name) tuples.
        Returns:   (success, message, http_status, details)
        """
        if not to_emails:
            return False, 'No recipients specified.', None, _empty_details(0)

        if not self.is_configured():
            return self._not_configured_error(len(to_emails))

        # Normalise recipient list
        recipient_list = []
        for r in to_emails:
            if isinstance(r, tuple):
                recipient_list.append(r)
            else:
                recipient_list.append((r, None))

        if self.provider == 'sendgrid':
            return self._send_bulk_sendgrid(
                recipient_list, subject, html_content, text_content, attachments)
        if self.provider == 'ses':
            return self._send_bulk_ses(
                recipient_list, subject, html_content, text_content, attachments)
        return self._send_bulk_brevo(
            recipient_list, subject, html_content, text_content, attachments)

    def send_single_email(self, to_email, to_name, subject, html_content,
                          text_content=None, attachments=None):
        """Send to a single recipient."""
        return self.send_bulk_email(
            [(to_email, to_name)], subject, html_content, text_content, attachments)

    def send_email(self, to_email, subject, html_content,
                   text_content=None, to_name=None, attachments=None):
        """Backwards-compatibility wrapper — returns bool only."""
        success, _, _, _ = self.send_single_email(
            to_email, to_name, subject, html_content, text_content, attachments)
        return success

    # ------------------------------------------------------------------
    # SendGrid implementation
    # ------------------------------------------------------------------

    def _send_bulk_sendgrid(self, recipient_list, subject, html_content,
                             text_content, attachments):
        sg = SendGridAPIClient(api_key=self.sendgrid_key)
        total = len(recipient_list)
        successful_sends, failed_sends = 0, 0
        successful_recipients, failed_recipients, message_ids = [], [], []

        current_app.logger.info(
            f"[EMAIL_SEND] SendGrid: sending {total} emails — '{subject}'"
        )

        for idx, (email, name) in enumerate(recipient_list, 1):
            try:
                mail = Mail(
                    from_email=(self.from_email, self.from_name),
                    to_emails=To(email=email, name=name or ''),
                    subject=subject,
                    html_content=html_content,
                )
                if text_content:
                    mail.plain_text_content = text_content

                if attachments:
                    for att in attachments:
                        sg_att = Attachment(
                            file_content=FileContent(att['content']),
                            file_name=FileName(att['name']),
                            disposition=Disposition('attachment'),
                        )
                        mail.attachment = sg_att

                response = sg.send(mail)

                if response.status_code in (200, 202):
                    msg_id = response.headers.get('X-Message-Id', '')
                    successful_sends += 1
                    successful_recipients.append(email)
                    message_ids.append(msg_id)
                    current_app.logger.info(
                        f"[EMAIL_SEND] ✓ {idx}/{total} → {email} (ID: {msg_id})"
                    )
                else:
                    failed_sends += 1
                    failed_recipients.append(email)
                    current_app.logger.error(
                        f"[EMAIL_SEND] ✗ {idx}/{total} → {email}: "
                        f"HTTP {response.status_code}"
                    )

            except Exception as e:
                failed_sends += 1
                failed_recipients.append(email)
                current_app.logger.error(
                    f"[EMAIL_SEND] ✗ {idx}/{total} → {email}: {e}"
                )

        return self._build_result(
            successful_sends, failed_sends, total,
            successful_recipients, failed_recipients, message_ids
        )

    # ------------------------------------------------------------------
    # Amazon SES implementation
    # ------------------------------------------------------------------

    def _ses_client(self):
        return boto3.client(
            'ses',
            region_name=self.ses_region,
            aws_access_key_id=self.ses_access or None,
            aws_secret_access_key=self.ses_secret or None,
        )

    def _send_bulk_ses(self, recipient_list, subject, html_content,
                        text_content, attachments):
        """
        SES send_email — plain text + HTML.
        Attachments require SES send_raw_email (MIME); if attachments are
        provided we log a warning and skip them (add MIME support if needed).
        """
        client = self._ses_client()
        total = len(recipient_list)
        successful_sends, failed_sends = 0, 0
        successful_recipients, failed_recipients, message_ids = [], [], []

        if attachments:
            current_app.logger.warning(
                '[EMAIL_SEND] SES provider: attachments are not yet supported '
                'and will be skipped. Switch to SendGrid for attachment support.'
            )

        current_app.logger.info(
            f"[EMAIL_SEND] SES: sending {total} emails — '{subject}'"
        )

        for idx, (email, name) in enumerate(recipient_list, 1):
            try:
                source = (
                    f'{self.from_name} <{self.from_email}>'
                    if self.from_name else self.from_email
                )
                body = {'Html': {'Data': html_content, 'Charset': 'UTF-8'}}
                if text_content:
                    body['Text'] = {'Data': text_content, 'Charset': 'UTF-8'}

                response = client.send_email(
                    Source=source,
                    Destination={'ToAddresses': [email]},
                    Message={
                        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                        'Body': body,
                    },
                )
                msg_id = response.get('MessageId', '')
                successful_sends += 1
                successful_recipients.append(email)
                message_ids.append(msg_id)
                current_app.logger.info(
                    f"[EMAIL_SEND] ✓ {idx}/{total} → {email} (ID: {msg_id})"
                )

            except Exception as e:
                failed_sends += 1
                failed_recipients.append(email)
                current_app.logger.error(
                    f"[EMAIL_SEND] ✗ {idx}/{total} → {email}: {e}"
                )

        return self._build_result(
            successful_sends, failed_sends, total,
            successful_recipients, failed_recipients, message_ids
        )

    # ------------------------------------------------------------------
    # Brevo implementation (legacy — kept for backwards compatibility)
    # ------------------------------------------------------------------

    def _send_bulk_brevo(self, recipient_list, subject, html_content,
                          text_content, attachments):
        client = brevo.Brevo(api_key=self.brevo_key)
        total = len(recipient_list)
        successful_sends, failed_sends = 0, 0
        successful_recipients, failed_recipients, message_ids = [], [], []

        current_app.logger.info(
            f"[EMAIL_SEND] Brevo: sending {total} emails — '{subject}'"
        )

        for idx, (email, name) in enumerate(recipient_list, 1):
            try:
                to_item = {'email': email}
                if name:
                    to_item['name'] = name

                send_kwargs = dict(
                    to=[to_item],
                    sender={'email': self.from_email, 'name': self.from_name},
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                )
                if attachments:
                    send_kwargs['attachment'] = attachments

                api_response = client.transactional_emails.send_transac_email(
                    **send_kwargs)

                if api_response and hasattr(api_response, 'message_id'):
                    successful_sends += 1
                    successful_recipients.append(email)
                    message_ids.append(api_response.message_id)
                    current_app.logger.info(
                        f"[EMAIL_SEND] ✓ {idx}/{total} → {email} "
                        f"(ID: {api_response.message_id})"
                    )
                else:
                    failed_sends += 1
                    failed_recipients.append(email)
                    current_app.logger.error(
                        f"[EMAIL_SEND] ✗ {idx}/{total} → {email}: no message_id"
                    )

            except Exception as e:
                failed_sends += 1
                failed_recipients.append(email)
                is_ip_blocked, human_msg = _parse_brevo_error(e)
                current_app.logger.error(
                    f"[EMAIL_SEND] ✗ {idx}/{total} → {email}: {e}"
                )
                if is_ip_blocked:
                    remaining = total - idx
                    failed_sends += remaining
                    failed_recipients += [r[0] for r in recipient_list[idx:]]
                    current_app.logger.error(
                        f"[EMAIL_SEND] Aborting — IP not whitelisted. "
                        f"Skipped {remaining} remaining recipients."
                    )
                    details = _empty_details(total)
                    details.update({
                        'successful_count': successful_sends,
                        'failed_count': failed_sends,
                        'failed_recipients': failed_recipients,
                        'message_ids': message_ids,
                        'brevo_message_ids': message_ids,
                    })
                    return False, human_msg, 401, details

        return self._build_result(
            successful_sends, failed_sends, total,
            successful_recipients, failed_recipients, message_ids
        )

    # ------------------------------------------------------------------
    # Shared result builder
    # ------------------------------------------------------------------

    def _build_result(self, successful_sends, failed_sends, total,
                      successful_recipients, failed_recipients, message_ids):
        current_app.logger.info(
            f"[EMAIL_SEND] Done: {successful_sends} sent, "
            f"{failed_sends} failed out of {total}"
        )
        details = {
            'successful_count': successful_sends,
            'failed_count': failed_sends,
            'total_count': total,
            'successful_recipients': successful_recipients,
            'failed_recipients': failed_recipients,
            'message_ids': message_ids,
            'brevo_message_ids': message_ids,   # legacy key — keep for callers
        }
        if successful_sends == total:
            return True, f'Email sent successfully to all {successful_sends} recipients.', 200, details
        if successful_sends > 0:
            tail = ''
            if failed_recipients:
                sample = ', '.join(failed_recipients[:5])
                tail = f' Failed: {sample}'
                if len(failed_recipients) > 5:
                    tail += f' and {len(failed_recipients) - 5} more'
            return True, (
                f'Email sent to {successful_sends}/{total} recipients. '
                f'{failed_sends} failed.{tail}'
            ), 207, details
        return False, f'Failed to send email to all {total} recipients.', None, details


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
email_service = EmailService()
