# DuitNow QR Code Payment Implementation

## Overview

This document describes the DuitNow QR code payment system implemented for GigHala's Malaysia-based escrow payments. DuitNow is an interbank QR code standard that allows customers to make payments by scanning a QR code with their banking app.

## Architecture

### Components

1. **DuitNow Service** (`services/duitnow_service.py`)
   - Generates DuitNow-compliant QR codes
   - Creates EMVCo-formatted payment strings
   - Handles QR code image generation and base64 encoding

2. **Escrow Model Extensions** (`app.py`)
   - New fields for DuitNow payment tracking
   - Payment method selection
   - QR code storage

3. **Payment Endpoints** (`app.py`)
   - Modified `/api/escrow/<gig_id>/pay` - Supports DuitNow method selection
   - New `/api/escrow/<gig_id>/confirm-duitnow` - Handles payment confirmation

4. **Database Migration** (`migrations/add_duitnow_fields_to_escrow.sql`)
   - Adds 5 new columns to escrow table
   - Creates indexes for faster lookups

## Database Schema

### New Escrow Fields

```sql
payment_method VARCHAR(30)           -- 'duitnow', 'fpx', 'bank_transfer'
qr_code_image LONGBLOB               -- PNG image bytes for QR code
qr_code_string TEXT                  -- DuitNow EMVCo formatted string
duitnow_reference VARCHAR(50)        -- Unique reference (ESC-{gig_id}-{random})
payment_confirmation_ref VARCHAR(100) -- Client's bank transaction reference
```

### Indexes Created

- `idx_escrow_duitnow_reference` - For payment matching
- `idx_escrow_payment_method` - For querying by payment method

## Payment Flow

### Client Perspective (Step-by-Step)

```
1. Client selects "DuitNow QR" payment method
   ↓
2. System generates:
   - Unique escrow reference: ESC-{gig_id}-{random}
   - DuitNow QR code with payment details
   ↓
3. Client sees:
   ┌──────────────────────────┐
   │   [QR Code Image]        │
   │                          │
   │ Bank:     Maybank        │
   │ Amount:   RM 1,500       │
   │ Ref:      ESC-123-ABC456 │
   └──────────────────────────┘
   ↓
4. Client opens banking app (Maybank, CIMB, etc.)
   ↓
5. Client scans QR code
   → Banking app auto-fills:
     - Recipient: GigHala Sdn Bhd
     - Account: 512345678901
     - Amount: RM 1,500
     - Reference: ESC-123-ABC456
   ↓
6. Client enters PIN to confirm
   ↓
7. Payment sent to GigHala's Maybank account
   ↓
8. Client receives bank reference (e.g., "TRANSACTION123456")
   ↓
9. Client submits bank reference in payment confirmation screen
   ↓
10. Admin verifies:
    - Bank statement shows matching reference
    - Amount matches escrow amount
    ↓
11. Admin clicks "Confirm Payment"
    ↓
12. Escrow marked as "funded"
    Freelancer can proceed with work
```

## API Endpoints

### 1. Initiate Payment (with DuitNow Support)

**Endpoint:** `POST /api/escrow/<gig_id>/pay`

**Request:**
```json
{
  "amount": 1500.00,
  "payment_method": "duitnow"  // New: or "bank_transfer", "fpx"
}
```

**DuitNow Response:**
```json
{
  "success": true,
  "payment_method": "duitnow",
  "escrow": {
    "id": 123,
    "escrow_number": "RET-ABC12345",
    "amount": 1500.00,
    "payment_method": "duitnow",
    "duitnow_reference": "ESC-123-ABC456",
    // ... other escrow fields
  },
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "payment_details": {
    "bank_name": "Maybank",
    "account_number": "512345678901",
    "account_name": "GigHala Sdn Bhd",
    "amount": 1500.00,
    "reference": "ESC-123-ABC456",
    "instructions": "Scan the QR code with your banking app..."
  },
  "fee_breakdown": {
    "gig_amount": 1500.00,
    "platform_fee": 150.00,
    "freelancer_receives": 1350.00
  }
}
```

