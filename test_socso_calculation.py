#!/usr/bin/env python3
"""
SOCSO Calculation Test Script
Tests the 1.25% SOCSO deduction logic for compliance with Gig Workers Bill 2025
"""

def calculate_socso(net_earnings):
    """
    Calculate SOCSO contribution as per Gig Workers Bill 2025
    SOCSO Rate: 1.25% of net earnings (after platform commission)
    """
    if net_earnings <= 0:
        return 0.0
    return round(net_earnings * 0.0125, 2)  # 1.25%


def test_socso_calculations():
    """Run comprehensive SOCSO calculation tests"""

    print("=" * 60)
    print("SOCSO CALCULATION TESTS - Gig Workers Bill 2025")
    print("Deduction Rate: 1.25% of net earnings")
    print("=" * 60)
    print()

    # Test cases
    test_cases = [
        # (net_earnings, expected_socso, description)
        (1000.00, 12.50, "Standard MYR 1,000 payout"),
        (900.00, 11.25, "MYR 900 net after commission"),
        (800.00, 10.00, "MYR 800 payout"),
        (500.00, 6.25, "MYR 500 payout"),
        (100.00, 1.25, "MYR 100 minimum payout"),
        (50.00, 0.62, "MYR 50 small payout (banker's rounding to 0.62)"),
        (833.33, 10.42, "MYR 833.33 with rounding"),
        (1234.56, 15.43, "MYR 1,234.56 precise calculation"),
        (5000.00, 62.50, "MYR 5,000 large payout"),
        (10000.00, 125.00, "MYR 10,000 very large payout"),
        (0.00, 0.00, "Zero earnings"),
        (-100.00, 0.00, "Negative earnings (edge case)"),
    ]

    passed = 0
    failed = 0

    print("Test Results:")
    print("-" * 60)

    for net_earnings, expected_socso, description in test_cases:
        calculated_socso = calculate_socso(net_earnings)
        status = "✓ PASS" if calculated_socso == expected_socso else "✗ FAIL"

        if calculated_socso == expected_socso:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {description}")
        print(f"      Net Earnings: MYR {net_earnings:,.2f}")
        print(f"      Expected SOCSO: MYR {expected_socso:.2f}")
        print(f"      Calculated SOCSO: MYR {calculated_socso:.2f}")

        if calculated_socso != expected_socso:
            print(f"      ERROR: Mismatch!")

        print()

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    print()

    # Practical scenario tests
    print("PRACTICAL SCENARIO TESTS")
    print("=" * 60)
    print()

    scenarios = [
        {
            "description": "Graphic design gig",
            "gross_amount": 1000.00,
            "commission_rate": 0.10,  # 10%
        },
        {
            "description": "Video editing project",
            "gross_amount": 2500.00,
            "commission_rate": 0.05,  # 5%
        },
        {
            "description": "Translation service",
            "gross_amount": 500.00,
            "commission_rate": 0.15,  # 15%
        },
        {
            "description": "Web development",
            "gross_amount": 5000.00,
            "commission_rate": 0.05,  # 5%
        }
    ]

    for scenario in scenarios:
        gross = scenario["gross_amount"]
        commission_rate = scenario["commission_rate"]
        commission = round(gross * commission_rate, 2)
        net_earnings = round(gross - commission, 2)
        socso = calculate_socso(net_earnings)
        final_payout = round(net_earnings - socso, 2)

        print(f"Scenario: {scenario['description']}")
        print(f"  Gross Amount:        MYR {gross:>10,.2f}")
        print(f"  Platform Commission: MYR {commission:>10,.2f} ({commission_rate*100:.0f}%)")
        print(f"  " + "-" * 40)
        print(f"  Net Earnings:        MYR {net_earnings:>10,.2f}")
        print(f"  SOCSO Deduction:     MYR {socso:>10,.2f} (1.25%)")
        print(f"  " + "-" * 40)
        print(f"  Final Payout:        MYR {final_payout:>10,.2f}")
        print()

    print("=" * 60)

    # Summary
    if failed == 0:
        print("✓ ALL TESTS PASSED - SOCSO calculations are correct!")
    else:
        print(f"✗ {failed} TEST(S) FAILED - Review calculation logic!")

    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = test_socso_calculations()
    exit(0 if success else 1)
