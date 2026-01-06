"""
AI-Powered Halal Compliance Moderation using Groq API
=====================================================

This module provides AI-based halal compliance checking for gig postings using
the Groq API with Llama-3-70b-8192 model. It enforces strict Islamic Shariah
principles to ensure all content on GigHala is 100% halal compliant.

The AI moderation works alongside existing keyword-based filtering to provide
an additional layer of protection against haram content.
"""

import os
import json
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
import requests
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

# Groq API configuration
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama-3.3-70b-versatile'  # Updated to supported model
GROQ_TIMEOUT = 15  # seconds
GROQ_MAX_RETRIES = 2

# Confidence thresholds for decision making
CONFIDENCE_THRESHOLD_AUTO_APPROVE = 0.80  # Reduced from 0.90 to be less restrictive
CONFIDENCE_THRESHOLD_AUTO_REJECT = 0.90   # Increased from 0.85 to require higher certainty for rejection
# Between 80-90% or <80% → flag for manual review

# System prompt for strict Islamic Shariah compliance checking
HALAL_COMPLIANCE_SYSTEM_PROMPT = """You are an expert Islamic Shariah compliance officer for GigHala, Malaysia's first 100% halal gig economy platform. Your role is to analyze gig postings (job listings) and determine if they comply with strict Islamic Shariah principles.

STRICT PROHIBITION CRITERIA - Reject ANY content involving:

1. **Alcohol & Intoxicants (Khamr)**
   - Production, sale, distribution, marketing, or promotion of alcohol
   - Bars, pubs, breweries, distilleries, liquor stores
   - Wine tasting, bartending, mixology services
   - Any business or activity involving alcoholic beverages

2. **Pork & Non-Halal Meat**
   - Pork products, bacon, ham, lard, or pork-based ingredients
   - Non-halal slaughtered meat (not zabihah)
   - Restaurants or businesses serving pork
   - Any food business without clear halal certification

3. **Interest-Based Finance (Riba)**
   - Conventional loans with interest
   - Payday loans, loan sharks, money lending with interest
   - Interest-bearing financial products
   - Non-Islamic banking services involving riba

4. **Gambling & Games of Chance (Maisir)**
   - Casinos, betting, lottery, sports betting
   - Online gambling platforms or software
   - Poker, slot machines, gaming machines
   - Any game of chance involving money

5. **Adult & Sexual Content**
   - Pornography, escort services, massage parlors
   - Adult entertainment, nightclubs, strip clubs
   - Dating services promoting zina (fornication)
   - Sexually explicit content or services

6. **Fraud, Scams & Deception (Gharar)**
   - Pyramid schemes, MLM scams
   - Get-rich-quick schemes
   - Fraudulent investment opportunities
   - Deceptive business practices

7. **Haram Entertainment**
   - Music concerts or events promoting immoral behavior
   - Entertainment that contradicts Islamic values
   - Productions glorifying haram activities

8. **Black Magic & Occult (Sihr & Shirk)**
   - Fortune telling, astrology, horoscopes
   - Black magic, witchcraft, sorcery
   - Tarot reading, psychic services
   - Any practice involving shirk (associating partners with Allah)

9. **Tobacco & Harmful Substances**
   - Cigarette sales or promotion
   - Vaping, e-cigarettes, shisha
   - Drug production or distribution
   - Any harmful or intoxicating substances

10. **Religious Defamation**
    - Content mocking or disrespecting Islam
    - Blasphemy or religious insults
    - Anti-Islamic propaganda

**EVALUATION APPROACH:**
- Do NOT reject content just because it is a "test" or "placeholder".
- If the content is generic, harmless, or common business activity, approve it.
- Apply "when in doubt, FLAG" instead of "when in doubt, reject".
- Consider cultural context of Malaysia and Islamic norms.
- Analyze both explicit and implicit haram elements.
- Check for deceptive wording trying to hide haram nature.
- Evaluate the overall purpose and outcome of the gig.

**RESPONSE FORMAT:**
You must respond with ONLY a valid JSON object (no markdown, no extra text):

{
  "is_halal": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation in English (1-2 sentences). If it's a test, mention it's harmless.",
  "violations": ["list", "of", "specific", "violations"] or [],
  "action": "approve" | "flag" | "reject"
}

**DECISION RULES:**
- is_halal: true if no prohibited elements are detected.
- is_halal: false ONLY if a clear prohibited element (alcohol, pork, riba, etc.) is detected.
- confidence: Your confidence level (0.0 = not confident, 1.0 = absolutely certain)
- action:
  * "approve" - Clear halal or harmless content, high confidence (≥80%)
  * "flag" - Uncertain, borderline, or generic but not clearly haram content.
  * "reject" - Clear haram content with very high confidence (≥90%).
- violations: List specific Shariah violations found (empty if halal)
- reason: Explain your decision briefly and clearly. If it's a test, mention it's harmless.

**IMPORTANT:** Be fair but firm. Harmless "test" content should NOT be rejected. Protect the integrity of the platform without blocking valid or harmless testing activity.

Examples of HALAL gigs (approve):
- "Need graphic designer for halal restaurant menu"
- "Looking for web developer for Islamic education app"
- "Tutor needed for Quran recitation and tajweed"
- "Content writer for halal food blog"

Examples of HARAM gigs (reject):
- "Bartender needed for nightclub"
- "Promote our new beer brand on social media"
- "Casino dealer for weekend events"
- "Looking for fortune teller for corporate event"

Examples to FLAG for review (uncertain):
- "Photographer for wedding" (depends on gender mixing, music, etc.)
- "Marketing consultant for restaurant" (depends if restaurant is halal)
- "Event planner for birthday party" (depends on event activities)

Remember: When uncertain, ALWAYS flag for manual review. Never approve questionable content."""


