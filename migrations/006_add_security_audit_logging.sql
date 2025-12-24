-- Migration: Add Security Audit Logging System
-- Description: Implements comprehensive security event logging with SIEM integration
-- Purpose: Track authentication, authorization, admin operations, financial transactions, and data changes
-- Compliance: Supports forensic analysis, audit trails, and regulatory compliance

-- =====================================================
-- Create AuditLog table for security event tracking
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,

    -- Event classification
    event_category VARCHAR(50) NOT NULL,  -- authentication, authorization, admin, financial, data_access, system
    event_type VARCHAR(100) NOT NULL,     -- login_success, login_failure, permission_denied, etc.
    severity VARCHAR(20) NOT NULL,        -- low, medium, high, critical

    -- Actor information (who performed the action)
    user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    username VARCHAR(80),
    ip_address VARCHAR(45),               -- Support IPv4 and IPv6
    user_agent TEXT,

    -- Action details (what was done)
    action VARCHAR(200) NOT NULL,
    resource_type VARCHAR(50),             -- user, gig, transaction, escrow, payout, etc.
    resource_id VARCHAR(100),              -- ID of affected resource

    -- Result and details
    status VARCHAR(20) NOT NULL,           -- success, failure, blocked
    message TEXT,
    details TEXT,                          -- JSON string with additional context

    -- Data change tracking (for sensitive operations)
    old_value TEXT,                        -- JSON string
    new_value TEXT,                        -- JSON string

    -- Request context
    request_method VARCHAR(10),            -- GET, POST, PUT, DELETE
    request_path VARCHAR(500),
    request_id VARCHAR(100),               -- Correlation ID for tracing

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- SIEM integration fields
    siem_forwarded BOOLEAN DEFAULT FALSE,
    siem_forwarded_at TIMESTAMP
);

-- =====================================================
-- Create indexes for performance and security queries
-- =====================================================

-- Index for querying by event category and severity (most common security queries)
CREATE INDEX IF NOT EXISTS idx_audit_log_category_severity ON audit_log(event_category, severity);

-- Index for user activity queries
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);

-- Index for IP address tracking (brute force detection, threat analysis)
CREATE INDEX IF NOT EXISTS idx_audit_log_ip_address ON audit_log(ip_address);

-- Index for event type (specific security event analysis)
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);

-- Index for timestamp-based queries (recent events, time-range analysis)
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

-- Composite index for resource tracking
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Index for SIEM integration queries
CREATE INDEX IF NOT EXISTS idx_audit_log_siem_forwarded ON audit_log(siem_forwarded, created_at) WHERE siem_forwarded = FALSE;

-- =====================================================
-- Add comments for documentation
-- =====================================================

COMMENT ON TABLE audit_log IS 'Security audit log for tracking all security-relevant events';
COMMENT ON COLUMN audit_log.event_category IS 'High-level category: authentication, authorization, admin, financial, data_access, system';
COMMENT ON COLUMN audit_log.event_type IS 'Specific event type: login_success, permission_denied, payout_approved, etc.';
COMMENT ON COLUMN audit_log.severity IS 'Event severity level: low, medium, high, critical';
COMMENT ON COLUMN audit_log.user_id IS 'User who performed the action (if authenticated)';
COMMENT ON COLUMN audit_log.ip_address IS 'IP address of the actor (supports IPv4 and IPv6)';
COMMENT ON COLUMN audit_log.action IS 'Human-readable description of the action';
COMMENT ON COLUMN audit_log.resource_type IS 'Type of resource affected (user, gig, transaction, etc.)';
COMMENT ON COLUMN audit_log.resource_id IS 'Identifier of the affected resource';
COMMENT ON COLUMN audit_log.status IS 'Result of the action: success, failure, blocked';
COMMENT ON COLUMN audit_log.details IS 'Additional context stored as JSON';
COMMENT ON COLUMN audit_log.old_value IS 'Previous value for data modification events (JSON)';
COMMENT ON COLUMN audit_log.new_value IS 'New value for data modification events (JSON)';
COMMENT ON COLUMN audit_log.siem_forwarded IS 'Whether this event has been forwarded to SIEM';

-- =====================================================
-- Grant permissions (adjust based on your security model)
-- =====================================================

-- Only allow INSERT and SELECT on audit_log (prevent tampering)
-- UPDATE and DELETE should be restricted to prevent audit log modification
-- REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;

-- =====================================================
-- Create view for common security queries
-- =====================================================

-- View for high-severity security events
CREATE OR REPLACE VIEW audit_log_critical_events AS
SELECT
    id,
    event_category,
    event_type,
    user_id,
    username,
    ip_address,
    action,
    status,
    message,
    created_at
FROM audit_log
WHERE severity IN ('high', 'critical')
ORDER BY created_at DESC;

-- View for failed authentication attempts
CREATE OR REPLACE VIEW audit_log_failed_auth AS
SELECT
    id,
    event_type,
    username,
    ip_address,
    message,
    created_at
FROM audit_log
WHERE event_category = 'authentication'
  AND status = 'failure'
ORDER BY created_at DESC;

-- View for admin operations
CREATE OR REPLACE VIEW audit_log_admin_actions AS
SELECT
    id,
    event_type,
    username,
    action,
    resource_type,
    resource_id,
    message,
    created_at
FROM audit_log
WHERE event_category = 'admin'
ORDER BY created_at DESC;

-- View for financial transactions
CREATE OR REPLACE VIEW audit_log_financial_events AS
SELECT
    id,
    event_type,
    username,
    action,
    resource_type,
    resource_id,
    details,
    created_at
FROM audit_log
WHERE event_category = 'financial'
ORDER BY created_at DESC;

-- =====================================================
-- Migration Complete
-- =====================================================

-- Verify the migration
SELECT 'Migration 006: Security Audit Logging - Completed Successfully' AS status;
