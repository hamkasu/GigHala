import os
from twilio.rest import Client
from flask import current_app

def get_twilio_client():
    """Initialize and return Twilio client"""
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    
    if not account_sid or not auth_token:
        raise ValueError("Twilio credentials not configured")
    
    return Client(account_sid, auth_token)

def send_sms(to_phone, message):
    """
    Send SMS message via Twilio
    
    Args:
        to_phone (str): Recipient phone number (format: +60123456789)
        message (str): SMS message content
    
    Returns:
        dict: Response with status, message_sid, and error (if any)
    """
    try:
        client = get_twilio_client()
        from_phone = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not from_phone:
            raise ValueError("TWILIO_PHONE_NUMBER not configured")
        
        msg = client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone
        )
        
        current_app.logger.info(f"SMS sent successfully to {to_phone}. SID: {msg.sid}")
        
        return {
            'status': 'success',
            'message_sid': msg.sid,
            'error': None
        }
    
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"Failed to send SMS to {to_phone}: {error_msg}")
        
        return {
            'status': 'error',
            'message_sid': None,
            'error': error_msg
        }

def send_verification_sms(to_phone, code):
    """
    Send verification code SMS
    
    Args:
        to_phone (str): Recipient phone number
        code (str): Verification code
    
    Returns:
        dict: Response with status and details
    """
    message = f"Kod pengesahan GigHala anda: {code}\n\nJangan berkongsi kod ini dengan sesiapa. Kod akan tamat dalam 10 minit."
    return send_sms(to_phone, message)

def send_notification_sms(to_phone, subject, message_text):
    """
    Send notification SMS
    
    Args:
        to_phone (str): Recipient phone number
        subject (str): SMS subject/title
        message_text (str): SMS message content
    
    Returns:
        dict: Response with status and details
    """
    message = f"{subject}\n\n{message_text}\n\nGigHala Platform"
    return send_sms(to_phone, message)

def send_whatsapp(to_whatsapp, message):
    """
    Send WhatsApp message via Twilio
    
    Args:
        to_whatsapp (str): Recipient WhatsApp number (format: whatsapp:+60123456789 or +60123456789)
        message (str): WhatsApp message content
    
    Returns:
        dict: Response with status, message_sid, and error (if any)
    """
    try:
        client = get_twilio_client()
        from_whatsapp = f"whatsapp:{os.environ.get('TWILIO_PHONE_NUMBER')}"
        
        if not to_whatsapp.startswith('whatsapp:'):
            to_whatsapp = f"whatsapp:{to_whatsapp}"
        
        msg = client.messages.create(
            body=message,
            from_=from_whatsapp,
            to=to_whatsapp
        )
        
        current_app.logger.info(f"WhatsApp message sent to {to_whatsapp}. SID: {msg.sid}")
        
        return {
            'status': 'success',
            'message_sid': msg.sid,
            'error': None
        }
    
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"Failed to send WhatsApp to {to_whatsapp}: {error_msg}")
        
        return {
            'status': 'error',
            'message_sid': None,
            'error': error_msg
        }

def send_verification_whatsapp(to_whatsapp, code):
    """
    Send verification code via WhatsApp
    
    Args:
        to_whatsapp (str): Recipient WhatsApp number
        code (str): Verification code
    
    Returns:
        dict: Response with status and details
    """
    message = f"Kod pengesahan GigHala anda: {code}\n\n🔐 Jangan berkongsi kod ini dengan sesiapa. Kod akan tamat dalam 10 minit."
    return send_whatsapp(to_whatsapp, message)

def send_notification_whatsapp(to_whatsapp, subject, message_text):
    """
    Send notification via WhatsApp
    
    Args:
        to_whatsapp (str): Recipient WhatsApp number
        subject (str): Message subject/title
        message_text (str): Message content
    
    Returns:
        dict: Response with status and details
    """
    message = f"📢 {subject}\n\n{message_text}\n\n💚 GigHala Platform"
    return send_whatsapp(to_whatsapp, message)