### 2. Confirm DuitNow Payment

**Endpoint:** `POST /api/escrow/<gig_id>/confirm-duitnow`

**Request (Client):**
```json
{
  "bank_reference": "TRANSACTION123456"  // From client's bank app
}
```

**Client Response:**
```json
{
  "success": true,
  "message": "Bank reference submitted. Admin will verify within 24 hours.",
  "escrow": { /* escrow object */ }
}
```

**Admin Flow:**
1. Verify bank statement has matching transaction
2. Confirm payment via same endpoint
3. System marks escrow as "funded"

## DuitNow Service Usage

### Basic QR Generation

```python
from services.duitnow_service import DuitNowPaymentGenerator

# Generate DuitNow string (EMVCo format)
qr_string = DuitNowPaymentGenerator.generate_duitnow_string(
    bank_code="0121104",      # Maybank
    account_number="512345678901",
    amount=1500.00,
    reference="ESC-123-ABC456"
)

# Generate QR code image
qr_bytes = DuitNowPaymentGenerator.create_qr_code(qr_string)

# Get base64 data URI for HTML display
qr_base64 = DuitNowPaymentGenerator.create_qr_code_base64(qr_string)
# Returns: "data:image/png;base64,iVBORw0KGgo..."
```

### Complete Escrow QR

```python
from services.duitnow_service import generate_escrow_duitnow_qr

result = generate_escrow_duitnow_qr(
    escrow_amount=1500.00,
    escrow_reference="ESC-GIG-123-ABC456"
)

if result['success']:
    print(result['qr_image_base64'])  # Display in frontend
    print(result['qr_string'])         # Store in database
```

## Frontend Implementation

### Payment Method Selector

```html
<div class="payment-method-selector">
  <label>
    <input type="radio" name="payment_method" value="duitnow">
    DuitNow QR Code
  </label>
  <label>
    <input type="radio" name="payment_method" value="bank_transfer">
    Manual Bank Transfer
  </label>
  <label>
    <input type="radio" name="payment_method" value="fpx">
    FPX (Future)
  </label>
</div>
```

### QR Code Display

```html
<div id="qr-container" style="display:none;">
  <img id="qr-code" style="max-width: 300px;" />
  <p>Scan with your banking app</p>
</div>
```

### JavaScript Integration

```javascript
// Handle payment method change
document.querySelectorAll('input[name="payment_method"]').forEach(radio => {
  radio.addEventListener('change', async (e) => {
    const method = e.target.value;
    
    if (method === 'duitnow') {
      // Show DuitNow QR option
      document.getElementById('qr-container').style.display = 'block';
    } else {
      document.getElementById('qr-container').style.display = 'none';
    }
  });
});

// Initiate payment
async function initiatePayment() {
  const response = await fetch(`/api/escrow/${gigId}/pay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      amount: 1500.00,
      payment_method: 'duitnow'
    })
  });
  
  const data = await response.json();
  
  if (data.success && data.payment_method === 'duitnow') {
    // Display QR code
    document.getElementById('qr-code').src = data.qr_code;
    document.getElementById('qr-container').style.display = 'block';
    
    // Show payment details
    document.getElementById('bank-name').textContent = 
      data.payment_details.bank_name;
    document.getElementById('account').textContent = 
      data.payment_details.account_number;
    document.getElementById('amount').textContent = 
      `RM ${data.payment_details.amount}`;
    document.getElementById('reference').textContent = 
      data.payment_details.reference;
  }
}

