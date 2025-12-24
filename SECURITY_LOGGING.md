# Security Event Logging System

## Overview

This document describes the comprehensive security event logging system implemented for GigHala. The system provides complete audit trails, forensic capabilities, compliance support, and SIEM integration.

## Features

- ✅ **Comprehensive Event Tracking**: Logs authentication, authorization, admin operations, financial transactions, and data changes
- ✅ **Database Audit Trail**: Persistent storage in AuditLog table with indexed queries
- ✅ **Structured Logging**: JSON-formatted logs with rotation (50MB files, 10 backups)
- ✅ **SIEM Integration**: Syslog (RFC 5424) and webhook support with CEF format
- ✅ **Admin Dashboard**: Web API for viewing, filtering, and exporting audit logs
- ✅ **Forensic Analysis**: Detailed tracking of who did what, when, and from where
- ✅ **Compliance Support**: Meets audit trail requirements for financial regulations

## Architecture

### Components

1. **AuditLog Model** (`app.py`): Database model for storing security events
2. **SecurityLogger Service** (`security_logger.py`): Core logging service with SIEM integration
3. **Database Migrations** (`migrations/006_add_security_audit_logging.sql`): Schema setup
4. **Admin API** (`app.py`): RESTful endpoints for viewing audit logs
5. **Log Files**: Structured JSON logs in `logs/` directory

### Event Categories

- **authentication**: Login, logout, registration, password changes
- **authorization**: Permission checks, access denials
- **admin**: Admin operations (user management, broadcasting, master reset)
- **financial**: Transactions, payouts, escrow operations
- **data_access**: Sensitive data viewing and modifications
- **system**: System-level events and errors

### Severity Levels

- **low**: Routine operations (successful logins, data access)
- **medium**: Authorization checks, data modifications
- **high**: Failed authentication, admin operations, financial transactions
- **critical**: System-wide changes (master reset), security breaches

## Configuration

### Environment Variables

Configure SIEM integration using environment variables:

```bash
# Syslog integration (optional)
SIEM_SYSLOG_HOST=siem.example.com
SIEM_SYSLOG_PORT=514

# Webhook integration (optional)
SIEM_WEBHOOK_URL=https://siem.example.com/webhook/audit-logs
```

### Database Setup

Run the migration to create the AuditLog table:

```bash
# PostgreSQL
psql -U your_user -d your_database -f migrations/006_add_security_audit_logging.sql

# SQLite
sqlite3 gighala.db < migrations/006_add_security_audit_logging_sqlite.sql
```

## Usage

### Logging Security Events

The security logger is automatically initialized and available globally:

```python
from security_logger import security_logger

# Log authentication event
security_logger.log_authentication(
    event_type='login_success',
    username='john_doe',
    status='success',
    message='User logged in successfully'
)

# Log admin operation
security_logger.log_admin_action(
    action='Updated user permissions',
    resource_type='user',
    resource_id='123',
    details={'permissions': ['admin', 'moderator']}
)

# Log financial transaction
security_logger.log_financial(
    event_type='payout_approved',
    action='Admin approved payout',
    amount=1000.00,
    resource_type='payout',
    resource_id='PO-20231224-12345'
)

# Log data change
security_logger.log_data_change(
    resource_type='user',
    resource_id='123',
    action='Updated email address',
    old_value={'email': 'old@example.com'},
    new_value={'email': 'new@example.com'}
)
```

### Using Decorators

Automatically log function execution:

```python
from security_logger import log_security_event

@log_security_event('admin', 'user_deletion', 'Delete user account', severity='high')
def delete_user(user_id):
    # Function implementation
    pass
```

## API Endpoints

All audit log endpoints require admin authentication.

### Get Audit Logs (with filtering)

```http
GET /api/admin/audit-logs?page=1&per_page=50&category=authentication&severity=high
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 50)
- `category` (string): Filter by category (authentication, authorization, admin, financial, data_access, system)
- `severity` (string): Filter by severity (low, medium, high, critical)
- `user_id` (int): Filter by user ID
- `event_type` (string): Filter by specific event type
- `status` (string): Filter by status (success, failure, blocked)
- `start_date` (string): Filter from date (YYYY-MM-DD)
- `end_date` (string): Filter to date (YYYY-MM-DD)
- `search` (string): Search in username, action, or message

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "event_category": "authentication",
      "event_type": "login_failure",
      "severity": "high",
      "user_id": 123,
      "username": "john_doe",
      "ip_address": "192.168.1.100",
      "action": "Failed login attempt",
      "status": "failure",
      "message": "Invalid password",
      "created_at": "2023-12-24T10:30:00"
    }
  ],
  "total": 1500,
  "pages": 30,
  "current_page": 1
}
```

### Get Audit Log Detail

```http
GET /api/admin/audit-logs/123
```

**Response:**
```json
{
  "id": 123,
  "event_category": "financial",
  "event_type": "payout_requested",
  "severity": "high",
  "username": "freelancer_user",
  "action": "Payout request submitted",
  "details": {
    "payout_number": "PO-20231224-12345",
    "amount": 1000.00,
    "payment_method": "bank_transfer"
  },
  "created_at": "2023-12-24T10:30:00"
}
```

### Get Audit Log Statistics

```http
GET /api/admin/audit-logs/stats
```

