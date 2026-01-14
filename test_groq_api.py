#!/usr/bin/env python3
"""
Test script to verify Groq API key is working correctly
Run this before deploying to production
"""

import os
import sys
from groq_moderation import (
    ai_halal_moderation,
    check_groq_api_health,
    GROQ_API_KEY
)

def print_separator():
    print("=" * 70)

def test_api_key_configured():
    """Test 1: Check if API key is configured"""
    print_separator()
    print("TEST 1: API Key Configuration")
    print_separator()

    if GROQ_API_KEY:
        print(f"✅ GROQ_API_KEY is configured")
        print(f"   Key length: {len(GROQ_API_KEY)} characters")
        print(f"   Key starts with: {GROQ_API_KEY[:10]}...")
        return True
    else:
        print("❌ GROQ_API_KEY is NOT configured")
        print("\nTo configure:")
        print("  export GROQ_API_KEY='your-api-key-here'")
        print("\nOr add to .env file:")
        print("  GROQ_API_KEY=your-api-key-here")
        return False

def test_halal_content():
    """Test 2: Test with clear halal content"""
    print_separator()
    print("TEST 2: Halal Content Detection")
    print_separator()

    title = "Quran Teacher for Children"
    description = "Looking for experienced Quran teacher to teach tajweed and memorization to children aged 7-12."

    print(f"Title: {title}")
    print(f"Description: {description}")
    print("\nSending to Groq API...")

    result = ai_halal_moderation(title, description)

    print(f"\n📊 Result:")
    print(f"  Success: {result['success']}")
    print(f"  Is Halal: {result.get('is_halal', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print(f"  Action: {result['action']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Model: {result['model']}")
    print(f"  Tokens Used: {result.get('tokens_used', 0)}")

    if result['success'] and result['action'] == 'approve':
        print("\n✅ PASSED: Halal content correctly identified")
        return True
    elif not result['success']:
        print(f"\n❌ FAILED: API call failed - {result.get('error', 'Unknown error')}")
        return False
    else:
        print(f"\n⚠️  WARNING: Unexpected action '{result['action']}' for halal content")
        return False

def test_haram_content():
    """Test 3: Test with clear haram content"""
    print_separator()
    print("TEST 3: Haram Content Detection")
    print_separator()

    title = "Bartender Needed for Nightclub"
    description = "Experienced bartender needed to mix cocktails and serve alcoholic beverages at our bar."

    print(f"Title: {title}")
    print(f"Description: {description}")
    print("\nSending to Groq API...")

    result = ai_halal_moderation(title, description)

    print(f"\n📊 Result:")
    print(f"  Success: {result['success']}")
    print(f"  Is Halal: {result.get('is_halal', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print(f"  Action: {result['action']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Violations: {result.get('violations', [])}")
    print(f"  Model: {result['model']}")
    print(f"  Tokens Used: {result.get('tokens_used', 0)}")

    if result['success'] and result['action'] in ['reject', 'flag']:
        print("\n✅ PASSED: Haram content correctly detected")
        return True
    elif not result['success']:
        print(f"\n❌ FAILED: API call failed - {result.get('error', 'Unknown error')}")
        return False
    else:
        print(f"\n⚠️  WARNING: Haram content was approved (action: {result['action']})")
        return False

def test_borderline_content():
    """Test 4: Test with borderline content"""
    print_separator()
    print("TEST 4: Borderline Content Detection")
    print_separator()

    title = "Event Photographer Needed"
    description = "Looking for photographer for corporate events and parties. Must be available on weekends."

    print(f"Title: {title}")
    print(f"Description: {description}")
    print("\nSending to Groq API...")

    result = ai_halal_moderation(title, description)

    print(f"\n📊 Result:")
    print(f"  Success: {result['success']}")
    print(f"  Is Halal: {result.get('is_halal', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")
    print(f"  Action: {result['action']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Model: {result['model']}")
    print(f"  Tokens Used: {result.get('tokens_used', 0)}")

    if result['success']:
        print(f"\n✅ PASSED: Borderline content processed (action: {result['action']})")
        return True
    else:
        print(f"\n❌ FAILED: API call failed - {result.get('error', 'Unknown error')}")
        return False

def test_api_health():
    """Test 5: Overall API health check"""
    print_separator()
    print("TEST 5: API Health Check")
    print_separator()

    is_healthy, message = check_groq_api_health()

    print(f"Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    print(f"Message: {message}")

    return is_healthy

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("GROQ API KEY TEST SUITE")
    print("=" * 70)
    print()

    tests_passed = 0
    tests_total = 5

    # Test 1: API Key Configuration
    if test_api_key_configured():
        tests_passed += 1
    else:
        print("\n⚠️  Cannot continue without API key. Please configure GROQ_API_KEY.")
        sys.exit(1)

    print()

    # Test 2: Halal Content
    if test_halal_content():
        tests_passed += 1

    print()

    # Test 3: Haram Content
    if test_haram_content():
        tests_passed += 1

    print()

    # Test 4: Borderline Content
    if test_borderline_content():
        tests_passed += 1

    print()

    # Test 5: Health Check
    if test_api_health():
        tests_passed += 1

    # Summary
    print_separator()
    print("TEST SUMMARY")
    print_separator()
    print(f"Tests Passed: {tests_passed}/{tests_total}")
    print()

    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Groq API integration is working correctly")
        print("✅ AI moderation is ready for production")
    elif tests_passed >= 3:
        print("⚠️  SOME TESTS FAILED")
        print(f"   {tests_passed}/{tests_total} tests passed")
        print("   Review the failures above and check your API key")
    else:
        print("❌ MOST TESTS FAILED")
        print("   Please check:")
        print("   1. GROQ_API_KEY is correct")
        print("   2. API key has valid permissions")
        print("   3. Internet connection is working")
        print("   4. Groq API service is operational")

    print_separator()
    print()

    return tests_passed == tests_total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
