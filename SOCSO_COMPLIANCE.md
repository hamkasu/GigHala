# SOCSO Compliance Implementation - Gig Workers Bill 2025

## Overview

This document describes the implementation of **SOCSO (Social Security Organization)** compliance for the GigHala platform, as mandated by the **Gig Workers Bill 2025** which enforces the **Self-Employment Social Security Scheme (SESKSO/SKSPS)** starting in 2026.

## Legal Requirements

Under the Gig Workers Bill 2025, as a platform provider, GigHala has the following mandatory obligations:

1. **Register all eligible gig workers** (Malaysian citizens/permanent residents) with SOCSO
2. **Automatically deduct SOCSO contributions** from workers' earnings (1.25% of net earnings)
3. **Remit contributions to SOCSO** on behalf of workers via the ASSIST Portal
4. **Provide workers access to contribution records** via the digital system
5. **Maintain compliance records** for audit purposes

### Contribution Details

- **Deduction Rate**: 1.25% of net earnings (after platform commission but including tips)
- **Funding**: 100% worker-funded (deducted from freelancer's payout)
- **Calculation Basis**: Net earnings after platform commission, per transaction/gig payout
- **Remittance Portal**: ASSIST Portal (https://assist.perkeso.gov.my)
- **Non-Compliance Penalty**: Fines up to RM50,000 or more

---

## Implementation Architecture

### 1. Database Schema Changes

#### New Tables

**`socso_contribution`** - Comprehensive SOCSO contribution tracking table
```sql
- id (PRIMARY KEY)
- freelancer_id (FOREIGN KEY → user.id)
- transaction_id, payout_id, gig_id (FOREIGN KEYS)
- gross_amount, platform_commission, net_earnings, socso_amount, final_payout
- contribution_month, contribution_year, contribution_type
- remitted_to_socso, remittance_date, remittance_reference, remittance_batch_id
- created_at, updated_at, notes
```

#### Updated Tables

**`user`** table - Added SOCSO consent and registration tracking:
```sql
- socso_registered (BOOLEAN)
- socso_consent (BOOLEAN) - User consent to mandatory deductions
- socso_consent_date (TIMESTAMP)
- socso_data_complete (BOOLEAN) - IC number and consent verified
```

**`transaction`** table:
```sql
- socso_amount (FLOAT) - SOCSO deducted from this transaction
```

**`payout`** table:
```sql
- socso_amount (FLOAT) - SOCSO deducted from this payout
```

**`payment_history`** table:
```sql
- socso_amount (FLOAT) - SOCSO amount for audit trail
- type enum extended to include 'socso'
```

#### Database Views

**`socso_monthly_report`** - Aggregated monthly SOCSO data for ASSIST Portal exports

#### SQL Functions

**`calculate_socso(net_earnings FLOAT)`** - Calculates 1.25% with proper rounding to sen

---

## 2. Core Logic Implementation

### SOCSO Calculation Function (`app.py:1188-1203`)

```python
def calculate_socso(net_earnings):
    """
    Calculate SOCSO contribution as per Gig Workers Bill 2025
    SOCSO Rate: 1.25% of net earnings (after platform commission)
    """
    if net_earnings <= 0:
        return 0.0
    return round(net_earnings * 0.0125, 2)  # 1.25%
```

### SOCSO Contribution Record Creation (`app.py:1205-1248`)

```python
def create_socso_contribution(freelancer_id, gross_amount, platform_commission,
                               net_earnings, contribution_type='escrow_release',
                               gig_id=None, transaction_id=None, payout_id=None):
    """
    Create a SOCSO contribution record for compliance tracking
    Returns: SocsoContribution object
    """
```

### SOCSO Compliance Validation (`app.py:1250-1277`)

```python
def check_socso_compliance(user):
    """
    Check if user is compliant with SOCSO requirements
    Returns: (is_compliant: bool, reason: str)

    Validates:
    - User is a freelancer
    - IC number is provided
    - SOCSO consent has been given
    """
```

---

## 3. Payment Flow with SOCSO Deduction

### Workflow 1: Escrow Release (`app.py:5209-5320`)

When a client releases payment after work completion:

```
1. Client pays MYR 1,000 for a gig
2. Platform commission calculated (tiered: 5-15%)
   Example: MYR 100 commission (10%)
3. Net earnings = MYR 900 (basis for SOCSO)
4. SOCSO deducted = MYR 900 × 1.25% = MYR 11.25
5. Final payout to freelancer = MYR 888.75
```

**Code Flow:**
```python
# Calculate SOCSO from net amount after commission
socso_amount = calculate_socso(escrow.net_amount)
final_payout_amount = round(escrow.net_amount - socso_amount, 2)

# Create SOCSO contribution record
create_socso_contribution(
    freelancer_id=gig.freelancer_id,
    gross_amount=escrow.amount,
    platform_commission=escrow.platform_fee,
    net_earnings=escrow.net_amount,
    contribution_type='escrow_release',
    gig_id=gig_id,
    transaction_id=transaction.id
)

# Credit freelancer wallet with final amount
freelancer_wallet.balance += final_payout_amount
```

### Workflow 2: Payout Request (`app.py:7292-7412`)

When a freelancer requests to withdraw funds:

```
1. Freelancer requests payout of MYR 500
2. SOCSO compliance check (IC number + consent required)
3. SOCSO deducted = MYR 500 × 1.25% = MYR 6.25
4. Platform fee = MYR 500 × 2% = MYR 10.00
5. Final bank transfer = MYR 483.75
```

**Breakdown Returned to User:**
```json
{
  "gross_amount": 500.00,
  "platform_fee": 10.00,
  "socso_contribution": 6.25,
  "final_payout": 483.75
}
```

---

## 4. User Registration Flow

### Registration with SOCSO Consent (`app.py:3291-3387`)

**Required Fields for Freelancers:**
- IC/Passport number (6-20 alphanumeric characters)
- Privacy consent (PDPA 2010)
- **SOCSO consent** (mandatory for freelancers)

**Validation:**
```python
# SOCSO consent required for freelancers
if user_type in ['freelancer', 'both']:
    if not socso_consent:
        return error: 'You must agree to mandatory SOCSO deductions (1.25%)
                      as required by the Gig Workers Bill 2025'
```

**User Creation:**
```python
new_user = User(
    username=username,
    email=email,
    ic_number=ic_number_clean,
    socso_consent=socso_consent,
    socso_consent_date=datetime.utcnow(),
    socso_data_complete=True  # If IC and consent both provided
)
```

---

## 5. API Endpoints

### Freelancer Endpoints

#### GET `/api/billing/socso-contributions`
**Description**: Get freelancer's SOCSO contribution history

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 50)
- `year` (int): Filter by year
- `month` (int): Filter by month (requires year)

**Response:**
```json
{
  "contributions": [
    {
      "id": 123,
      "gig_id": 45,
      "gross_amount": 1000.00,
      "platform_commission": 100.00,
      "net_earnings": 900.00,
      "socso_amount": 11.25,
      "final_payout": 888.75,
      "contribution_month": "2026-01",
      "contribution_year": 2026,
      "contribution_type": "escrow_release",
      "remitted_to_socso": true,
      "remittance_date": "2026-02-05T10:00:00Z",
      "created_at": "2026-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "total": 24,
    "pages": 1,
    "current_page": 1,
    "per_page": 50
  },
  "summary": {
    "total_socso_contributed": 135.50,
    "total_net_earnings": 10840.00,
    "total_final_payout": 10704.50,
    "transaction_count": 24
  },
  "user_info": {
    "socso_consent": true,
    "socso_consent_date": "2025-12-01T09:00:00Z",
    "ic_number": "920101125678"
  }
}
```

---

### Admin Endpoints

#### GET `/api/admin/socso/monthly-report`
**Description**: Generate monthly SOCSO report for ASSIST Portal bulk upload

**Query Parameters:**
- `year` (int): Report year (default: current year)
- `month` (int, optional): Specific month (1-12)
- `format` (string): Response format - `json` or `csv` (default: json)

**JSON Response:**
```json
{
  "report": [
    {
      "contribution_month": "2026-01",
      "contribution_year": 2026,
      "freelancer_id": 42,
      "full_name": "Ahmad Bin Abdullah",
      "ic_number": "920101125678",
      "email": "ahmad@example.com",
      "phone": "+60123456789",
      "transaction_count": 5,
      "total_net_earnings": 4500.00,
      "total_socso_amount": 56.25,
      "total_final_payout": 4443.75,
      "all_remitted": true,
      "last_remittance_date": "2026-02-05T10:00:00Z"
    }
  ],
  "totals": {
    "total_freelancers": 150,
    "total_transactions": 450,
    "total_net_earnings": 675000.00,
    "total_socso_amount": 8437.50,
    "total_final_payout": 666562.50
  },
  "filters": {
    "year": 2026,
    "month": 1
  }
}
```

**CSV Export** (`?format=csv`):
Downloads a CSV file formatted for ASSIST Portal bulk upload with columns:
- Month, Year, IC Number, Full Name, Email, Phone
- Transaction Count, Total Net Earnings (MYR), SOCSO Contribution (MYR)
- Final Payout (MYR), Remitted to SOCSO

**Filename**: `socso_report_2026_01.csv`

---

#### POST `/api/admin/socso/mark-remitted`
**Description**: Mark SOCSO contributions as remitted to ASSIST Portal

**Request Body:**
```json
{
  "contribution_ids": [123, 124, 125],
  "remittance_reference": "PERKESO-2026-01-001",
  "remittance_batch_id": "BATCH-202601"
}
```

**Response:**
```json
{
  "message": "Marked 3 contributions as remitted",
  "updated_count": 3
}
```

---

#### GET `/api/admin/stats`
**Description**: Admin dashboard statistics (now includes SOCSO data)

**Additional Response Section:**
```json
{
  "socso": {
    "total_collected": 125000.50,
    "total_remitted": 100000.00,
    "pending_remittance": 25000.50,
    "current_month_collection": 8437.50,
    "registered_freelancers": 1250,
    "compliance_rate": 95.45
  }
}
```

---

## 6. Compliance Safeguards

### Payout Blocking

Freelancers **cannot request payouts** without:
1. Valid IC/Passport number
2. SOCSO consent

**Error Response:**
```json
{
  "error": "SOCSO compliance required",
  "reason": "IC number is required for SOCSO registration",
  "socso_required": true
}
```

### Legal Disclaimers

Displayed during:
- User registration (freelancers)
- First payout request
- SOCSO contribution history page

**Sample Text:**
```
"Mandatory SOCSO contribution under Gig Workers Bill 2025
for your social security protection. You consent to automatic
deduction of 1.25% from your net earnings."
```

---

## 7. Monthly SOCSO Remittance Workflow (Admin)

### Step 1: Generate Monthly Report
```bash
GET /api/admin/socso/monthly-report?year=2026&month=1&format=csv
```

### Step 2: Upload to ASSIST Portal
1. Login to https://assist.perkeso.gov.my
2. Navigate to "Bulk Contribution Upload"
3. Upload the CSV file
4. Obtain remittance reference number

### Step 3: Mark as Remitted
```bash
POST /api/admin/socso/mark-remitted
{
  "contribution_ids": [all_ids_for_month],
  "remittance_reference": "PERKESO-2026-01-001",
  "remittance_batch_id": "BATCH-202601"
}
```

---

## 8. Testing & Validation

### Manual Calculation Test

**Scenario**: MYR 1,000 gig with 10% commission

```
Gross Amount:        MYR 1,000.00
Platform Commission: MYR   100.00 (10%)
─────────────────────────────────
Net Earnings:        MYR   900.00
SOCSO (1.25%):       MYR    11.25
─────────────────────────────────
Final Payout:        MYR   888.75
```

**Verification:**
```python
assert calculate_socso(900.00) == 11.25
assert round(900.00 - 11.25, 2) == 888.75
```

### Rounding Validation

SOCSO amounts are rounded to 2 decimal places (Malaysian Ringgit sen):

```python
# Edge case tests
assert calculate_socso(800.00) == 10.00   # 800 × 1.25% = 10.00
assert calculate_socso(833.33) == 10.42   # 833.33 × 1.25% = 10.4166... → 10.42
assert calculate_socso(100.00) == 1.25    # 100 × 1.25% = 1.25
assert calculate_socso(50.00) == 0.63     # 50 × 1.25% = 0.625 → 0.63 (banker's rounding)
```

---

## 9. Migration Instructions

### Running the Migration

```bash
# Connect to PostgreSQL database
psql -U username -d gighala

# Run the migration
\i migrations/005_add_socso_compliance.sql
```

### Verification Queries

```sql
-- Check if SOCSO tables and columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'socso_contribution';

-- Verify SOCSO function exists
SELECT calculate_socso(1000.00);  -- Should return 12.50

-- Check view
SELECT * FROM socso_monthly_report LIMIT 5;
```

---

## 10. Compliance Checklist

- [x] Database schema includes SOCSO contribution tracking
- [x] User registration requires SOCSO consent for freelancers
- [x] IC/Passport number mandatory and validated
- [x] SOCSO automatically calculated at 1.25% of net earnings
- [x] SOCSO deducted on escrow release
- [x] SOCSO deducted on payout requests
- [x] Freelancers can view SOCSO contribution history
- [x] Admin can generate monthly SOCSO reports
- [x] CSV export compatible with ASSIST Portal
- [x] Admin can mark contributions as remitted
- [x] Payout requests blocked without SOCSO compliance
- [x] Proper rounding to 2 decimal places (sen)
- [x] Audit trail in payment history
- [x] SOCSO statistics in admin dashboard

---

## 11. Future Enhancements

1. **ASSIST Portal API Integration** (when available)
   - Automatic remittance via API
   - Real-time contribution status sync

2. **Freelancer Notifications**
   - Monthly SOCSO contribution summary emails
   - SOCSO registration confirmation emails

3. **Analytics Dashboard**
   - SOCSO trends over time
   - Compliance rate tracking
   - Projected monthly remittances

4. **Automated Remittance Scheduling**
   - Scheduled monthly report generation
   - Auto-upload to ASSIST Portal (API)

---

## 12. Support & References

### Official SOCSO Resources
- ASSIST Portal: https://assist.perkeso.gov.my
- SESKSO Information: https://www.perkeso.gov.my/en/self-employment-social-security-scheme.html
- Gig Workers Bill 2025: [Parliament Malaysia Official Gazette]

### Technical Support
- Platform Admin: admin@gighala.my
- SOCSO Compliance Officer: compliance@gighala.my

### Code References
- Migration: `/migrations/005_add_socso_compliance.sql`
- Models: `/app.py:1971-2032` (SocsoContribution model)
- Utility Functions: `/app.py:1188-1277`
- API Endpoints: `/app.py:7493-7781`

---

**Last Updated**: 2025-12-20
**Implementation Version**: 1.0
**Compliance Deadline**: January 1, 2026
