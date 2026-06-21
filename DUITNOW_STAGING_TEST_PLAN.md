# DuitNow Payment System - Comprehensive Staging Test Plan

## Test Environment Setup

**Prerequisites:**
- Staging database with test data (users, gigs, escrows)
- Maybank test account credentials (512345678901)
- Admin user created for testing
- Client and freelancer test users
- Test gigs created with assigned freelancers

---

## 1. CLIENT PAYMENT FORM TESTING

### 1.1 Payment Method Selection

**Test Case 1.1.1: DuitNow Option Appears**
- **Steps:**
  1. Log in as client user
  2. Navigate to Escrow page
  3. Click "Fund Escrow" on a pending escrow
  4. Observe payment method options
- **Expected:**
  - "DuitNow QR Code" option visible
  - Icon is 🏦
  - Description: "Scan with your banking app - fastest payment method"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.1.2: DuitNow Selection Visual Feedback**
- **Steps:**
  1. Display fund escrow modal
  2. Click on DuitNow payment method
  3. Observe styling
- **Expected:**
  - DuitNow option highlighted (green border)
  - Background changes to light green (#F0FDF4)
  - Other options become unselected
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.1.3: Other Payment Methods Still Available**
- **Steps:**
  1. View payment method options
  2. Count available options
- **Expected:**
  - At least 4 options available: DuitNow, FPX, Card/Google Pay, Manual Bank Transfer
  - All clickable and selectable
- **Result:** ☐ PASS / ☐ FAIL

---

### 1.2 QR Code Generation & Display

**Test Case 1.2.1: QR Code Generates Successfully**
- **Steps:**
  1. Select DuitNow payment method
  2. Click "Proceed to Payment"
  3. Wait for response
  4. Check for QR code display
- **Expected:**
  - No errors in console
  - QR code modal appears
  - QR code image displays (visible square pattern)
  - Image size ~280px x 280px
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.2.2: QR Code is Scannable**
- **Steps:**
  1. Generate QR code (as above)
  2. Use phone camera/QR scanner to scan displayed QR
- **Expected:**
  - QR code successfully scans
  - Decoded content includes:
    - Bank account (0121104512345678901)
    - Amount (RM value)
    - Reference (ESC-{gig_id}-{random})
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.2.3: QR Code Image Quality**
- **Steps:**
  1. Generate QR code
  2. Right-click → Inspect element or Save image
  3. Check image properties
- **Expected:**
  - Valid PNG image (header: 89 50 4E 47)
  - Size > 500 bytes
  - Base64 encoded data URI format
  - Renders clearly without pixelation
- **Result:** ☐ PASS / ☐ FAIL

---

### 1.3 Payment Details Display

**Test Case 1.3.1: All Payment Details Visible**
- **Steps:**
  1. Generate DuitNow QR code
  2. Check details section below QR
- **Expected:**
  - Bank Name: "Maybank"
  - Account: "512345678901"
  - Recipient: "GigHala Sdn Bhd"
  - Amount: RM {amount from gig}
  - Reference: "ESC-{gig_id}-{random8chars}"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.3.2: Reference Format Correct**
- **Steps:**
  1. Generate multiple DuitNow payments
  2. Note the reference format for each
- **Expected:**
  - Format matches: ESC-{gig_id}-{8_char_hex}
  - References are unique per payment
  - No duplicate references
  - Example: ESC-123-ABC456F7
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.3.3: Amount Formatting**
- **Steps:**
  1. Create escrow with various amounts
  2. Check displayed amounts: RM 500, RM 1,500.50, RM 10,000
- **Expected:**
  - Amounts formatted to 2 decimal places
  - Currency symbol "RM" displayed
  - Thousand separators correct
  - Primary color highlighting
- **Result:** ☐ PASS / ☐ FAIL

---

### 1.4 Payment Instructions

**Test Case 1.4.1: Clear Step-by-Step Instructions**
- **Steps:**
  1. View DuitNow payment modal
  2. Scroll to instructions section
  3. Read all steps
- **Expected:**
  - "How to Pay with DuitNow" section visible
  - 5 clear numbered steps:
    1. Open your banking app
    2. Look for "Scan QR" or "DuitNow"
    3. Point camera at QR code
    4. Amount and reference auto-fill
    5. Enter PIN to confirm
  - Instructions in light green box
  - Text clearly readable
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.4.2: Instructions Visible on Mobile**
- **Steps:**
  1. Test on mobile device (iPhone/Android)
  2. Generate DuitNow payment
  3. Check instructions display
- **Expected:**
  - All text readable (font size ≥13px)
  - Instructions don't overflow
  - Proper spacing between steps
  - QR code still scannable
- **Result:** ☐ PASS / ☐ FAIL

---

### 1.5 Bank Reference Submission

**Test Case 1.5.1: Reference Input Field Present**
- **Steps:**
  1. View DuitNow payment modal
  2. Look for reference input section
- **Expected:**
  - Input field labeled: "After Payment: Enter Your Bank Reference"
  - Placeholder text: "e.g., DEC202512345678"
  - Help text: "Find in app under 'Transaction Details'"
  - Field in yellow box (background: #FFFBEB)
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.5.2: Submit Valid Reference**
- **Steps:**
  1. Enter bank reference: "DEC2025123456"
  2. Click "Confirm Payment Sent"
  3. Wait for response
- **Expected:**
  - No validation error
  - Success message: "Bank reference submitted..."
  - Modal closes
  - Alert: "Admin will verify within 24 hours"
  - Escrow status updates in background
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.5.3: Empty Reference Rejected**
- **Steps:**
  1. Leave reference field empty
  2. Click "Confirm Payment Sent"
- **Expected:**
  - Error message: "Please enter your bank reference"
  - Modal stays open
  - Field focused
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 1.5.4: Reference Stored in Database**
- **Steps:**
  1. Submit bank reference (e.g., "TEST2025ABC123")
  2. Check database directly:
     `SELECT payment_confirmation_ref FROM escrow WHERE id={escrow_id}`
- **Expected:**
  - Field contains: "TEST2025ABC123"
  - Reference matches what client entered
  - Timestamp is recent
- **Result:** ☐ PASS / ☐ FAIL

---

## 2. DATABASE INTEGRITY TESTING

### 2.1 Escrow Model Fields

**Test Case 2.1.1: All DuitNow Fields Created**
- **Steps:**
  1. Check database schema:
     `DESCRIBE escrow;`
  2. Verify columns exist
- **Expected:**
  - `payment_method` VARCHAR(30)
  - `qr_code_image` LONGBLOB
  - `qr_code_string` TEXT
  - `duitnow_reference` VARCHAR(50)
  - `payment_confirmation_ref` VARCHAR(100)
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 2.1.2: Default Values Correct**
- **Steps:**
  1. Create new escrow without DuitNow fields
  2. Check default values
- **Expected:**
  - payment_method defaults to 'bank_transfer'
  - Other fields default to NULL
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 2.1.3: Indexes Created**
- **Steps:**
  1. Check database indexes:
     `SHOW INDEX FROM escrow;`
- **Expected:**
  - idx_escrow_duitnow_reference exists
  - idx_escrow_payment_method exists
  - Both point to correct columns
- **Result:** ☐ PASS / ☐ FAIL

---

### 2.2 Data Consistency

**Test Case 2.2.1: No Data Loss During Migration**
- **Steps:**
  1. Count existing escrows before migration
  2. Run migration
  3. Count escrows after migration
- **Expected:**
  - Row count unchanged
  - All existing data intact
  - No errors in migration log
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 2.2.2: QR Code Storage**
- **Steps:**
  1. Generate DuitNow payment
  2. Query database for QR code:
     `SELECT LENGTH(qr_code_image) FROM escrow WHERE id={id}`
- **Expected:**
  - qr_code_image NOT NULL
  - Size > 500 bytes (valid PNG)
  - Binary data valid (PNG header: 89504E47)
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 2.2.3: Reference Uniqueness**
- **Steps:**
  1. Create 10 DuitNow payments
  2. Query database:
     `SELECT duitnow_reference FROM escrow WHERE payment_method='duitnow';`
  3. Check for duplicates
- **Expected:**
  - All 10 references unique
  - No NULL values
  - Format matches: ESC-{gig_id}-{8char}
- **Result:** ☐ PASS / ☐ FAIL

---

## 3. API ENDPOINT TESTING

### 3.1 Client Endpoints

**Test Case 3.1.1: POST /api/escrow/<gig_id>/pay with DuitNow**
- **Steps:**
  1. Make request with auth cookie:
     ```
     POST /api/escrow/123/pay
     {"payment_method": "duitnow"}
     ```
  2. Check response
- **Expected:**
  - Status: 200
  - Response includes:
    - success: true
    - payment_method: "duitnow"
    - qr_code: (base64 PNG)
    - payment_details object with all fields
    - escrow object
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.1.2: Response QR Code Valid**
- **Steps:**
  1. Extract qr_code from response
  2. Verify base64 format
  3. Decode and check size
- **Expected:**
  - Starts with "data:image/png;base64,"
  - Base64 string is valid
  - Decodes to valid PNG image
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.1.3: Unauthorized Access Denied**
- **Steps:**
  1. Make request without auth
  2. Make request as different user (not client)
- **Expected:**
  - Status: 403
  - Error: "Only the client can fund the escrow"
  - Status: 403
  - Error: "Only the client can fund the escrow"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.1.4: Invalid Amount Rejected**
- **Steps:**
  1. Request with amount: 0
  2. Request with amount: -1000
- **Expected:**
  - Status: 400
  - Error: "Invalid amount"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.1.5: POST /api/escrow/<gig_id>/confirm-duitnow**
- **Steps:**
  1. Make request:
     ```
     POST /api/escrow/123/confirm-duitnow
     {"bank_reference": "TEST2025ABC"}
     ```
  2. Check response
- **Expected:**
  - Status: 200
  - Message: "Bank reference submitted..."
  - escrow.payment_confirmation_ref updated
- **Result:** ☐ PASS / ☐ FAIL

---

### 3.2 Admin Endpoints

**Test Case 3.2.1: GET /api/admin/duitnow/pending-confirmations**
- **Steps:**
  1. Create 3 pending DuitNow payments
  2. Make request as admin:
     ```
     GET /api/admin/duitnow/pending-confirmations
     ```
  3. Check response
- **Expected:**
  - Status: 200
  - confirmations array with 3 items
  - stats object with:
    - pending: 3
    - total_amount: (sum of amounts)
    - confirmed_today: (count)
  - Each item has: escrow_id, gig_title, client_name, amount, etc.
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.2.2: Non-Admin Denied**
- **Steps:**
  1. Request as regular user
- **Expected:**
  - Status: 403
  - Error: "Access denied"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.2.3: POST /api/admin/duitnow/<escrow_id>/confirm**
- **Steps:**
  1. Get pending escrow ID
  2. Make request as admin:
     ```
     POST /api/admin/duitnow/123/confirm
     {}
     ```
  3. Check response
- **Expected:**
  - Status: 200
  - Message: "DuitNow payment confirmed and escrow funded"
  - Escrow status changes from "pending" to "funded"
  - funded_at timestamp set
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.2.4: Confirm Updates Wallet**
- **Steps:**
  1. Note client wallet held_balance before
  2. Confirm payment
  3. Query wallet after:
     `SELECT held_balance FROM wallet WHERE user_id={client_id}`
- **Expected:**
  - held_balance increased by escrow amount
  - Amount stored with 2 decimal precision
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 3.2.5: POST /api/admin/duitnow/<escrow_id>/reject**
- **Steps:**
  1. Make request as admin:
     ```
     POST /api/admin/duitnow/123/reject
     {"reason": "Reference does not match"}
     ```
  2. Check response
- **Expected:**
  - Status: 200
  - Message: "Payment rejected. Client has been notified..."
  - admin_notes includes rejection reason
  - Escrow status remains "pending"
- **Result:** ☐ PASS / ☐ FAIL

---

## 4. ADMIN DASHBOARD TESTING

### 4.1 Page Load & Navigation

**Test Case 4.1.1: Admin Page Accessible**
- **Steps:**
  1. Log in as admin
  2. Navigate to /admin/duitnow-confirmations
- **Expected:**
  - Page loads without errors
  - No 404 or auth errors
  - Console has no JavaScript errors
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.1.2: Page Title & Header**
- **Steps:**
  1. View page header
- **Expected:**
  - Title: "DuitNow Payment Confirmations"
  - Subtitle: "Manage pending DuitNow QR code payments from clients"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.1.3: Statistics Display**
- **Steps:**
  1. View stats cards
  2. Compare with database
- **Expected:**
  - "Pending Confirmations" card shows count of pending escrows
  - "Amount Awaiting Verification" shows sum of amounts
  - "Confirmed Today" shows count of funded escrows today
  - All numbers accurate
- **Result:** ☐ PASS / ☐ FAIL

---

### 4.2 Confirmation List

**Test Case 4.2.1: Pending Confirmations Listed**
- **Steps:**
  1. Create 3 pending DuitNow payments
  2. View admin dashboard
  3. Check confirmation list
- **Expected:**
  - All 3 pending payments visible
  - Table shows: Gig, Amount, DuitNow Ref, Bank Ref, Status, Actions
  - Status badge shows "PENDING"
  - Green "View" button visible
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.2.2: Confirmed Payments Hidden by Default**
- **Steps:**
  1. Confirm 1 payment (status becomes "funded")
  2. View list without filter
- **Expected:**
  - Only pending payments shown
  - Confirmed payments not in list
  - Status bar updated (pending count decreased)
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.2.3: Filter by Status**
- **Steps:**
  1. Set filter: Status = "Confirmed"
  2. View list
- **Expected:**
  - Only confirmed payments shown
  - Status badges show "CONFIRMED"
  - Pending payments hidden
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.2.4: Filter by Client**
- **Steps:**
  1. Create payments from 2 different clients
  2. Select client filter
- **Expected:**
  - Only payments from selected client shown
  - Correct client name displayed
  - Payment count matches filter
- **Result:** ☐ PASS / ☐ FAIL

---

### 4.3 Detail Modal

**Test Case 4.3.1: Modal Opens with Payment Details**
- **Steps:**
  1. Click "View" on a payment
  2. Check modal content
- **Expected:**
  - Modal displays:
    - Gig title and code
    - Client name and email
    - Amount, references, status
    - Submit date/time
  - All data accurate
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.3.2: Verification Checklist**
- **Steps:**
  1. View modal
  2. Check checklist section
- **Expected:**
  - 4 checkboxes visible:
    1. Reference matches DuitNow ref
    2. Amount matches escrow amount
    3. Payment within 24 hours
    4. Correct account
  - All unchecked initially
  - Can be clicked to check
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.3.3: Checklist Validation**
- **Steps:**
  1. Try to confirm without checking boxes
  2. Check 1-2 boxes, try again
  3. Check all 4 boxes, confirm
- **Expected:**
  - Error: "Please complete all verification checks"
  - Error shown until all 4 checked
  - Confirms only when all checked
- **Result:** ☐ PASS / ☐ FAIL

---

### 4.4 Admin Actions

**Test Case 4.4.1: Confirm Button Works**
- **Steps:**
  1. Complete verification checklist
  2. Click "Confirm & Fund Escrow"
  3. Confirm in alert dialog
- **Expected:**
  - Modal closes
  - Success message: "Payment confirmed and escrow funded!"
  - List refreshes
  - Payment now shows as "Confirmed"
  - Stats updated
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.4.2: Reject Button Works**
- **Steps:**
  1. Click "Reject & Request Resubmission"
  2. Enter reason: "Reference incorrect"
  3. Check admin_notes in database
- **Expected:**
  - Modal closes
  - Success message: "Payment rejected. Client notified."
  - admin_notes contains rejection reason
  - Escrow remains pending
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 4.4.3: Email Notifications Sent**
- **Steps:**
  1. Confirm a payment
  2. Check email logs
  3. Reject a payment
  4. Check email logs again
- **Expected:**
  - Confirmation sends email to client
  - Rejection sends email to client
  - Emails contain relevant details
  - Emails sent from correct address
- **Result:** ☐ PASS / ☐ FAIL

---

## 5. SECURITY TESTING

### 5.1 Authorization

**Test Case 5.1.1: Clients Cannot Access Admin APIs**
- **Steps:**
  1. Log in as client
  2. Try to call: GET /api/admin/duitnow/pending-confirmations
- **Expected:**
  - Status: 403
  - Error: "Access denied"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 5.1.2: Clients Cannot Confirm Own Payments Directly**
- **Steps:**
  1. Log in as client
  2. Try to call: POST /api/admin/duitnow/{id}/confirm
- **Expected:**
  - Status: 403
  - Error: "Access denied"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 5.1.3: Unauthenticated Requests Denied**
- **Steps:**
  1. Make requests without auth cookie
- **Expected:**
  - Status: 401 or redirect to login
- **Result:** ☐ PASS / ☐ FAIL

---

### 5.2 Data Validation

**Test Case 5.2.1: SQL Injection Prevention**
- **Steps:**
  1. Submit bank reference: `'; DROP TABLE escrow; --`
  2. Check database integrity
- **Expected:**
  - Reference stored as-is (no execution)
  - Table still intact
  - No error logs with SQL
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 5.2.2: XSS Prevention in Admin Dashboard**
- **Steps:**
  1. Create payment with malicious client name: `<img src=x onerror=alert('xss')>`
  2. View admin dashboard
- **Expected:**
  - No JavaScript alert triggered
  - Malicious code displayed as text (escaped)
  - HTML source shows escaped tags
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 5.2.3: Reference Format Validation**
- **Steps:**
  1. Submit bank reference with unusual chars: `@#$%^&*()`
  2. Check storage and display
- **Expected:**
  - Reference accepted and stored
  - Displayed correctly without interpretation
  - No SQL/NoSQL injection
- **Result:** ☐ PASS / ☐ FAIL

---

### 5.3 Reference Matching

**Test Case 5.3.1: Unique References Prevent Mixing**
- **Steps:**
  1. Create 2 escrows for same client, same amount
  2. Confirm first with reference "REF001"
  3. Admin verifies first payment
- **Expected:**
  - References are different (ESC-{gig1} vs ESC-{gig2})
  - Each payment's reference unique
  - Admin cannot accidentally confirm wrong payment
- **Result:** ☐ PASS / ☐ FAIL

---

## 6. INTEGRATION TESTING

### 6.1 End-to-End Payment Flow

**Test Case 6.1.1: Complete DuitNow Payment Cycle**
- **Steps:**
  1. Client initiates DuitNow payment
  2. Client scans QR (simulate)
  3. Client submits bank reference
  4. Admin views pending payment
  5. Admin verifies and confirms
  6. Freelancer can proceed with work
- **Expected:**
  - All steps succeed
  - Data consistent throughout
  - Final status: funded
  - Wallet updated
  - Freelancer can release work
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 6.1.2: Failed Verification & Resubmission**
- **Steps:**
  1. Client submits DuitNow payment
  2. Admin rejects (wrong reference)
  3. Client submits again with correct reference
  4. Admin confirms
- **Expected:**
  - First rejection sent to client
  - Escrow remains pending
  - Second submission accepted
  - Admin can see both submissions
  - Final confirmation works
- **Result:** ☐ PASS / ☐ FAIL

---

### 6.2 Concurrent Operations

**Test Case 6.2.1: Race Condition - Multiple Admins**
- **Steps:**
  1. Two admins load same pending payment
  2. Admin A confirms
  3. Admin B tries to confirm same payment
- **Expected:**
  - Admin A confirmation succeeds
  - Admin B gets error: "Not pending" or status already changed
  - Payment only funded once
  - No duplicate processing
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 6.2.2: Client Spamming References**
- **Steps:**
  1. Client submits multiple references for same escrow
  2. Check database and admin dashboard
- **Expected:**
  - Only latest reference stored
  - No duplicate entries
  - Payment appears once in list
- **Result:** ☐ PASS / ☐ FAIL

---

## 7. PERFORMANCE TESTING

### 7.1 Query Performance

**Test Case 7.1.1: Admin Dashboard Load Time**
- **Steps:**
  1. Create 100 escrows (10% DuitNow pending)
  2. Load admin dashboard
  3. Measure response time
- **Expected:**
  - API response: < 1 second
  - Page load: < 3 seconds
  - No N+1 queries
  - Indexes used efficiently
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 7.1.2: QR Code Generation Time**
- **Steps:**
  1. Generate 10 QR codes
  2. Measure average generation time
- **Expected:**
  - Average: < 200ms per QR code
  - No timeouts (should be < 5s)
  - No memory leaks
- **Result:** ☐ PASS / ☐ FAIL

---

## 8. MOBILE TESTING

### 8.1 Responsive Design

**Test Case 8.1.1: Client Payment Form on Mobile**
- **Steps:**
  1. Access payment form on iPhone/Android
  2. Test all interactions
- **Expected:**
  - Payment methods stack vertically
  - QR code displays clearly
  - Can scroll to see all info
  - Reference input usable
  - Buttons clickable
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 8.1.2: Admin Dashboard on Tablet**
- **Steps:**
  1. Access admin dashboard on iPad
  2. Test filtering and details
- **Expected:**
  - List converts to card layout
  - Data labels visible
  - Filters accessible
  - Modal opens properly
  - Actions work correctly
- **Result:** ☐ PASS / ☐ FAIL

---

## 9. EDGE CASES

### 9.1 Data Edge Cases

**Test Case 9.1.1: Very Large Amount**
- **Steps:**
  1. Create escrow with amount: 999,999.99
  2. Generate DuitNow payment
- **Expected:**
  - QR code generated successfully
  - Amount displays correctly
  - No truncation or rounding errors
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 9.1.2: Very Small Amount**
- **Steps:**
  1. Create escrow with amount: 0.01
  2. Generate DuitNow payment
- **Expected:**
  - QR code generated successfully
  - Amount: RM 0.01
  - Proper formatting maintained
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 9.1.3: Long Client Names**
- **Steps:**
  1. Create client with name: "Very Long Name With Many Words That Goes On And On"
  2. View in admin dashboard
- **Expected:**
  - Name displays without overflow
  - Text wraps or truncates gracefully
  - Table layout maintained
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 9.1.4: Deleted Gig After Payment Creation**
- **Steps:**
  1. Create DuitNow payment for escrow
  2. Delete the gig
  3. Try to confirm payment as admin
- **Expected:**
  - Admin can still confirm payment
  - Error handling graceful
  - No crash or 500 error
- **Result:** ☐ PASS / ☐ FAIL

---

### 9.2 Timing Edge Cases

**Test Case 9.2.1: Payment Confirmation After 24 Hours**
- **Steps:**
  1. Create DuitNow payment
  2. Wait 24+ hours (or simulate time)
  3. Admin verifies and confirms
- **Expected:**
  - Confirmation still works
  - Timestamp shows correct time
  - No automatic expiration
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 9.2.2: Multiple Payments by Same Client**
- **Steps:**
  1. Client creates 5 DuitNow payments
  2. Admin confirms them in random order
  3. Check final state
- **Expected:**
  - Each payment tracked independently
  - References prevent mixing
  - All confirmed successfully
  - Wallet updated correctly for each
- **Result:** ☐ PASS / ☐ FAIL

---

## 10. ERROR HANDLING

### 10.1 API Error Responses

**Test Case 10.1.1: Missing Required Fields**
- **Steps:**
  1. POST /api/escrow/{id}/confirm-duitnow with no bank_reference
- **Expected:**
  - Status: 400
  - Error: "Bank reference is required"
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 10.1.2: Invalid Escrow ID**
- **Steps:**
  1. Try to confirm with invalid escrow ID
- **Expected:**
  - Status: 404
  - Error: "Not found" or appropriate message
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 10.1.3: Already Funded Escrow**
- **Steps:**
  1. Try to confirm an already-funded escrow
- **Expected:**
  - Status: 400
  - Error: "Escrow is not pending"
- **Result:** ☐ PASS / ☐ FAIL

---

### 10.2 Graceful Degradation

**Test Case 10.2.1: QR Generation Failure Handling**
- **Steps:**
  1. Mock QR service to fail
  2. Try to generate DuitNow payment
- **Expected:**
  - No crash
  - Error message to client: "Failed to generate QR code"
  - Escrow not created
- **Result:** ☐ PASS / ☐ FAIL

**Test Case 10.2.2: Database Connection Error**
- **Steps:**
  1. Simulate database connection failure
  2. Try to confirm payment
- **Expected:**
  - Error response with 500 status
  - Error message logged
  - Transaction rolled back
  - No partial data
- **Result:** ☐ PASS / ☐ FAIL

---

## Test Execution Summary

**Total Test Cases:** 80+

**Required Results for GO/NO-GO:**
- ✅ All correctness tests PASS
- ✅ All security tests PASS
- ✅ All API tests PASS (≥95%)
- ✅ Admin dashboard PASS (≥95%)
- ✅ Mobile responsiveness PASS (≥95%)
- ✅ No critical bugs
- ✅ No unhandled exceptions

**Sign-off:** 
- [ ] QA Lead: _________________ Date: _______
- [ ] Dev Lead: ________________ Date: _______
- [ ] Product Manager: _________ Date: _______
