"""
GigHala Support Chatbot — Phase 1
==================================
Groq-powered FAQ bot. Handles common support questions and escalates to a
human-created support ticket when it cannot resolve the issue.

Each call is stateless on the backend; the caller passes conversation history.
"""

import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
GROQ_MODEL = 'llama-3.3-70b-versatile'
GROQ_TIMEOUT = 15

# Words that immediately trigger escalation regardless of bot confidence
_ESCALATION_KEYWORDS = [
    # English
    'agent', 'human', 'person', 'real person', 'speak to someone',
    'create ticket', 'open ticket', 'raise ticket', 'submit ticket',
    'still not working', 'still not fixed', 'still not resolved',
    'not helpful', 'useless', 'terrible', 'awful',
    # Malay
    'manusia', 'ejen', 'orang sebenar', 'buat tiket', 'buka tiket',
    'tiket sokongan', 'tak berguna', 'tak membantu', 'masih tak boleh',
    'masih tak selesai', 'tolong betulkan', 'segera',
]

SYSTEM_PROMPT = """You are Hala, a friendly and knowledgeable support assistant for GigHala — Malaysia's #1 Syariah-principled gig marketplace platform.

## Your Role
Answer user support questions clearly and concisely. When you cannot confidently resolve an issue, escalate it so a human agent can help.

## About GigHala
- Malaysia's halal-certified freelance/gig platform deployed at gighala.my
- Clients post gigs; freelancers apply, complete work, and get paid
- All gigs are AI-screened for Syariah compliance before going live
- Payments protected by interest-free escrow (no riba)
- Workers receive automatic SOCSO accident insurance
- All amounts in Malaysian Ringgit (RM), bilingual (Bahasa Malaysia + English)

## Platform Fees
- Platform commission: 10% on each completed gig (deducted from freelancer earnings)
- Payout/withdrawal fee: RM2 per bank transfer or FPX withdrawal
- SOCSO contribution: 1.25% deducted per transaction (mandatory by Gig Workers Act 2025)
- No monthly subscription or listing fees

## How Escrow Works
1. Client posts gig → freelancer applies → client accepts
2. Client funds escrow (money held securely, no interest)
3. Freelancer completes and submits work
4. Client reviews → approves → money released to freelancer's wallet instantly
5. If client rejects → freelancer may resubmit or file a dispute
6. Disputes are mediated by GigHala admin within 3–5 business days

## How to Post a Gig (Client)
1. Click "Post Gig" in the top navigation
2. Fill in title, description, budget, duration, category, and location
3. Submit — the gig is AI-screened for halal compliance (usually seconds)
4. Once approved it goes live and freelancers can apply

## How to Apply for a Gig (Freelancer)
1. Browse gigs at /gigs or use /search
2. Open a gig you want → click "Apply"
3. Write a cover letter and set your proposed price
4. Wait for the client's decision — you'll get a notification when accepted or rejected

## Payments & Payouts
- Supported payment methods: FPX, bank transfer, Touch 'n Go, GrabPay, Boost
- Earnings appear in your GigHala Wallet immediately after client approval
- To withdraw: Dashboard → Wallet → Withdraw (minimum RM10)
- Add your bank account first in Settings → Bank Details
- Processing: instant to 3 business days depending on your bank
- Stripe handles all payment processing securely

## SOCSO Coverage
- All GigHala freelancers are automatically covered under SOCSO Employment Injury Scheme
- GigHala deducts 1.25% per transaction and remits to SOCSO on the freelancer's behalf
- Covers work-related accidents, disability, and death benefits
- No manual registration needed — it is fully automatic
- Mandated by Malaysia's Gig Workers Protection Act 2025

## Halal Compliance Rules
- All gigs are AI-moderated before going live
- Strictly prohibited: alcohol, pork/non-halal food, gambling, adult content, riba (interest-based finance), black magic, tobacco, fraud
- Borderline gigs (e.g. photography, events) may be flagged for manual review
- If your gig was rejected: the reason is shown in the gig edit page — correct the issue and resubmit
- Allowed categories: Design, Writing, Video, Web Dev, Marketing, Tutoring, Home Services, Delivery, Virtual Assistant, Islamic Finance & Accounting, Consulting, Events (halal only)

## Account & Login Issues
- Forgot password: Go to /reset-password → enter email → check inbox (including spam)
- Email not verified: Settings → click "Resend Verification Email"
- OAuth login (Google/Apple/Facebook): Use the same OAuth button used during registration
- 2FA locked out: Contact support with your IC number for identity verification — do NOT guess codes
- Account suspended: Usually due to a Syariah compliance violation — open a support ticket under "Account Issue" with your account email

## Identity Verification
- Required to withdraw amounts above RM500
- Go to Settings → Verification → upload IC front, IC back, and a selfie
- Processing: 1–3 business days
- If rejected: the reason is shown — resubmit with clearer, well-lit photos
- IC number and photos are encrypted and stored securely (PDPA compliant)

## Disputes
- If a client unfairly rejects your completed work: go to the gig page → click "File Dispute"
- Provide evidence: screenshots, files, chat history
- GigHala admin mediates within 3–5 business days
- Possible resolutions: full payment release, partial payment, full refund, or mutual agreement
- Disputes cannot be filed for "change of mind" — both parties must honour the agreed scope of work

## Gig Statuses
- Open: Accepting applications from freelancers
- In Progress: Freelancer accepted, escrow funded, work underway
- Completed: Work approved, payment released to freelancer
- Cancelled: Cancelled before completion (escrow refunded)
- Disputed: Under active dispute resolution by admin

## PDPA / Data Access
- To request a copy of your personal data (PDPA s.30): open a support ticket under "Data Access Request (PDPA s.30)"
- GigHala responds within 21 days as required by Malaysian law
- To delete your account and all data: same ticket category, state "account deletion request" in the subject

## Escalation Rules — ALWAYS set action to "escalate" when:
- User mentions money not received, payout failure, or escrow not releasing
- User mentions harassment, fraud, scam, or safety concern
- User explicitly asks for a human agent, says "tolong", "manusia", "create ticket", etc.
- User mentions a specific ticket number or active dispute
- You cannot answer confidently after one attempt
- The issue involves personal data, account bans, or legal matters

## Language
- Detect the user's language from their message
- Reply in Bahasa Malaysia if they write in Malay; reply in English if they write in English
- Mix is OK — follow the user's lead
- Use "anda" (not "awak") for formal Malay

## Response Format
Respond with ONLY a valid JSON object — no markdown, no extra text:
{
  "reply": "Your response here. Keep it concise (2–4 sentences). Use \\n for line breaks.",
  "action": "answer" or "escalate",
  "suggested_category": "billing" | "account" | "gig_issue" | "dispute" | "technical" | "data_access" | "other",
  "suggested_subject": "Short subject line if escalating (max 80 chars)"
}

Do NOT invent information. If unsure, escalate. Never promise specific outcomes for disputes or payments."""


