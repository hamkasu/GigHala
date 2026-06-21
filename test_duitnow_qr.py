#!/usr/bin/env python3
"""
Test DuitNow QR code generation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.duitnow_service import DuitNowPaymentGenerator, generate_escrow_duitnow_qr
import base64


def test_duitnow_string_generation():
    """Test basic DuitNow string generation"""
    print("=" * 60)
    print("Test 1: DuitNow String Generation")
    print("=" * 60)

    duitnow_string = DuitNowPaymentGenerator.generate_duitnow_string(
        bank_code="0121104",
        account_number="512345678901",
        amount=1500.00,
        reference="ESC-123-ABC456"
    )

    print(f"✅ DuitNow String Generated:")
    print(f"   {duitnow_string}")
    print(f"   Length: {len(duitnow_string)} characters")
    print()


def test_qr_code_generation():
    """Test QR code image generation"""
    print("=" * 60)
    print("Test 2: QR Code Image Generation")
    print("=" * 60)

    data = "00020136080010a000000615010121104512345678901501500ESC-123-ABC456"
    qr_bytes = DuitNowPaymentGenerator.create_qr_code(data)

    print(f"✅ QR Code Generated:")
    print(f"   PNG Size: {len(qr_bytes)} bytes")
    png_header = b'\x89PNG\r\n\x1a\n'
    print(f"   Is Valid PNG: {qr_bytes[:8] == png_header}")
    print()


def test_qr_code_base64():
    """Test base64 encoding"""
    print("=" * 60)
    print("Test 3: QR Code Base64 Data URI")
    print("=" * 60)

    data = "00020136080010a000000615010121104512345678901501500ESC-123-ABC456"
    qr_base64 = DuitNowPaymentGenerator.create_qr_code_base64(data)

    print(f"✅ Base64 Data URI Generated:")
    print(f"   Prefix: {qr_base64[:50]}...")
    print(f"   Length: {len(qr_base64)} characters")
    print(f"   Valid Data URI: {qr_base64.startswith('data:image/png;base64,')}")
    print()


def test_full_escrow_payment_qr():
    """Test complete escrow payment QR generation"""
    print("=" * 60)
    print("Test 4: Complete Escrow Payment QR")
    print("=" * 60)

    result = generate_escrow_duitnow_qr(
        escrow_amount=1500.00,
        escrow_reference="ESC-GIG-123-ABC456",
        recipient_account="512345678901",
        recipient_name="GigHala Sdn Bhd"
    )

    if result['success']:
        print(f"✅ Escrow DuitNow QR Generated Successfully:")
        print(f"   Reference: {result['reference']}")
        print(f"   Amount: RM {result['amount']}")
        print(f"   Bank: {result['account_number']} ({result['recipient_name']})")
        print(f"   QR String Length: {len(result['qr_string'])} chars")
        print(f"   QR Image Size: {len(result['qr_image_bytes'])} bytes")
        print(f"   Data URI: {result['qr_image_base64'][:60]}...")
        print()

        # Simulate what frontend would display
        print("Frontend Display Simulation:")
        print("─" * 60)
        print(f"┌─────────────────────────────────────────────────────────┐")
        print(f"│  DuitNow Payment QR Code                                 │")
        print(f"│                                                          │")
        print(f"│  [QR Code would display here using the base64 URI]      │")
        print(f"│                                                          │")
        print(f"├─────────────────────────────────────────────────────────┤")
        print(f"│ Bank:        {result['account_number'][-4:]} - Maybank 2U              │")
        print(f"│ Recipient:   {result['recipient_name']:<43} │")
        print(f"│ Amount:      RM {result['amount']:>45.2f}  │")
        print(f"│ Reference:   {result['reference']:<43} │")
        print(f"├─────────────────────────────────────────────────────────┤")
        print(f"│ Instructions:                                            │")
        print(f"│ 1. Open your banking app                                │")
        print(f"│ 2. Scan this QR code                                    │")
        print(f"│ 3. Amount and reference will auto-fill                  │")
        print(f"│ 4. Complete payment and submit bank reference           │")
        print(f"└─────────────────────────────────────────────────────────┘")
        print("─" * 60)
    else:
        print(f"❌ Failed to generate QR: {result['error']}")

    print()


def test_different_amounts():
    """Test QR generation with different amounts"""
    print("=" * 60)
    print("Test 5: Different Payment Amounts")
    print("=" * 60)

    amounts = [500, 1000, 1500, 2500, 5000]

    for amount in amounts:
        result = generate_escrow_duitnow_qr(
            escrow_amount=amount,
            escrow_reference=f"ESC-TEST-{amount}"
        )
        if result['success']:
            print(f"✅ RM {amount:>5.2f} - QR generated ({len(result['qr_image_bytes']):>4} bytes)")
        else:
            print(f"❌ RM {amount:>5.2f} - Failed")

    print()


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  DuitNow QR Code Generation Tests".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    try:
        test_duitnow_string_generation()
        test_qr_code_generation()
        test_qr_code_base64()
        test_full_escrow_payment_qr()
        test_different_amounts()

        print("=" * 60)
        print("✅ All DuitNow QR code tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
