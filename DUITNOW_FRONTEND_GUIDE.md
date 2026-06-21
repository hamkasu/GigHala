# DuitNow Frontend Integration Guide

## Overview

This guide covers the frontend integration of DuitNow QR code payments in GigHala. It includes:
1. **Client Payment Form** - How clients select and complete DuitNow payments
2. **Admin Dashboard** - How admins verify and manage pending confirmations
3. **User Experience Flow** - Step-by-step payment process

## Client Payment Experience

### Payment Method Selection

When a client clicks "Fund Escrow", they see a modal with payment method options:

```
┌─────────────────────────────────────────┐
│ Fund Escrow for: Sample Gig             │
├─────────────────────────────────────────┤
│                                         │
│ Payment Methods:                        │
│                                         │
│ [✓] DuitNow QR Code                     │
│     Scan with your banking app          │
│                                         │
│ [ ] FPX Online Banking                  │
│     Direct bank transfer                │
│                                         │
│ [ ] QR / E-Wallet                       │
│     GrabPay integration                 │
│                                         │
│ [ ] Card / Google Pay / Apple Pay       │
│     Stripe payment processor            │
│                                         │
│ [ ] Manual Bank Transfer                │
│     Direct account transfer             │
│                                         │
└─────────────────────────────────────────┘
        [Cancel] [Proceed to Payment]
```

### DuitNow QR Payment Screen

After selecting DuitNow, the client sees:

```
┌─────────────────────────────────────────┐
│ DuitNow Payment                         │
├─────────────────────────────────────────┤
│                                         │
│ Scan QR Code with Your Banking App      │
│                                         │
│          ┌──────────────┐               │
│          │   /\_/\_     │               │
│          │  |QR CODE|   │ ← QR image    │
│          │   \_/\_/     │               │
│          └──────────────┘               │
│                                         │
│ Bank Details:                           │
│ ┌─────────────────────────────────────┐ │
│ | Bank          | Maybank             | │
│ | Account       | ••••5678901         | │
│ | Recipient     | GigHala Sdn Bhd     | │
│ | Amount        | RM 1,500.00 (green) | │
│ | Reference     | ESC-123-ABC456      | │
│ └─────────────────────────────────────┘ │
│                                         │
│ ✓ How to Pay with DuitNow               │
│ 1. Open your banking app                │
│ 2. Look for "Scan QR" or "DuitNow"     │
│ 3. Point camera at QR code above        │
│ 4. Amount and reference auto-fill       │
│ 5. Enter your PIN to confirm            │
│                                         │
│ After Payment:                          │
│ ┌─────────────────────────────────────┐ │
│ | Bank Reference from transaction:    | │
│ | [________________] (e.g. DEC2025...) │ │
│ | Find in app under "Transaction..."  | │
│ └─────────────────────────────────────┘ │
│                                         │
└─────────────────────────────────────────┘
    [Cancel] [Confirm Payment Sent]
```

### Key Components

#### 1. QR Code Display

```html
<div class="qr-code-display">
    <img src="data:image/png;base64,iVBORw0KGgo..." alt="DuitNow QR Code" />
</div>
```

The QR code is displayed as a base64-encoded PNG image returned from the API.

#### 2. Payment Details Section

```html
<div class="duitnow-details">
    <div class="bank-row">
        <span>Bank</span>
        <span>Maybank</span>
    </div>
    <div class="bank-row">
        <span>Account</span>
        <span>512345678901</span>
    </div>
    <!-- ... more details ... -->
</div>
```

Shows all payment information needed for verification.

#### 3. Bank Reference Input

```html
<div class="duitnow-ref-section">
    <label for="duitnowReference">After Payment: Enter Your Bank Reference</label>
    <input type="text" id="duitnowReference" placeholder="e.g., DEC202512345678" />
</div>
```

Collects the bank transaction reference for verification.

## Client Payment Flow (Step-by-Step)

### Frontend Code

**1. Select Payment Method**