// Submit bank reference after payment
async function submitPaymentConfirmation() {
  const bankRef = document.getElementById('bank-ref-input').value;
  
  const response = await fetch(`/api/escrow/${gigId}/confirm-duitnow`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bank_reference: bankRef
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    alert('Payment reference submitted. Admin will verify within 24 hours.');
  }
}
```

## Payment Matching Strategy

### Reference-Based Matching

The key to payment verification is the **unique reference number**:

1. **Generation**: System creates `ESC-{gig_id}-{random_8_chars}`
   - Example: `ESC-123-ABC456`

2. **QR Encoding**: Reference embedded in DuitNow QR string
   - When client scans, banking app includes reference in transaction

3. **Bank Record**: Payment appears in bank statement with reference
   - Example: "Transfer In - 1500.00 ESC-123-ABC456"

4. **Verification**: Admin matches references
   ```
   Escrow Record:  ESC-123-ABC456 (RM 1500)
   ↓ matches ↓
   Bank Statement: ESC-123-ABC456 (RM 1500)
   ↓
   Confirm & Mark as Funded
   ```

### Admin Verification Checklist

- [ ] Reference number matches (`duitnow_reference` = bank statement reference)
- [ ] Amount matches (escrow amount = transferred amount)
- [ ] Timestamp reasonable (recent payment, within 24 hours)
- [ ] Client bank reference stored (`payment_confirmation_ref`)
- [ ] Notes updated with bank details and confirmation time

## Configuration

### Recipient Account Details (Hardcoded)

```python
# In app.py - initiate_escrow_payment endpoint
recipient_account = "512345678901"  # Update with actual Maybank account
recipient_name = "GigHala Sdn Bhd"  # Update with actual company name
```

**To Change:** Update these values in the endpoint and DuitNow service calls.

### Bank Codes Reference

Common Malaysian bank codes for DuitNow:

- Maybank: `0121104`
- CIMB: `0342001`
- Public Bank: `0233006`
- Hong Leong: `0208001`
- OCBC: `0229001`
- RHB: `0218001`
- AmBank: `0227001`
- UOB: `0226001`

## Testing

### Run Tests

```bash
python test_duitnow_qr.py
```

### Test Coverage

- ✅ DuitNow string generation
- ✅ QR code image creation
- ✅ Base64 data URI encoding
- ✅ Complete escrow payment QR
- ✅ Multiple payment amounts

## Security Considerations

1. **Reference Uniqueness**: Each escrow gets unique reference
   - Prevents payment mixing between orders

2. **Reference Validation**: Admin must verify reference matches
   - Prevents accidental confirmation of wrong payment

3. **Amount Verification**: System checks amount matches escrow
   - Catches shortfalls or overpayments

4. **Timestamp Tracking**: Records when payment confirmed
   - Audit trail for disputes

5. **Admin-Only Confirmation**: Only admins can mark as funded
   - Prevents client self-confirmation

## Future Enhancements

1. **Automated Payment Verification**
   - Integrate with Maybank API for automatic confirmation
   - Real-time webhook notifications

2. **Multiple Bank Support**
   - Support different recipient accounts per region
   - Dynamic bank code selection

3. **FPX Integration**
   - Add FPX (Fund Transfer Online) as payment method
   - Similar flow but different QR standard

4. **Payment Reconciliation**
   - Automated daily bank statement matching
   - Flag unmatched payments for admin review

5. **Receipt Generation**
   - Auto-generate receipts from QR code data
   - Email receipts to client and freelancer

## Troubleshooting

### QR Code Not Generating

- Verify `qrcode` library is installed: `pip install qrcode[pil]`
- Check amount is valid (> 0)
- Check reference string is not too long (max 50 chars)

### Payment Not Matching

- Verify reference in bank statement exactly matches `duitnow_reference`
- Check amount in bank statement matches escrow amount
- Look for additional fees or surcharges

### Escrow Not Updating

- Verify user is admin (for direct confirmation)
- Check escrow status is "pending"
- Check payment_method is "duitnow"

## References

- [DuitNow Official Documentation](https://www.bnm.gov.my/financial-infrastructure/payment-systems/duitnow)
- [EMVCo QR Code Standard](https://www.emvco.com/)
- [Malaysian Banking Standards](https://www.bnm.gov.my/)

## Support

For questions or issues with the DuitNow implementation:
1. Check this documentation
2. Review the test file: `test_duitnow_qr.py`
3. Check app.py endpoints for example usage
4. Contact the development team
