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
    Perform AI-powered halal compliance moderation on gig content.

    This function sends the gig title and description to the Groq API using
    the Llama-3-70b-8192 model to evaluate against strict Islamic Shariah
    principles. It provides an additional layer of protection beyond keyword
    filtering.

    Args:
        title: The gig title (max 200 characters)
        description: The gig description (full text)

    Returns:
        Dict containing:
        - is_halal (bool): Whether the content is halal compliant
        - confidence (float): AI confidence score (0.0 to 1.0)
        - reason (str): Explanation of the decision
        - violations (list): List of specific Shariah violations found
        - action (str): Recommended action ('approve', 'flag', or 'reject')
        - model (str): AI model used
        - timestamp (str): ISO timestamp of the check
        - success (bool): Whether the API call succeeded
        - error (str, optional): Error message if failed

    Example:
        >>> result = ai_halal_moderation(
        ...     "Bartender needed",
        ...     "Looking for experienced bartender for nightclub"
        ... )
        >>> result['is_halal']
        False
        >>> result['action']
        'reject'
    """

    # Input validation
    if not title or not description:
        logger.warning("AI moderation called with empty title or description")
        return _create_fallback_response(
            "Empty title or description provided",
            flag=True
        )

    # Fast-track harmless "test" content to avoid false positives
    test_keywords = ["live test", "test live", "testing purposes only", "test gig"]
    combined_text = (title + " " + description).lower()
    if any(keyword in combined_text for keyword in test_keywords):
        logger.info(f"Auto-approving harmless test content: {title}")
        return {
            'success': True,
            'is_halal': True,
            'confidence': 1.0,
            'reason': 'Harmeless test or placeholder content identified.',
            'violations': [],
            'action': 'approve',
            'model': 'heuristic-check',
            'timestamp': datetime.utcnow().isoformat(),
            'tokens_used': 0
        }

    # Check if API key is configured
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY environment variable not set")
        return _create_fallback_response(
            "AI moderation unavailable - missing API configuration",
            flag=True
        )

    # Prepare the user prompt with gig content
    user_prompt = f"""Analyze this gig posting for halal compliance:

**Title:** {title}

**Description:** {description}

Evaluate against Islamic Shariah principles and respond with JSON only."""

    # Prepare API request
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': GROQ_MODEL,
        'messages': [
            {
                'role': 'system',
                'content': HALAL_COMPLIANCE_SYSTEM_PROMPT
            },
            {
                'role': 'user',
                'content': user_prompt
            }
        ],
        'temperature': 0.1,  # Low temperature for consistent, strict evaluation
        'max_tokens': 500,   # Enough for detailed response
        'top_p': 0.9,
    }

    # Attempt API call with retries
    last_error = None
    for attempt in range(GROQ_MAX_RETRIES + 1):
        try:
            logger.info(f"AI moderation attempt {attempt + 1}/{GROQ_MAX_RETRIES + 1} for gig: {title[:50]}")

            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=GROQ_TIMEOUT
            )

            # Check for HTTP errors
            if response.status_code == 401:
                logger.error("Groq API authentication failed - invalid API key")
                return _create_fallback_response(
                    "AI moderation authentication failed",
                    flag=True
                )

            if response.status_code == 429:
                logger.warning("Groq API rate limit exceeded")
                if attempt < GROQ_MAX_RETRIES:
                    continue  # Retry
                return _create_fallback_response(
                    "AI moderation rate limit exceeded",
                    flag=True
                )

            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if response is not None and response.status_code == 400:
                logger.error(f"Groq API Bad Request (400): {response.text}")
                return _create_fallback_response(
                    f"AI moderation API error (400): {response.text}",
                    flag=True
                )
            raise e

        try:
            # Parse response
            if response is None:
                raise ValueError("Response is None")
            response_data = response.json()
            ai_response_text = response_data['choices'][0]['message']['content']

            # Parse AI's JSON response
            ai_result = json.loads(ai_response_text)

            # Validate response structure
            if not _validate_ai_response(ai_result):
                logger.error(f"Invalid AI response structure: {ai_result}")
                return _create_fallback_response(
                    "AI returned invalid response format",
                    flag=True
                )

            # Determine final action based on confidence and compliance
            final_action = _determine_action(
                ai_result['is_halal'],
                ai_result['confidence']
            )

            # Build structured response
            result = {
                'success': True,
                'is_halal': ai_result['is_halal'],
                'confidence': float(ai_result['confidence']),
                'reason': ai_result.get('reason', 'No reason provided'),
                'violations': ai_result.get('violations', []),
                'action': final_action,
                'model': GROQ_MODEL,
                'timestamp': datetime.utcnow().isoformat(),
                'tokens_used': response_data.get('usage', {}).get('total_tokens', 0)
            }

            logger.info(
                f"AI moderation success: action={final_action}, "
                f"is_halal={result['is_halal']}, "
                f"confidence={result['confidence']:.2f}"
            )

            return result

        except requests.exceptions.Timeout:
            last_error = "API request timeout"
            logger.warning(f"Groq API timeout on attempt {attempt + 1}")

        except requests.exceptions.ConnectionError:
            last_error = "Network connection error"
            logger.warning(f"Network error on attempt {attempt + 1}")

        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON response: {str(e)}"
            logger.error(f"Failed to parse AI response: {e}")

        except KeyError as e:
            last_error = f"Missing expected field in response: {str(e)}"
            logger.error(f"Unexpected response structure: {e}")

        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error in AI moderation: {e}", exc_info=True)

    # All retries failed - return fallback
    logger.error(f"AI moderation failed after {GROQ_MAX_RETRIES + 1} attempts: {last_error}")
    return _create_fallback_response(str(last_error) if last_error else "Unknown error", flag=True)


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