```javascript
function openFundModal(gigId, freelancerId) {
    // ... existing code ...
    
    // User clicks DuitNow payment method option
    document.querySelectorAll('.payment-method').forEach(pm => {
        pm.addEventListener('click', function() {
            document.querySelectorAll('.payment-method').forEach(p => p.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
}
```

**2. Initiate DuitNow Payment**

```javascript
function confirmFund() {
    const selectedMethod = document.querySelector('.payment-method.selected').dataset.method;
    
    if (selectedMethod === 'duitnow') {
        fetch(`/api/escrow/${currentGigId}/pay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ payment_method: 'duitnow' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.payment_method === 'duitnow') {
                closeModal('fundModal');
                showDuitNowPaymentModal(data);
            }
        });
    }
}
```

**3. Display QR Code and Instructions**

```javascript
function showDuitNowPaymentModal(data) {
    const qrCode = data.qr_code;  // base64 PNG image
    const details = data.payment_details;
    
    // Create modal with QR code and payment details
    const duitnowModal = document.createElement('div');
    duitnowModal.innerHTML = `
        <div class="qr-code-display">
            <img src="${qrCode}" alt="DuitNow QR Code" />
        </div>
        <div class="duitnow-details">
            <!-- payment details -->
        </div>
        <div class="qr-code-instructions">
            <!-- step-by-step instructions -->
        </div>
    `;
    document.body.appendChild(duitnowModal);
}
```

**4. Submit Bank Reference**

```javascript
function submitDuitNowPayment() {
    const bankRef = document.getElementById('duitnowReference').value.trim();
    
    fetch(`/api/escrow/${currentGigId}/confirm-duitnow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bank_reference: bankRef })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message, 'success');
            loadEscrows();
        }
    });
}
```

## Admin Dashboard

### Location

**URL:** `/admin/duitnow-confirmations`

**Access:** Admin users only

### Features

#### 1. Statistics Cards

```
┌──────────────┬──────────────┬──────────────┐
│ 5            │ RM 7,500     │ 8            │
│ Pending      │ Amount       │ Confirmed    │
│ Confirmations│ Awaiting     │ Today        │
│              │ Verification │              │
└──────────────┴──────────────┴──────────────┘
```

Updates in real-time as confirmations are processed.

#### 2. Filters

```
Status: [All       ▼]  Client: [All Clients ▼]  [Refresh]
```

Filter pending confirmations by:
- Status: Pending / Confirmed
- Client name

#### 3. Confirmation Table

```
┌─────────────────┬────────────┬──────────────┬────────────┬──────────┬────────┐
│ Gig Details     │ Amount     │ DuitNow Ref  │ Bank Ref   │ Status   │ Action │
├─────────────────┼────────────┼──────────────┼────────────┼──────────┼────────┤
│ Sample Gig      │ RM 1,500   │ ESC-123-ABC  │ Pending    │ Pending  │ [View] │
│ Client: John    │            │              │            │          │        │
│ 21 Jun 2026     │            │              │            │          │        │
├─────────────────┼────────────┼──────────────┼────────────┼──────────┼────────┤
│ Another Gig     │ RM 2,500   │ ESC-124-DEF  │ DEC2025001 │ Confirmed│ [View] │
│ Client: Jane    │            │              │            │          │        │
│ 20 Jun 2026     │            │              │            │          │        │
└─────────────────┴────────────┴──────────────┴────────────┴──────────┴────────┘
```

#### 4. Payment Details Modal

```
┌─────────────────────────────────────────────┐
│ DuitNow Payment Details                     │
├─────────────────────────────────────────────┤
│                                             │
│ Gig Information                             │
│ ┌─────────────────────────────────────────┐ │
│ | Gig Title       | Sample Gig            | │
│ | Gig Code        | GIG-123               | │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Client Information                          │
│ ┌─────────────────────────────────────────┐ │
│ | Name            | John Doe              | │
│ | Email           | john@example.com      | │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Payment Details                             │
│ ┌─────────────────────────────────────────┐ │
│ | Amount          | RM 1,500.00           | │
│ | DuitNow Ref     | ESC-123-ABC456        | │
│ | Bank Ref        | DEC2025123456         | │
│ | Status          | PENDING               | │
│ | Submitted       | 21 Jun 2026, 2:30 PM  | │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Verification Checklist                      │
│ ┌─────────────────────────────────────────┐ │
│ | ☐ Bank reference matches DuitNow ref    | │
│ | ☐ Amount matches escrow amount          | │
│ | ☐ Payment received within last 24h      | │
│ | ☐ Payment received to correct account   | │
│ └─────────────────────────────────────────┘ │
│                                             │
├─────────────────────────────────────────────┤
│ [Cancel] [Reject] [Confirm & Fund Escrow]  │
└─────────────────────────────────────────────┘
```

### Admin Workflow

#### Verification Process

1. **Review Payment Details**
   - Check gig information
   - Verify client identity
   - Review payment amount and references

2. **Verify Against Bank Statement**
   - Log into Maybank
   - Find transaction matching:
     - Amount: RM 1,500.00
     - Reference: ESC-123-ABC456
     - Recipient: GigHala Sdn Bhd

3. **Complete Verification Checklist**
   ```
   ☑ Bank reference matches DuitNow ref (ESC-123-ABC456)
   ☑ Amount matches escrow amount (RM 1,500.00)
   ☑ Payment received within last 24 hours
   ☑ Payment received to correct account
   ```

4. **Confirm or Reject**
   - **Confirm:** Payment is valid, escrow is funded
   - **Reject:** Ask for reason, client resubmits

#### Admin Actions

**Confirm Payment:**
```javascript
function confirmPayment() {
    // All checkboxes must be checked
    if (!document.getElementById('checkRef').checked ||
        !document.getElementById('checkAmount').checked ||
        !document.getElementById('checkTime').checked ||
        !document.getElementById('checkAccount').checked) {
        showAlert('Please complete all verification checks', 'error');
        return;
    }

    fetch(`/api/admin/duitnow/${escrowId}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Payment confirmed and escrow funded!', 'success');
            loadConfirmations();
        }
    });
}
```

**Reject Payment:**
```javascript
function rejectPayment() {
    const reason = prompt('Enter reason for rejection:');
    if (!reason) return;

    fetch(`/api/admin/duitnow/${escrowId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Payment rejected. Client notified.', 'success');
            loadConfirmations();
        }
    });
}
```

## Styling

### DuitNow-Specific CSS Classes

```css
/* QR Code Container */
.qr-code-container {
    border: 2px dashed var(--primary);
    padding: 24px;
    margin: 20px 0;
}

/* QR Code Display */
.qr-code-display {
    text-align: center;
    margin-bottom: 24px;
}

.qr-code-display img {
    max-width: 280px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* DuitNow Details */
.duitnow-details {
    background: var(--bg-light);
    padding: 16px;
    border-radius: var(--radius-md);
}

/* Reference Input Section */
.duitnow-ref-section {
    background: #FFFBEB;
    border: 1px solid #FCD34D;
    padding: 16px;
    margin-top: 16px;
}

/* Instructions */
.qr-code-instructions {
    background: #F0FDF4;
    border: 1px solid #BBEF63;
    padding: 16px;
    margin-bottom: 16px;
}
```

### Payment Method Selection

```css
.payment-method {
    border: 2px solid var(--border);
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s;
}

.payment-method:hover {
    border-color: var(--primary);
}

.payment-method.selected {
    border-color: var(--primary);
    background: #F0FDF4;
}

.payment-method.duitnow {
    border-color: #10B981;
}

.payment-method.duitnow.selected {
    background: #F0FDF4;
    border-color: #10B981;
}
```

## API Endpoints (Frontend Perspective)

### Client Endpoints

**Initiate DuitNow Payment**
```
POST /api/escrow/<gig_id>/pay
Content-Type: application/json

{
  "payment_method": "duitnow"
}

Response:
{
  "success": true,
  "payment_method": "duitnow",
  "qr_code": "data:image/png;base64,...",
  "payment_details": {
    "bank_name": "Maybank",
    "account_number": "512345678901",
    "amount": 1500.00,
    "reference": "ESC-123-ABC456"
  },
  "escrow": { /* escrow object */ }
}
```

**Submit Bank Reference**
```
POST /api/escrow/<gig_id>/confirm-duitnow
Content-Type: application/json

{
  "bank_reference": "DEC2025123456"
}

Response:
{
  "success": true,
  "message": "Bank reference submitted. Admin will verify...",
  "escrow": { /* escrow object */ }
}
```

### Admin Endpoints

**Get Pending Confirmations**
```
GET /api/admin/duitnow/pending-confirmations

Response:
{
  "success": true,
  "confirmations": [
    {
      "escrow_id": 123,
      "gig_title": "Sample Gig",
      "client_name": "John Doe",
      "amount": 1500.00,
      "duitnow_reference": "ESC-123-ABC456",
      "bank_reference": "DEC2025123456",
      "status": "pending",
      "created_at": "2026-06-21T02:30:00"
    }
  ],
  "stats": {
    "pending": 5,
    "total_amount": 7500.00,
    "confirmed_today": 8
  }
}
```

**Confirm Payment**
```
POST /api/admin/duitnow/<escrow_id>/confirm

Response:
{
  "success": true,
  "message": "DuitNow payment confirmed and escrow funded",
  "escrow": { /* escrow object */ }
}
```

**Reject Payment**
```
POST /api/admin/duitnow/<escrow_id>/reject
Content-Type: application/json

{
  "reason": "Bank reference does not match DuitNow reference"
}

Response:
{
  "success": true,
  "message": "Payment rejected. Client has been notified...",
  "escrow": { /* escrow object */ }
}
```

## Responsive Design

The interface is fully responsive for mobile devices:

### Mobile Layout (Under 768px)

- Payment method selector: Full-width stacked buttons
- QR code display: Responsive image sizing
- Admin table: Converts to card layout with data labels
- Filters: Stacked vertically
- Buttons: Full-width for easier touch targets

## Testing the Integration

### Manual Testing Checklist

- [ ] Client can select DuitNow as payment method
- [ ] QR code displays correctly with base64 image
- [ ] Payment details show correctly (bank, account, amount, reference)
- [ ] Instructions are clear and helpful
- [ ] Client can enter bank reference
- [ ] Submission works and shows success message
- [ ] Admin can view pending confirmations
- [ ] Admin filters work (by status, client)
- [ ] Admin can view payment details
- [ ] Admin verification checklist works
- [ ] Admin can confirm payment
- [ ] Admin can reject payment with reason
- [ ] Escrow status updates to "funded" after confirmation
- [ ] Wallet balance updates correctly
- [ ] Email notifications sent to client

## Troubleshooting

### QR Code Not Displaying

1. Check that the API response includes `qr_code` field
2. Verify it's a valid base64-encoded PNG string
3. Check browser console for errors

### Bank Reference Not Accepting

1. Check input validation in `submitDuitNowPayment()`
2. Verify API endpoint is working: POST `/api/escrow/{gig_id}/confirm-duitnow`
3. Check error response for validation issues

### Admin Dashboard Not Loading

1. Verify user is admin: `user.is_admin === true`
2. Check network tab for API request to `/api/admin/duitnow/pending-confirmations`
3. Verify admin endpoint is implemented in app.py

## Future Enhancements

1. **Real-time Updates** - WebSocket for live confirmation updates
2. **Email Notifications** - Auto-send links for easier verification
3. **Mobile App Integration** - Native mobile app DuitNow support
4. **Multiple Bank Support** - Add different bank accounts
5. **Batch Verification** - Confirm multiple payments at once
6. **Payment History** - Dashboard showing past DuitNow payments
7. **Auto-reconciliation** - API integration with Maybank for auto-verification

## Support

For issues or questions about the frontend integration:
1. Check this guide first
2. Review DUITNOW_IMPLEMENTATION.md for backend details
3. Check test file: test_duitnow_qr.py
4. Contact development team