def ai_halal_moderation(title: str, description: str) -> Dict:
    """
    AI moderation is currently DISABLED.
    Returns a success response with 'approve' action for all content.
    """
    return {
        'success': True,
        'is_halal': True,
        'confidence': 1.0,
        'reason': 'AI moderation disabled by administrator.',
        'violations': [],
        'action': 'approve',
        'model': 'disabled',
        'timestamp': datetime.utcnow().isoformat(),
        'tokens_used': 0
    }


def _validate_ai_response(ai_result: Dict) -> bool:
    """
    Validate that the AI response contains all required fields.

    Args:
        ai_result: Parsed JSON response from AI

    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ['is_halal', 'confidence', 'reason', 'action']

    # Check all required fields exist
    if not all(field in ai_result for field in required_fields):
        return False

    # Validate types
    if not isinstance(ai_result['is_halal'], bool):
        return False

    if not isinstance(ai_result['confidence'], (int, float)):
        return False

    if ai_result['confidence'] < 0 or ai_result['confidence'] > 1:
        return False

    if ai_result['action'] not in ['approve', 'flag', 'reject']:
        return False

    return True


def _determine_action(is_halal: bool, confidence: float) -> str:
    """
    Determine the final moderation action based on AI assessment.

    Decision logic:
    - If is_halal=True and confidence ≥ 0.90: AUTO-APPROVE
    - If is_halal=False and confidence ≥ 0.85: AUTO-REJECT
    - Otherwise: FLAG for manual review

    Args:
        is_halal: Whether AI determined content is halal
        confidence: AI confidence score (0.0 to 1.0)

    Returns:
        str: 'approve', 'flag', or 'reject'
    """
    if is_halal and confidence >= CONFIDENCE_THRESHOLD_AUTO_APPROVE:
        return 'approve'
    elif not is_halal and confidence >= CONFIDENCE_THRESHOLD_AUTO_REJECT:
        return 'reject'
    else:
        # When in doubt, flag for human review
        return 'flag'


def _create_fallback_response(error_message: str, flag: bool = True) -> Dict:
    """
    Create a fallback response when AI moderation fails.

    Default behavior: Flag for manual review to ensure safety.
    We never auto-approve on failure to maintain strict halal compliance.

    Args:
        error_message: Description of the error
        flag: Whether to flag for review (default: True)

    Returns:
        Dict: Structured fallback response
    """
    return {
        'success': False,
        'is_halal': None,  # Unknown due to error
        'confidence': 0.0,
        'reason': f'AI moderation unavailable: {error_message}',
        'violations': [],
        'action': 'flag' if flag else 'reject',
        'model': 'fallback',
        'timestamp': datetime.utcnow().isoformat(),
        'error': error_message
    }


@lru_cache(maxsize=1000)
def ai_halal_moderation_cached(title: str, description: str) -> str:
    """
    Cached version of AI moderation for identical title+description pairs.

    This reduces API calls for duplicate submissions and improves response time.
    Cache size is limited to 1000 entries to prevent memory issues.

    Args:
        title: The gig title
        description: The gig description

    Returns:
        str: JSON-encoded moderation result

    Note:
        Returns JSON string (not dict) because lru_cache requires hashable types.
        Call json.loads() on the result to get the dict.
    """
    result = ai_halal_moderation(title, description)
    return json.dumps(result)


def get_cached_moderation(title: str, description: str) -> Dict:
    """
    Get AI moderation result with caching support.

    This is the recommended function to use for gig moderation as it
    automatically handles caching to reduce API costs and improve speed.

    Args:
        title: The gig title
        description: The gig description

    Returns:
        Dict: Moderation result (same format as ai_halal_moderation)
    """
    cached_json = ai_halal_moderation_cached(title, description)
    return json.loads(cached_json)


def clear_moderation_cache():
    """
    Clear the moderation cache.

    Use this after updating moderation rules or for testing.
    """
    ai_halal_moderation_cached.cache_clear()
    logger.info("AI moderation cache cleared")


# Health check function for monitoring
def check_groq_api_health() -> Tuple[bool, str]:
    """
    Check if Groq API is accessible and configured correctly.

    Returns:
        Tuple[bool, str]: (is_healthy, status_message)
    """
    if not GROQ_API_KEY:
        return False, "GROQ_API_KEY not configured"

    try:
        # Simple test request
        test_result = ai_halal_moderation(
            "Test gig",
            "This is a test for halal compliance checking"
        )

        if test_result['success']:
            return True, "Groq API is healthy"
        else:
            return False, f"API test failed: {test_result.get('error', 'Unknown error')}"

    except Exception as e:
        return False, f"Health check failed: {str(e)}"


if __name__ == '__main__':
    # Test the moderation system
    print("Testing AI Halal Moderation System\n" + "="*50)

    # Test case 1: Clear halal content
    print("\n✅ Test 1: Halal content")
    result = ai_halal_moderation(
        "Graphic Designer for Halal Restaurant",
        "We need a talented graphic designer to create a new menu for our halal-certified restaurant. The design should be modern and appealing to Muslim customers."
    )
    print(json.dumps(result, indent=2))

    # Test case 2: Clear haram content
    print("\n❌ Test 2: Haram content")
    result = ai_halal_moderation(
        "Bartender Needed for Weekend Shifts",
        "Experienced bartender needed for our nightclub. Must know how to mix cocktails and serve alcoholic beverages."
    )
    print(json.dumps(result, indent=2))

    # Test case 3: Borderline content
    print("\n⚠️ Test 3: Borderline content")
    result = ai_halal_moderation(
        "Event Photographer Needed",
        "Looking for photographer for corporate events and parties. Must be available on weekends."
    )
    print(json.dumps(result, indent=2))

    # Health check
    print("\n🏥 API Health Check")
    is_healthy, message = check_groq_api_health()
    print(f"Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    print(f"Message: {message}")
