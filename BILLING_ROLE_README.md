# Billing/Accounting Admin Role Feature

## Overview

This feature adds a dedicated billing/accounting user role to the GigHala platform, allowing you to assign specialized financial management permissions to specific admin users without granting them full platform admin access.

## Features

### 1. New Admin Roles
- **super_admin**: Full access to all admin features (existing admins)
- **billing**: Access to accounting/billing features only
- **moderator**: Reserved for future use (content moderation)

### 2. Dedicated Accounting Dashboard
Access at `/admin/accounting`

Features:
- **Overview Tab**: Real-time financial summary
- **Invoices Tab**: View and manage all platform invoices
- **Payouts Tab**: Monitor and track payout requests
- **Revenue Tab**: Revenue analytics (daily, weekly, monthly, yearly)
- **User Roles Tab**: Manage admin user roles (super_admin only)

### 3. Role-Based Access Control
- Billing admins can only access accounting/billing endpoints
- Super admins have full platform access
- Security logging for all role-based access attempts

## Installation & Setup

### Step 1: Run Database Migration

Run the migration script to add the new columns to the user table:

```bash
python3 migrate_add_admin_roles.py
```

This will:
- Add `admin_role` column to the user table
- Add `admin_permissions` column to the user table
- Automatically upgrade existing admin users to 'super_admin' role

### Step 2: Assign Billing Role to Users

1. Log in as a super admin
2. Go to Admin Dashboard → 💰 Accounting Dashboard
3. Click on the "User Roles" tab
4. Click "Edit" next to the user you want to assign the billing role to
5. Enter `billing` as the new role
6. Click OK to save

Alternatively, you can update roles directly via SQL:

```sql
-- Assign billing role to a user
UPDATE "user"
SET admin_role = 'billing',
    admin_permissions = NULL,
    is_admin = TRUE
WHERE email = 'accountant@gighala.my';
```

## API Endpoints

### Billing Admin Endpoints (Requires billing or super_admin role)

- **GET** `/api/accounting/invoices?status={all|draft|issued|paid|cancelled}`
  - Get all invoices with optional status filter

- **GET** `/api/accounting/payouts?status={all|pending|processing|completed|failed}`
  - Get all payout requests with optional status filter

- **GET** `/api/accounting/revenue-summary?period={day|week|month|year}`
  - Get revenue summary for specified period

### Role Management Endpoints (Requires super_admin role only)

- **GET** `/api/accounting/user-roles`
  - Get all admin users and their roles

- **PUT** `/api/accounting/user-roles/{user_id}`
  - Update a user's admin role
  - Body: `{"admin_role": "billing", "admin_permissions": null}`

## Usage Examples

### Creating a Billing Admin User

```python
from app import app, db, User
import bcrypt

with app.app_context():
    # Create new user
    password_hash = bcrypt.hashpw('SecurePassword123!'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    billing_user = User(
        username='accountant',
        email='accountant@gighala.my',
        password_hash=password_hash,
        full_name='Finance Manager',
        user_type='freelancer',  # Required field
        is_admin=True,
        admin_role='billing',
        admin_permissions=None  # Or JSON string with specific permissions
    )

    db.session.add(billing_user)
    db.session.commit()
    print(f"Created billing admin: {billing_user.username}")
```

### Checking User Role in Code

```python
# Check if user has billing access
if user.is_admin and user.admin_role in ['super_admin', 'billing']:
    # User has billing access
    pass

# Check if user is super admin
if user.admin_role == 'super_admin':
    # User has full admin access
    pass
```

## Security Features

1. **Audit Logging**: All billing endpoint access attempts are logged to the security log
2. **Role Validation**: Invalid roles are rejected
3. **Super Admin Protection**: Only super admins can modify user roles
4. **Session Verification**: User authentication is re-verified on every request

## Permissions System

Currently using a simple role-based system:
- `super_admin`: Permissions = `["*"]` (all permissions)
- `billing`: Permissions = `null` or specific billing permissions
- `moderator`: Permissions = `null` or specific moderation permissions

You can extend the permissions system by:
1. Defining permission constants in a new `constants.py` file
2. Implementing granular permission checks in the decorators
3. Storing permissions as JSON in the `admin_permissions` column

Example permissions structure:
```json
{
  "billing": ["view_invoices", "manage_payouts", "view_reports", "export_data"],
  "moderator": ["view_gigs", "approve_gigs", "handle_disputes"]
}
```

## Accessing the Accounting Dashboard

### For Super Admins:
1. Log in to your admin account
2. Go to Admin Dashboard
3. Click on "💰 Accounting Dashboard" button
4. Access all tabs and features

### For Billing Admins:
1. Log in to your billing admin account
2. Navigate directly to `/admin/accounting`
3. Access billing-specific features only
4. Cannot access regular admin features

## Troubleshooting

### Issue: "Forbidden - Billing/Accounting access required"
**Solution**: Ensure the user has `is_admin=True` and `admin_role` is either 'billing' or 'super_admin'

### Issue: "Only super admins can modify user roles"
**Solution**: Role management is restricted to super_admin users only. Contact a super admin to change roles.

### Issue: Migration fails with "column already exists"
**Solution**: The migration script checks for existing columns and skips them. This is normal if you've run the migration before.

### Issue: Can't access accounting dashboard
**Solution**: Check that:
1. User is logged in
2. User has `is_admin=True`
3. User has `admin_role` set to 'billing' or 'super_admin'
4. Clear browser cache and cookies

## Files Modified/Created

### Modified Files:
- `app.py`: Added User model columns, billing_admin_required decorator, accounting routes
- `templates/admin.html`: Added Accounting Dashboard link

### New Files:
- `migrate_add_admin_roles.py`: Database migration script
- `templates/accounting.html`: Accounting dashboard template
- `BILLING_ROLE_README.md`: This documentation file

## Future Enhancements

Potential improvements:
1. Granular permission system with individual permissions
2. Role-based email notifications for financial events
3. Custom financial report generation
4. Invoice and payout approval workflows
5. Multi-currency support in accounting dashboard
6. Export functionality (CSV, Excel, PDF)
7. Scheduled financial reports via email

## Support

For issues or questions:
- Check the security logs at `/admin/security-logs`
- Review the application logs for errors
- Contact the development team

---

**Version**: 1.0
**Last Updated**: 2026-01-03
**Author**: GigHala Development Team
