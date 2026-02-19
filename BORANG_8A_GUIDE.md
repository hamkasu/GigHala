# Borang 8A Form Generator - Implementation Guide

## Overview

The Borang 8A Form Generator is a comprehensive SOCSO compliance feature that enables GigHala to generate official monthly SOCSO contribution reports (Borang 8A) for submission to PERKESO's ASSIST Portal. This is a mandatory requirement under the Gig Workers Bill 2025.

**Submission Deadline**: 15th of each month for the previous month's contributions

---

## Features

### 1. **Automated Form Generation**
- Generates official SOCSO Borang 8A monthly reports
- Supports multiple export formats:
  - **HTML**: Printable form for review and record-keeping
  - **TXT**: Text file for ASSIST Portal bulk upload
  - **JSON**: Data preview and integration

### 2. **Employer Configuration**
- Stores employer SOCSO settings in the database
- Required fields:
  - Employer Code (from PERKESO registration)
  - SSM/MyCoID Number
  - Company Name
  - Company Address
  - Contact Phone
  - Contact Email

### 3. **Employee Status Tracking**
- Automatically identifies employee status:
  - **B (Baru/New)**: First-time contribution in the selected month
  - **H (Berhenti/Terminated)**: Future enhancement for terminated employees
  - **Blank**: Existing employees

### 4. **Monthly Reporting**
- Groups contributions by month and employee
- Calculates monthly wages and SOCSO contributions
- Provides summary statistics:
  - Total employees
  - New employees
  - Total monthly wages
  - Total SOCSO contributions

---

## Implementation Details

### Database Changes

**Migration**: `014_add_employer_socso_settings.sql`

New settings added to `site_settings` table:
```sql
- socso_employer_code
- socso_ssm_number
- socso_company_name
- socso_company_address
- socso_company_phone
- socso_company_email
- socso_submission_reminder_enabled
- socso_last_submission_date
```

### API Endpoint

**Route**: `GET /api/admin/socso/borang-8a`

**Query Parameters**:
- `year` (int): Contribution year (default: current year)
- `month` (int): Contribution month 1-12 (default: previous month)
- `format` (string): 'json', 'txt', or 'html' (default: 'json')

**Example Requests**:
```bash
# Get JSON data
GET /api/admin/socso/borang-8a?year=2026&month=1&format=json

# View printable form
GET /api/admin/socso/borang-8a?year=2026&month=1&format=html

# Download text file for ASSIST Portal
GET /api/admin/socso/borang-8a?year=2026&month=1&format=txt
```

**Response Structure** (JSON format):
```json
{
  "form_info": {
    "form_name": "Borang 8A - Senarai Pekerja dan Caruman Bulanan",
    "form_name_en": "Form 8A - Monthly List of Employees and Contributions",
    "submission_deadline": "15th of February 2026"
  },
  "employer": {
    "employer_code": "E12345",
    "ssm_number": "201501012345",
    "company_name": "GigHala Sdn Bhd",
    "company_address": "...",
    "company_phone": "+60123456789",
    "company_email": "compliance@gighala.my"
  },
  "period": {
    "month": 1,
    "year": 2026,
    "month_name": "January",
    "contribution_month": "2026-01"
  },
  "employees": [
    {
      "ic_number": "920101125678",
      "socso_number": "S12345678",
      "full_name": "Ahmad Bin Abdullah",
      "employment_date": "2025-12-01",
      "monthly_wages": 4500.00,
      "contribution_amount": 56.25,
      "employment_status": "B",
      "transaction_count": 5
    }
  ],
  "summary": {
    "total_employees": 150,
    "total_wages": 675000.00,
    "total_contribution": 8437.50,
    "new_employees": 12,
    "terminated_employees": 0
  },
  "generated_at": "2026-02-01T10:00:00Z",
  "generated_by": "admin"
}
```

### Text File Format

The text file export uses a pipe-delimited format suitable for PERKESO ASSIST Portal:

```
# Borang 8A - GigHala Sdn Bhd
# Period: January 2026
# Employer Code: E12345
# SSM Number: 201501012345
#
E12345         |201501012345        |920101125678        |Ahmad Bin Abdullah                                   |2026-01|     56.25|     4500.00|2025-12-01|B
```

**Field Structure**:
1. Employer Code (15 chars, left-aligned)
2. SSM Number (20 chars, left-aligned)
3. IC Number (20 chars, left-aligned)
4. Employee Name (60 chars, left-aligned)
5. Contribution Month (7 chars, YYYY-MM)
6. Contribution Amount (10 chars, right-aligned, 2 decimals)
7. Monthly Wages (12 chars, right-aligned, 2 decimals)
8. Employment Date (10 chars, YYYY-MM-DD)
9. Employment Status (1 char: B/H/blank)

---

## Admin Panel UI

### Location
Admin Panel → SOCSO Compliance Tab → Borang 8A Generator Section

### User Interface Components

1. **Deadline Warning Banner**
   - Yellow warning highlighting the 15th monthly deadline
   - Automatically calculates next submission deadline

2. **Settings Validation**
   - Checks for required employer settings
   - Displays error if Employer Code or SSM Number is missing
   - Links to settings page for configuration

3. **Period Selection**
   - Year dropdown (current year and 3 previous years)
   - Month dropdown (January-December)
   - Defaults to previous month

4. **Action Buttons**
   - **View Printable Form**: Opens HTML version in new tab
   - **Download TXT File**: Downloads text file for ASSIST Portal
   - **Preview Data**: Shows inline preview of the report data

5. **Data Preview Panel**
   - Displays employer information
   - Shows summary statistics
   - Lists all employees with wages and contributions
   - Highlights new employee status