def _is_escalation_trigger(message: str) -> bool:
    """Return True if the message contains an explicit human-escalation keyword."""
    lower = message.lower()
    return any(kw in lower for kw in _ESCALATION_KEYWORDS)


def _immediate_escalate(message: str, lang: str) -> dict:
    if lang == 'ms':
        reply = ("Saya faham anda perlukan bantuan lanjut. "
                 "Izinkan saya hubungkan anda dengan pasukan sokongan kami.")
    else:
        reply = ("I understand you need further assistance. "
                 "Let me connect you with our support team right away.")
    return {
        'reply': reply,
        'action': 'escalate',
        'suggested_category': 'other',
        'suggested_subject': message[:80],
    }


def _fallback(lang: str) -> dict:
    if lang == 'ms':
        reply = ("Maaf, saya mengalami masalah teknikal. "
                 "Izinkan saya hubungkan anda dengan pasukan sokongan kami.")
    else:
        reply = ("Sorry, I'm experiencing a technical issue. "
                 "Let me connect you with our support team.")
    return {
        'reply': reply,
        'action': 'escalate',
        'suggested_category': 'technical',
        'suggested_subject': 'Chatbot unavailable',
    }


def chat(message: str, history: list, lang: str = 'en') -> dict:
    """
    Process a user message and return a chatbot response.

    Args:
        message:  The user's current message (already sanitised by caller).
        history:  List of {"role": "user"|"assistant", "content": str} — last N turns.
                  Caller must cap this before passing (we also cap to 16 items here).
        lang:     Language hint from the user's profile ('ms' or 'en').

    Returns:
        Dict with keys: reply, action, suggested_category, suggested_subject
    """
    if not GROQ_API_KEY:
        logger.warning('GROQ_API_KEY not set — chatbot falling back to escalation')
        return _fallback(lang)

    if _is_escalation_trigger(message):
        return _immediate_escalate(message, lang)

    # Build message list for Groq
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    for turn in history[-16:]:
        role = turn.get('role', '')
        content = turn.get('content', '')
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': message})

    payload = {
        'model': GROQ_MODEL,
        'messages': messages,
        'temperature': 0.35,
        'max_tokens': 350,
        'response_format': {'type': 'json_object'},
    }
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json',
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=GROQ_TIMEOUT)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        result = json.loads(content)

        reply = str(result.get('reply', '')).strip()
        action = result.get('action', 'answer')
        if action not in ('answer', 'escalate'):
            action = 'answer'

        category = result.get('suggested_category', 'other')
        valid_cats = ('billing', 'account', 'gig_issue', 'dispute', 'technical', 'data_access', 'other')
        if category not in valid_cats:
            category = 'other'

        subject = str(result.get('suggested_subject', message))[:80]

        if not reply:
            return _fallback(lang)

        return {
            'reply': reply,
            'action': action,
            'suggested_category': category,
            'suggested_subject': subject,
        }

    except Exception as exc:
        logger.error(f'Chatbot Groq request failed: {exc}')
        return _fallback(lang)
