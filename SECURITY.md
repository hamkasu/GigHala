# Security Documentation

This document outlines the security measures implemented in GigHala and best practices for secure deployment.

## Security Improvements Implemented

### 1. Session Security
- **Secure Cookie Configuration**
  - `SESSION_COOKIE_HTTPONLY`: Prevents JavaScript access to session cookies (XSS protection)
  - `SESSION_COOKIE_SECURE`: Ensures cookies only sent over HTTPS in production
  - `SESSION_COOKIE_SAMESITE`: Set to 'Lax' to prevent CSRF attacks
  - `PERMANENT_SESSION_LIFETIME`: 24-hour session timeout

### 2. CORS (Cross-Origin Resource Sharing)
- Configurable origin allowlist via `ALLOWED_ORIGINS` environment variable
- Credentials support enabled for authenticated requests
- 1-hour cache time for preflight requests
- **Important**: Set `ALLOWED_ORIGINS` to your specific domain(s) in production

### 3. Security Headers
All responses include the following security headers:
- `X-Content-Type-Options: nosniff` - Prevents MIME-sniffing attacks
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `X-XSS-Protection: 1; mode=block` - Enables browser XSS protection
- `Strict-Transport-Security` - Enforces HTTPS connections
- `Content-Security-Policy` - Restricts resource loading to prevent XSS

### 4. Rate Limiting & Brute Force Protection
- **Login Endpoint**: 5 attempts per 15 minutes, 30-minute lockout
- **Registration Endpoint**: 10 attempts per 60 minutes, 15-minute lockout
- IP-based rate limiting with automatic lockout
- Successful authentication resets attempt counter

### 5. Input Validation & Sanitization

#### Email Validation
- Uses `email-validator` library for RFC-compliant validation
- Normalizes email addresses before storage
- Prevents invalid email formats

#### Password Strength Requirements
All passwords must contain:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

#### Username Validation
- 3-30 characters in length
- Alphanumeric characters and underscores only
- Prevents special characters that could cause injection attacks

#### Phone Number Validation
- Malaysian phone number format validation
- Supports formats: +60XXXXXXXXX or 0XXXXXXXXX

#### Text Input Sanitization
- Automatic trimming of whitespace
- Length limits on all text fields
- Prevents overly long inputs that could cause DoS

### 6. SQL Injection Prevention
- Parameterized queries using SQLAlchemy ORM
- Input sanitization before database queries
- Case-insensitive search using `ilike()` with proper parameterization
- No raw SQL queries

### 7. Authorization & Access Control
- Session-based authentication
- Endpoint-level authorization checks
- Users can only access/modify their own data
- Clients cannot apply to their own gigs
- Closed gigs reject new applications

### 8. Error Handling & Information Disclosure Prevention
- Generic error messages for authentication failures
- Database errors logged but not exposed to users
- Exception handling on all endpoints
- Prevents enumeration of valid usernames/emails

### 9. Data Validation
- Budget values validated and limited to reasonable ranges
- Dates validated (deadlines must be in future)
- Array inputs limited in size (e.g., max 20 skills)
- URL validation for video pitch links
- Boolean type coercion to prevent type confusion

## Deployment Security Checklist

### Required Actions Before Production

1. **Environment Variables**
   ```bash
   # Generate a strong secret key
   python -c "import secrets; print(secrets.token_hex(32))"

   # Set in your .env file
   SECRET_KEY=<generated-key>
   FLASK_ENV=production
   FLASK_DEBUG=False
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

2. **Database Security**
   - Use strong database credentials
   - Enable SSL for database connections
   - Restrict database access to application servers only
   - Regular backups with encryption

3. **HTTPS/TLS**
   - Use HTTPS for all production traffic
   - Obtain SSL certificate (Let's Encrypt recommended)
   - Enable HSTS header (already configured)
   - Redirect HTTP to HTTPS at web server level

4. **Web Server Configuration**
   - Use a production WSGI server (Gunicorn is already in requirements)
   - Configure reverse proxy (nginx/Apache) with rate limiting
   - Hide server version information
   - Limit request body size

5. **Monitoring & Logging**
   - Enable application logging
   - Monitor for suspicious activities
   - Set up alerts for repeated failed logins
   - Log security events (not implemented yet - see improvements)

## Known Limitations & Future Improvements

### Current Limitations

1. **In-Memory Rate Limiting**
   - Rate limit data stored in memory
   - Resets on application restart
   - Not shared across multiple server instances
   - **Recommendation**: Implement Redis-based rate limiting for production

2. **No CSRF Protection**
   - Flask-WTF not implemented
   - Relies on SameSite cookies
   - **Recommendation**: Add Flask-WTF with CSRF tokens

3. **No API Authentication**
   - Session-based auth only
   - No JWT or API key support
   - **Recommendation**: Add JWT for API clients

4. **No Security Logging**
   - Failed login attempts not permanently logged
   - No audit trail for sensitive operations
   - **Recommendation**: Implement security event logging

5. **No Two-Factor Authentication**
   - Basic password authentication only
   - **Recommendation**: Add 2FA for high-value accounts

### Recommended Future Enhancements

1. **Implement Redis for Rate Limiting**
   ```python
   # Use Flask-Limiter with Redis backend
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address
   ```

2. **Add Content Security Policy Reporting**
   ```python
   # Add CSP violation reporting endpoint
   report-uri /api/csp-report
   ```

3. **Implement Security Monitoring**
   - Failed login attempt logging
   - Suspicious activity detection
   - Security event audit log

4. **Add Request Size Limits**
   ```python
   app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
   ```

5. **Implement Account Recovery**
   - Secure password reset flow
   - Email verification for new accounts
   - Account lockout notifications

## Security Incident Response

If you discover a security vulnerability:

1. **Do Not** create a public GitHub issue
2. Email security concerns to the maintainers
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## Password Policy

Users must create passwords that meet these requirements:
- Minimum 8 characters
- Mix of uppercase and lowercase letters
- At least one number
- At least one special character (!@#$%^&*(),.?":{}|<>)

## Rate Limit Policy

### Authentication Endpoints
- **Login**: 5 attempts per 15 minutes, 30-minute lockout after exceeding
- **Registration**: 10 attempts per 60 minutes, 15-minute lockout after exceeding

### Handling Rate Limits
- HTTP 429 (Too Many Requests) returned when rate limit exceeded
- Response includes time until lockout expires
- Successful authentication resets the counter

## Security Best Practices for Developers

1. **Never log sensitive data**: Passwords, tokens, session IDs
2. **Always use parameterized queries**: Prevent SQL injection
3. **Validate all inputs**: Never trust user input
4. **Use HTTPS in production**: Protect data in transit
5. **Keep dependencies updated**: Regular security patches
6. **Principle of least privilege**: Minimal database permissions
7. **Sanitize outputs**: Prevent XSS attacks
8. **Implement proper error handling**: Don't expose system details

## Compliance Considerations

- **GDPR**: User data collection and processing policies needed
- **PCI DSS**: If handling payments, PCI compliance required
- **Data Retention**: Implement data retention and deletion policies
- **Privacy Policy**: Required for user data collection
- **Terms of Service**: Legal protection for platform

## Regular Security Maintenance

1. **Weekly**: Review application logs for anomalies
2. **Monthly**: Update dependencies to latest secure versions
3. **Quarterly**: Security audit and penetration testing
4. **Annually**: Full security review and threat modeling

## Contact

For security concerns or questions, contact the development team.

---

Last Updated: 2025-12-11
Version: 1.0