6. **Submission Instructions**
   - Step-by-step guide for ASSIST Portal submission
   - Direct link to ASSIST Portal login

---

## Usage Workflow

### Monthly Submission Process

**Step 1: Configure Employer Settings** (One-time)
1. Navigate to Settings tab in Admin Panel
2. Add SOCSO Employer Code (from PERKESO registration)
3. Add SSM/MyCoID Number
4. Update company contact details
5. Save settings

**Step 2: Generate Borang 8A** (Monthly - by 15th)
1. Navigate to SOCSO Compliance tab
2. Scroll to "Generate Borang 8A" section
3. Select the previous month and year
4. Click "Preview Data" to review
5. Click "View Printable Form" for record-keeping
6. Click "Download TXT File" for ASSIST Portal upload

**Step 3: Submit to ASSIST Portal**
1. Login to [ASSIST Portal](https://assist.perkeso.gov.my/employer/login)
2. Navigate to "Bulk Contribution Upload" or "Borang 8A Submission"
3. Upload the downloaded TXT file
4. Review and confirm submission
5. Save the submission reference number
6. Keep the printable form for records

---

## Code References

### Backend
- **API Endpoint**: `app.py:11773-11993` (`admin_generate_borang_8a()`)
- **Helper Functions**:
  - `get_site_setting()`: `app.py:2446-2449`
  - `set_site_setting()`: `app.py:2451-2464`
- **SOCSO Models**: `app.py:1971-2032` (`SocsoContribution`)

### Frontend
- **HTML Template**: `templates/borang_8a_print.html`
- **Admin UI**: `templates/admin.html:936-1018` (Borang 8A section)
- **JavaScript Functions**: `templates/admin.html:2097-2272`
  - `initBorang8AYearSelector()`
  - `viewBorang8A()`
  - `downloadBorang8ATXT()`
  - `previewBorang8AData()`

### Database
- **Migrations**:
  - `migrations/014_add_employer_socso_settings.sql` (PostgreSQL)
  - `migrations/014_add_employer_socso_settings_sqlite.sql` (SQLite)

---

## Validation and Error Handling

### Required Settings Validation
The system validates that Employer Code and SSM Number are configured before generating Borang 8A:

```json
{
  "error": "Employer SOCSO settings incomplete",
  "message": "Please configure SOCSO Employer Code and SSM Number in settings",
  "missing": {
    "employer_code": true,
    "ssm_number": false
  }
}
```

### No Data Found
If no contributions exist for the selected period:

```json
{
  "error": "No SOCSO contributions found",
  "message": "No contributions found for 2026-01",
  "year": 2026,
  "month": 1
}
```

---

## Testing

### Manual Testing Checklist

1. **Settings Configuration**
   - [ ] Add SOCSO Employer Code in settings
   - [ ] Add SSM Number in settings
   - [ ] Verify settings are saved correctly

2. **Form Generation**
   - [ ] Select previous month
   - [ ] Click "Preview Data"
   - [ ] Verify employee list is correct
   - [ ] Verify calculations (wages and contributions)
   - [ ] Verify new employee status (B) appears correctly

3. **Export Formats**
   - [ ] View printable HTML form
   - [ ] Verify form displays all employer information
   - [ ] Verify employee table is complete
   - [ ] Download TXT file
   - [ ] Open TXT file and verify format
   - [ ] Check pipe-delimited structure

4. **Error Scenarios**
   - [ ] Try generating without employer settings
   - [ ] Try generating for a month with no contributions
   - [ ] Verify appropriate error messages display

---

## Future Enhancements

1. **ASSIST Portal API Integration** (when available)
   - Direct API submission to ASSIST Portal
   - Automatic submission confirmation
   - Real-time status tracking

2. **Automated Reminders**
   - Email notifications on 1st of each month
   - Dashboard alerts for pending submissions
   - SMS reminders for admins

3. **Employee Termination Tracking**
   - Add termination date field to user model
   - Automatically mark terminated employees with "H" status
   - Track termination reasons for compliance

4. **Submission History**
   - Log all Borang 8A generations
   - Track submission dates and reference numbers
   - Audit trail for compliance verification

5. **Validation Enhancements**
   - Pre-submission data validation
   - IC number format verification
   - Duplicate employee detection

6. **Multi-format Support**
   - PDF export with official PERKESO formatting
   - Excel export for record-keeping
   - Email delivery to compliance officer

---

## Compliance Notes

### Legal Requirements
- **Submission Deadline**: 15th of each month (or previous working day if 15th is a holiday)
- **Late Payment Penalty**: 6% per annum for each day of late payment
- **Required Information**: All employees with SOCSO contributions must be included
- **Record Retention**: Keep submission records for audit purposes

### SOCSO Contribution Rate
- **Rate**: 1.25% of net earnings (after platform commission)
- **Basis**: Net earnings per gig/transaction
- **Funding**: 100% worker-funded (deducted from freelancer payout)

### Contact Information
- **PERKESO Hotline**: 1-300-22-8000 (Mon-Fri, 8:00 AM - 5:00 PM)
- **ASSIST Portal**: https://assist.perkeso.gov.my/employer/login
- **SESKSO Information**: https://www.perkeso.gov.my/en/self-employment-social-security-scheme.html

---

## Support

For technical issues or questions regarding Borang 8A generation:
- **Platform Admin**: admin@gighala.my
- **SOCSO Compliance Officer**: compliance@gighala.my
- **Technical Support**: Create an issue in the repository

---

**Last Updated**: 2026-01-03
**Implementation Version**: 1.0
**Compliance Requirement**: Gig Workers Bill 2025
