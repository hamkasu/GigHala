#!/usr/bin/env python3
"""Test script to verify escrow SOCSO calculations"""

def calculate_socso(net_earnings):
    """Calculate SOCSO contribution (1.25% of net earnings)"""
    if net_earnings <= 0:
        return 0.0
    return round(net_earnings * 0.0125, 2)

def test_user_example():
    """Test the user's specific example from the screenshot"""
    print("=" * 60)
    print("Testing User's Example: RM 75.00 Escrow")
    print("=" * 60)

    escrow_amount = 75.00
    platform_fee_rate = 0.15  # 15%

    platform_fee = round(escrow_amount * platform_fee_rate, 2)
    net_amount = round(escrow_amount - platform_fee, 2)
    socso_amount = calculate_socso(net_amount)
    final_payout = round(net_amount - socso_amount, 2)

    print(f"Escrow Amount:        RM {escrow_amount:.2f}")
    print(f"Platform Fee (15%):   RM {platform_fee:.2f}")
    print(f"Net Amount:           RM {net_amount:.2f}")
    print(f"SOCSO (1.25% of net): RM {socso_amount:.2f}")
    print(f"Final Payout:         RM {final_payout:.2f}")
    print()
    print(f"Total Deductions:     RM {(platform_fee + socso_amount):.2f}")
    print()

    # Verify the issue
    print("BEFORE FIX (Incorrect):")
    incorrect_socso = round(escrow_amount * 0.0125, 2)  # Wrong: calculated on gross
    print(f"  SOCSO shown: RM {incorrect_socso:.2f} (calculated on gross amount)")
    print(f"  Freelancer receives: RM {net_amount:.2f} (no SOCSO deducted)")
    print()

    print("AFTER FIX (Correct):")
    print(f"  SOCSO shown: RM {socso_amount:.2f} (calculated on net amount)")
    print(f"  Freelancer receives: RM {final_payout:.2f} (after SOCSO deduction)")
    print()

    # Validation
    assert socso_amount == 0.80, f"Expected SOCSO to be 0.80, got {socso_amount}"
    assert final_payout == 62.95, f"Expected final payout to be 62.95, got {final_payout}"
    print("✓ All assertions passed!")

def test_additional_examples():
    """Test additional scenarios"""
    print("\n" + "=" * 60)
    print("Additional Test Cases")
    print("=" * 60)

    test_cases = [
        {"amount": 100.00, "platform_fee_rate": 0.15},
        {"amount": 500.00, "platform_fee_rate": 0.15},
        {"amount": 1000.00, "platform_fee_rate": 0.10},
        {"amount": 250.00, "platform_fee_rate": 0.15},
    ]

    for case in test_cases:
        amount = case["amount"]
        rate = case["platform_fee_rate"]

        platform_fee = round(amount * rate, 2)
        net_amount = round(amount - platform_fee, 2)
        socso = calculate_socso(net_amount)
        final_payout = round(net_amount - socso, 2)

        print(f"\nEscrow: RM {amount:.2f} | Platform: {rate*100}%")
        print(f"  Platform Fee: RM {platform_fee:.2f}")
        print(f"  Net Amount: RM {net_amount:.2f}")
        print(f"  SOCSO: RM {socso:.2f}")
        print(f"  Final Payout: RM {final_payout:.2f}")

if __name__ == "__main__":
    test_user_example()
    test_additional_examples()
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
