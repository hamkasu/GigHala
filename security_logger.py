"""
Security Event Logging Service
Provides comprehensive security event logging with SIEM integration
"""
import json
import logging
import logging.handlers
import os
import socket
from datetime import datetime
from functools import wraps
from flask import request, session
from typing import Optional, Dict, Any
import requests


class SecurityLogger:
    """
    Centralized security event logging with database audit trail and SIEM integration
    """

    def __init__(self, app=None, db=None):
        self.app = app
        self.db = db
        self.logger = None
        self.syslog_handler = None
        self.siem_webhook_url = None

        if app:
            self.init_app(app, db)

    def init_app(self, app, db):
        """Initialize security logger with Flask app"""
        self.app = app
        self.db = db

        # Setup structured logging
        self._setup_structured_logging()

        # Setup SIEM integration
        self._setup_siem_integration()

    def _setup_structured_logging(self):
        """Configure structured logging with JSON format and file rotation"""
        # Create logs directory
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Create security logger
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)

        # JSON formatter for structured logs
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )

        # Rotating file handler for security events (50MB max, keep 10 backups)
        security_file = os.path.join(log_dir, 'security.log')
        file_handler = logging.handlers.RotatingFileHandler(
            security_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)

        # Separate file for high-severity events (CRITICAL/ERROR)
        critical_file = os.path.join(log_dir, 'security_critical.log')
        critical_handler = logging.handlers.RotatingFileHandler(
            critical_file,
            maxBytes=50 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        critical_handler.setLevel(logging.WARNING)
        critical_handler.setFormatter(json_formatter)
        self.logger.addHandler(critical_handler)

        # Console handler for development
        if self.app and self.app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(json_formatter)
            self.logger.addHandler(console_handler)

    def _setup_siem_integration(self):
        """Setup SIEM integration (syslog and webhook)"""
        # Syslog integration (RFC 5424)
        syslog_host = os.environ.get('SIEM_SYSLOG_HOST')
        syslog_port = int(os.environ.get('SIEM_SYSLOG_PORT', 514))

        if syslog_host:
            try:
                self.syslog_handler = logging.handlers.SysLogHandler(
                    address=(syslog_host, syslog_port),
                    facility=logging.handlers.SysLogHandler.LOG_AUTH,
                    socktype=socket.SOCK_STREAM
                )
                # CEF format for SIEM
                syslog_formatter = logging.Formatter('%(message)s')
                self.syslog_handler.setFormatter(syslog_formatter)
                self.logger.addHandler(self.syslog_handler)
            except Exception as e:
                if self.app:
                    self.app.logger.error(f"Failed to setup syslog handler: {e}")

        # Webhook integration for SIEM
        self.siem_webhook_url = os.environ.get('SIEM_WEBHOOK_URL')

    def _get_request_context(self) -> Dict[str, Any]:
        """Extract context from current request"""
        context = {
            'ip_address': None,
            'user_agent': None,
            'request_method': None,
            'request_path': None,
            'username': None,
            'user_id': None
        }

        try:
            if request:
                # Get IP address (handle proxy headers)
                context['ip_address'] = request.headers.get('X-Forwarded-For', request.remote_addr)
                if context['ip_address'] and ',' in context['ip_address']:
                    context['ip_address'] = context['ip_address'].split(',')[0].strip()

                context['user_agent'] = request.headers.get('User-Agent', '')
                context['request_method'] = request.method
                context['request_path'] = request.path

            if session:
                context['user_id'] = session.get('user_id')
                # Try to get username from session or database
                if context['user_id']:
                    try:
                        from app import User
                        user = User.query.get(context['user_id'])
                        if user:
                            context['username'] = user.username
                    except:
                        pass

        except Exception as e:
            if self.app:
                self.app.logger.warning(f"Error extracting request context: {e}")

        return context

    def log_event(
        self,
        event_category: str,
        event_type: str,
        action: str,
        severity: str = 'medium',
        status: str = 'success',
        message: str = '',
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None
    ):
        """
        Log a security event to database and structured logs

        Args:
            event_category: Category (authentication, authorization, admin, financial, data_access, system)
            event_type: Specific event type (login_success, login_failure, permission_denied, etc.)
            action: Human-readable action description
            severity: Event severity (low, medium, high, critical)
            status: Event status (success, failure, blocked)
            message: Additional message
            resource_type: Type of resource affected (user, gig, transaction, etc.)
            resource_id: ID of affected resource
            details: Additional context as dictionary
            old_value: Previous value (for data changes)
            new_value: New value (for data changes)
            user_id: Override user ID (if not in session)
            username: Override username (if not in session)
        """
        try:
            # Get request context
            context = self._get_request_context()

            # Override with provided values
            if user_id:
                context['user_id'] = user_id
            if username:
                context['username'] = username

            # Create audit log entry in database
            from app import AuditLog
            audit_log = AuditLog(
                event_category=event_category,
                event_type=event_type,
                severity=severity,
                user_id=context['user_id'],
                username=context['username'],
                ip_address=context['ip_address'],
                user_agent=context['user_agent'],
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                status=status,
                message=message,
                details=json.dumps(details) if details else None,
                old_value=json.dumps(old_value) if old_value else None,
                new_value=json.dumps(new_value) if new_value else None,
                request_method=context['request_method'],
                request_path=context['request_path'],
                request_id=request.headers.get('X-Request-ID') if request else None
            )

            self.db.session.add(audit_log)
            self.db.session.commit()

            # Log to structured file
            log_data = {
                'event_category': event_category,
                'event_type': event_type,
                'severity': severity,
                'user_id': context['user_id'],
                'username': context['username'],
                'ip_address': context['ip_address'],
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'status': status,
                'message': message,
                'details': details
            }

            log_level = {
                'low': logging.INFO,
                'medium': logging.WARNING,
                'high': logging.ERROR,
                'critical': logging.CRITICAL
            }.get(severity, logging.INFO)

            self.logger.log(log_level, json.dumps(log_data))

            # Forward to SIEM if configured
            self._forward_to_siem(audit_log)

        except Exception as e:
            # Fallback to app logger if audit logging fails
            if self.app:
                self.app.logger.error(f"Security logging failed: {e}")
                self.app.logger.error(f"Event: {event_category}/{event_type} - {action}")

    def _forward_to_siem(self, audit_log):
        """Forward audit log to SIEM systems"""
        try:
            # Forward to syslog (CEF format)
            if self.syslog_handler:
                cef_message = audit_log.to_siem_format()
                self.logger.info(cef_message)

            # Forward to webhook
            if self.siem_webhook_url:
                try:
                    payload = audit_log.to_dict()
                    response = requests.post(
                        self.siem_webhook_url,
                        json=payload,
                        timeout=5,
                        headers={'Content-Type': 'application/json'}
                    )

                    if response.status_code == 200:
                        audit_log.siem_forwarded = True
                        audit_log.siem_forwarded_at = datetime.utcnow()
                        self.db.session.commit()
                except requests.exceptions.RequestException as e:
                    if self.app:
                        self.app.logger.warning(f"SIEM webhook failed: {e}")

        except Exception as e:
            if self.app:
                self.app.logger.warning(f"SIEM forwarding failed: {e}")

    # Convenience methods for common security events

    def log_authentication(self, event_type: str, username: str, status: str, message: str = '', **kwargs):
        """Log authentication event"""
        severity = 'high' if status == 'failure' else 'low'
        self.log_event(
            event_category='authentication',
            event_type=event_type,
            action=f"User authentication: {event_type}",
            severity=severity,
            status=status,
            message=message,
            username=username,
            **kwargs
        )

    def log_authorization(self, resource_type: str, resource_id: str, action: str, status: str, **kwargs):
        """Log authorization event"""
        severity = 'high' if status == 'blocked' else 'medium'
        self.log_event(
            event_category='authorization',
            event_type='permission_check',
            action=action,
            severity=severity,
            status=status,
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs
        )

    def log_admin_action(self, action: str, resource_type: str, resource_id: str, details: Dict = None, **kwargs):
        """Log admin operation"""
        self.log_event(
            event_category='admin',
            event_type='admin_operation',
            action=action,
            severity='high',
            status='success',
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            **kwargs
        )

    def log_financial(self, event_type: str, action: str, amount: float, resource_type: str, resource_id: str, **kwargs):
        """Log financial transaction"""
        self.log_event(
            event_category='financial',
            event_type=event_type,
            action=action,
            severity='high',
            resource_type=resource_type,
            resource_id=resource_id,
            details={'amount': amount},
            **kwargs
        )

    def log_data_access(self, resource_type: str, resource_id: str, action: str, **kwargs):
        """Log sensitive data access"""
        self.log_event(
            event_category='data_access',
            event_type='data_accessed',
            action=action,
            severity='medium',
            status='success',
            resource_type=resource_type,
            resource_id=resource_id,
            **kwargs
        )

    def log_data_change(self, resource_type: str, resource_id: str, action: str, old_value: Dict, new_value: Dict, **kwargs):
        """Log sensitive data modification"""
        self.log_event(
            event_category='data_access',
            event_type='data_modified',
            action=action,
            severity='high',
            status='success',
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            **kwargs
        )

    def log_system_event(self, event_type: str, action: str, severity: str = 'medium', **kwargs):
        """Log system event"""
        self.log_event(
            event_category='system',
            event_type=event_type,
            action=action,
            severity=severity,
            status='success',
            **kwargs
        )


    def log_security_event(self, event_category, event_type, action, severity='medium', **kwargs):
    """
    Decorator to automatically log security events for function execution

    Usage:
        @log_security_event('admin', 'user_update', 'Update user account', severity='high')
        def update_user(user_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **func_kwargs):
            from flask import current_app

            try:
                result = f(*args, **func_kwargs)
                # Log success
                security_logger = current_app.extensions.get('security_logger')
                if security_logger:
                    # Combine decorator kwargs with function kwargs if needed
                    # but usually decorator defines the event metadata
                    log_params = {
                        'event_category': event_category,
                        'event_type': event_type,
                        'action': action,
                        'severity': severity,
                        'status': 'success'
                    }
                    # Allow overriding user_id from function kwargs if present
                    if 'user_id' in func_kwargs:
                        log_params['user_id'] = func_kwargs['user_id']
                    
                    security_logger.log_event(**log_params)
                return result
            except Exception as e:
                # Log failure
                security_logger = current_app.extensions.get('security_logger')
                if security_logger:
                    log_params = {
                        'event_category': event_category,
                        'event_type': event_type,
                        'action': action,
                        'severity': 'high',
                        'status': 'failure',
                        'message': str(e)
                    }
                    if 'user_id' in func_kwargs:
                        log_params['user_id'] = func_kwargs['user_id']
                    
                    security_logger.log_event(**log_params)
                raise

        return decorated_function
    return decorator


# Global instance (will be initialized in app.py)
security_logger = None


def init_security_logger(app, db):
    """Initialize global security logger instance"""
    global security_logger
    security_logger = SecurityLogger(app, db)

    # Store in app extensions for easy access
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['security_logger'] = security_logger

    return security_logger