**Response:**
```json
{
  "total_logs": 15000,
  "by_category": {
    "authentication": 5000,
    "authorization": 3000,
    "admin": 500,
    "financial": 4000,
    "data_access": 2000,
    "system": 500
  },
  "by_severity": {
    "low": 8000,
    "medium": 4000,
    "high": 2500,
    "critical": 500
  },
  "failed_auth_24h": 25,
  "permission_denied_24h": 10,
  "critical_events_7d": 15,
  "top_users_7d": [
    {"username": "admin_user", "count": 150},
    {"username": "power_user", "count": 100}
  ]
}
```

### Export Audit Logs

```http
GET /api/admin/audit-logs/export?start_date=2023-12-01&end_date=2023-12-31&category=financial
```

**Response:**
```json
{
  "export_date": "2023-12-24T10:30:00",
  "total_records": 500,
  "logs": [ /* array of audit log objects */ ]
}
```

## Log Files

### Location

- Security logs: `logs/security.log`
- Critical events: `logs/security_critical.log`

### Format

Logs are stored in JSON format for easy parsing:

```json
{"timestamp": "2023-12-24 10:30:00,123", "level": "WARNING", "message": {"event_category": "authentication", "event_type": "login_failure", "severity": "high", "username": "john_doe", "ip_address": "192.168.1.100", "action": "Failed login attempt", "status": "failure"}}
```

### Rotation

- Maximum file size: 50MB
- Backup count: 10 files
- Automatic rotation when size limit is reached

## SIEM Integration

### Syslog (RFC 5424)

Events are forwarded to syslog in CEF (Common Event Format):

```
CEF:0|GigHala|GigHala Platform|1.0|login_failure|Failed login attempt|8|suser=john_doe suid=123 src=192.168.1.100 outcome=failure
```

### Webhook

Events are sent as JSON to configured webhook URL:

```bash
curl -X POST https://siem.example.com/webhook/audit-logs \
  -H "Content-Type: application/json" \
  -d '{
    "event_category": "authentication",
    "event_type": "login_failure",
    "severity": "high",
    "username": "john_doe",
    "action": "Failed login attempt"
  }'
```

## Security Considerations

### Access Control

- Only admins can view audit logs
- The `@admin_required` decorator logs unauthorized access attempts
- Audit log table should have restricted UPDATE/DELETE permissions

### Data Retention

Configure retention policies based on compliance requirements:

```sql
-- Example: Delete logs older than 1 year
DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL '1 year';
```

### PII Protection

- Passwords are never logged (even in hashed form)
- Sensitive fields (IC numbers, bank accounts) are masked in logs
- User consent is tracked for compliance

## Events Currently Logged

### Authentication
- ✅ Login success/failure
- ✅ Logout
- ✅ Registration
- ✅ OAuth authentication

### Authorization
- ✅ Admin access denials
- ✅ Permission checks
- ✅ Unauthorized access attempts

### Admin Operations
- ✅ Master reset
- ✅ Payout approval/rejection
- ✅ User management operations

### Financial
- ✅ Payout requests
- ✅ Payout status changes
- ✅ Escrow operations (can be added)
- ✅ Transaction processing (can be added)

## Extending the System

### Adding New Event Types

1. Use the security logger in your code:

```python
security_logger.log_event(
    event_category='your_category',
    event_type='your_event_type',
    action='Description of action',
    severity='medium',
    status='success',
    resource_type='resource_type',
    resource_id='resource_id'
)
```

2. Or use convenience methods:

```python
security_logger.log_authentication(...)
security_logger.log_authorization(...)
security_logger.log_admin_action(...)
security_logger.log_financial(...)
security_logger.log_data_access(...)
security_logger.log_system_event(...)
```

### Creating Custom Views

Add SQL views for specific queries:

```sql
CREATE VIEW audit_log_suspicious_activity AS
SELECT * FROM audit_log
WHERE (event_category = 'authentication' AND status = 'failure')
   OR (event_category = 'authorization' AND status = 'blocked')
   OR severity = 'critical'
ORDER BY created_at DESC;
```

## Monitoring and Alerts

### Key Metrics to Monitor

1. Failed authentication rate (threshold: >10 per hour from same IP)
2. Permission denial rate (threshold: >5 per hour per user)
3. Critical events (threshold: any occurrence should be investigated)
4. Unusual admin activity (threshold: activity outside business hours)
5. Financial transaction anomalies (threshold: large amounts, unusual patterns)

### Setting Up Alerts

Use your SIEM system to create alerts based on:

- Multiple failed logins from same IP
- Admin operations outside business hours
- Critical severity events
- Large financial transactions
- Data export operations

## Compliance

This logging system supports compliance with:

- **PCI DSS**: Transaction logging and audit trails
- **GDPR**: Data access and modification tracking
- **SOC 2**: Security event logging and monitoring
- **ISO 27001**: Information security event management
- **Local regulations**: Malaysia PDPA 2010, Gig Workers Bill 2025

## Troubleshooting

### Logs not appearing in database

1. Check if migration was run successfully
2. Verify database permissions
3. Check application logs for errors
4. Ensure security_logger is properly initialized

### SIEM integration not working

1. Verify environment variables are set correctly
2. Check network connectivity to SIEM server
3. Review firewall rules for syslog port 514
4. Check SIEM webhook endpoint is accessible

### High disk usage from log files

1. Verify log rotation is working (check for `.1`, `.2` backup files)
2. Adjust `maxBytes` in security_logger.py if needed
3. Implement log archival process
4. Consider shorter retention periods

## Support

For questions or issues with the security logging system:

1. Check this documentation
2. Review the code in `security_logger.py` and `app.py`
3. Check application logs for error messages
4. Contact the development team

---

**Last Updated**: 2024-12-24
**Version**: 1.0
**Author**: Security Team
