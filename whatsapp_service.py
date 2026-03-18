import os
import requests
from flask import current_app


def _get_meta_config():
    """Return Meta WhatsApp API configuration from environment."""
    access_token = os.environ.get('META_WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.environ.get('META_WHATSAPP_PHONE_NUMBER_ID')
    return access_token, phone_number_id


def _is_configured():
    access_token, phone_number_id = _get_meta_config()
    return bool(access_token and phone_number_id)


def _format_phone(phone):
    """Normalise phone number to E.164 without leading +."""
    if phone.startswith('01'):
        phone = '6' + phone  # 01X -> 601X
    elif phone.startswith('+'):
        phone = phone[1:]
    return phone


def send_whatsapp_text(to_phone, message):
    """
    Send a free-form text WhatsApp message via Meta Cloud API.

    Note: free-form text can only be sent within a 24-hour customer service
    window (i.e. the recipient must have messaged the business first).

    Args:
        to_phone (str): Recipient phone number (e.g. +60147804528 or 60147804528)
        message (str): Text message body

    Returns:
        dict: {'status': 'success'|'error', 'message_id': str|None, 'error': str|None}
    """
    access_token, phone_number_id = _get_meta_config()
    if not access_token or not phone_number_id:
        return {'status': 'error', 'message_id': None, 'error': 'Meta WhatsApp API not configured'}

    to = _format_phone(to_phone)
    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'text',
        'text': {'body': message},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()

        if response.ok and 'messages' in data:
            msg_id = data['messages'][0].get('id')
            current_app.logger.info(f"WhatsApp message sent to {to_phone}. ID: {msg_id}")
            return {'status': 'success', 'message_id': msg_id, 'error': None}
        else:
            error = data.get('error', {}).get('message', 'Unknown error')
            current_app.logger.error(f"Meta WhatsApp API error for {to_phone}: {error}")
            return {'status': 'error', 'message_id': None, 'error': error}

    except Exception as e:
        current_app.logger.error(f"Failed to send WhatsApp to {to_phone}: {str(e)}")
        return {'status': 'error', 'message_id': None, 'error': str(e)}


def send_whatsapp_template(to_phone, template_name, language_code='en_US', components=None):
    """
    Send a template WhatsApp message via Meta Cloud API.

    Template messages can be sent to any opted-in user regardless of the
    24-hour window.

    Args:
        to_phone (str): Recipient phone number
        template_name (str): Approved template name (e.g. 'hello_world')
        language_code (str): Template language code (default 'en_US')
        components (list|None): Optional template components for variable substitution

    Returns:
        dict: {'status': 'success'|'error', 'message_id': str|None, 'error': str|None}
    """
    access_token, phone_number_id = _get_meta_config()
    if not access_token or not phone_number_id:
        return {'status': 'error', 'message_id': None, 'error': 'Meta WhatsApp API not configured'}

    to = _format_phone(to_phone)
    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    template = {'name': template_name, 'language': {'code': language_code}}
    if components:
        template['components'] = components

    payload = {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'template',
        'template': template,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()

        if response.ok and 'messages' in data:
            msg_id = data['messages'][0].get('id')
            current_app.logger.info(f"WhatsApp template '{template_name}' sent to {to_phone}. ID: {msg_id}")
            return {'status': 'success', 'message_id': msg_id, 'error': None}
        else:
            error = data.get('error', {}).get('message', 'Unknown error')
            current_app.logger.error(f"Meta WhatsApp template error for {to_phone}: {error}")
            return {'status': 'error', 'message_id': None, 'error': error}

    except Exception as e:
        current_app.logger.error(f"Failed to send WhatsApp template to {to_phone}: {str(e)}")
        return {'status': 'error', 'message_id': None, 'error': str(e)}


def send_verification_whatsapp(to_phone, code):
    """Send OTP verification code via WhatsApp text message."""
    message = (
        f"Kod pengesahan GigHala anda: {code}\n\n"
        "Jangan berkongsi kod ini dengan sesiapa. Kod akan tamat dalam 10 minit."
    )
    return send_whatsapp_text(to_phone, message)


def send_notification_whatsapp(to_phone, subject, message_text):
    """Send a notification via WhatsApp text message."""
    message = f"{subject}\n\n{message_text}\n\nGigHala Platform"
    return send_whatsapp_text(to_phone, message)


def is_configured():
    """Return True if the Meta WhatsApp service is configured."""
    return _is_configured()
