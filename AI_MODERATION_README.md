# AI-Powered Halal Moderation for GigHala

## Overview

GigHala now features an advanced AI-powered moderation system that uses **Groq AI** with the **Llama-3.1-70b-versatile** model to enforce strict Islamic Shariah compliance. This system provides an additional layer of protection beyond keyword-based filtering to ensure all gig postings are 100% halal compliant.

### Key Features

✅ **Real-time AI Analysis** - Instant feedback as users type their gig content
✅ **Strict Shariah Compliance** - Enforces Islamic principles (no alcohol, pork, riba, gambling, etc.)
✅ **Multi-layer Protection** - Combines keyword filtering + AI analysis
✅ **Auto-moderation** - Automatically approves, flags, or rejects based on confidence levels
✅ **Admin Review Dashboard** - Manual review workflow for flagged content
✅ **Audit Trail** - Complete logging of all AI decisions for transparency
✅ **Caching** - Reduces API costs by caching identical content checks

---

## Architecture

### Flow Diagram

```
User submits gig
    ↓
1. Keyword-based validation (halal_compliance.py)
    ├─ ❌ Fails → Reject immediately
    └─ ✅ Passes → Continue to AI check
    ↓
2. AI-powered moderation (groq_moderation.py)
    ├─ Analyze title + description
    ├─ Call Groq API (Llama-3.1-70b-versatile)
    └─ Return: is_halal, confidence, reason, action
    ↓
3. Decision Engine
    ├─ action='approve' (confidence ≥90%) → Status: open
    ├─ action='flag' (uncertain) → Status: pending_review
    └─ action='reject' (confidence ≥85%, haram) → Block submission
    ↓
4. Admin Review (if flagged)
    ├─ Admin views flagged gigs
    ├─ Reviews AI reasoning
    └─ Approves or rejects manually
```

---

## Components

### 1. Backend: Groq AI Moderation Service

**File:** `groq_moderation.py`

**Key Functions:**

- `ai_halal_moderation(title, description)` - Main AI moderation function
- `get_cached_moderation(title, description)` - Cached version (recommended)
- `check_groq_api_health()` - Health check for monitoring

**AI Decision Logic:**

| is_halal | Confidence | Action | Description |
|----------|-----------|--------|-------------|
| `true` | ≥ 90% | `approve` | Auto-approve, gig goes live |
| `true` | < 90% | `flag` | Send for admin review |
| `false` | ≥ 85% | `reject` | Auto-reject, block submission |
| `false` | < 85% | `flag` | Send for admin review |

**System Prompt:**

The AI uses a comprehensive system prompt that evaluates content against strict Islamic Shariah principles:

- ❌ **Prohibited Content:**
  - Alcohol & intoxicants (khamr)
  - Pork & non-halal meat
  - Interest-based finance (riba)
  - Gambling & games of chance (maisir)
  - Adult & sexual content
  - Fraud, scams & deception (gharar)
  - Haram entertainment
  - Black magic & occult (sihr & shirk)
  - Tobacco & harmful substances
  - Religious defamation

- 🔍 **Evaluation Approach:**
  - "When in doubt, reject or flag" principle
  - Considers cultural context of Malaysia
  - Analyzes explicit and implicit haram elements
  - Checks for deceptive wording

### 2. Database Schema

**New Field Added to `gig` Table:**

```sql
ai_moderation_result TEXT  -- JSON result from AI check
```

**Structure of `ai_moderation_result` JSON:**

```json
{
  "success": true,
  "is_halal": true,
  "confidence": 0.95,
  "reason": "Content appears to be halal-compliant",
  "violations": [],
  "action": "approve",
  "model": "llama-3.1-70b-versatile",
  "timestamp": "2026-01-04T12:34:56.789Z",
  "tokens_used": 245
}
```

**Migration:**

Run the migration to add the new field:

```bash
# PostgreSQL
python migrations/048_add_ai_moderation.py

# Or manually
ALTER TABLE gig ADD COLUMN ai_moderation_result TEXT;
```

### 3. API Endpoints

#### Real-time Compliance Check (Frontend)

```
POST /api/check-halal-compliance
```

**Request:**
```json
{
  "title": "Gig title",
  "description": "Gig description",
  "category": "design",
  "skills": "photoshop graphic-design"
}
```

**Response:**
```json
{
  "is_halal": true,
  "action": "approve",
  "reason": "Content meets Islamic Shariah requirements",
  "confidence": 0.92,
  "keyword_check": {
    "is_compliant": true,
    "violations": []
  },
  "ai_check": {
    "is_halal": true,
    "confidence": 0.92,
    "reason": "...",
    "violations": [],
    "action": "approve",
    "model": "llama-3.1-70b-versatile",
    "success": true
  }
}
```

#### Admin: Get AI-Flagged Gigs

```
GET /api/admin/ai-flagged-gigs?action=flag&page=1&per_page=50
```

**Query Parameters:**
- `action`: `flag`, `reject`, or `all` (default: `flag`)
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50)

**Response:**
```json
{
  "gigs": [
    {
      "id": 123,
      "gig_code": "GIG-00123",
      "title": "...",
      "description": "...",
      "category": "design",
      "status": "pending_review",
      "client_name": "John Doe",
      "client_email": "john@example.com",
      "created_at": "2026-01-04T12:00:00",
      "ai_moderation": {
        "action": "flag",
        "is_halal": null,
        "confidence": 0.75,
        "reason": "Content may need verification",
        "violations": [],
        "model": "llama-3.1-70b-versatile",
        "timestamp": "2026-01-04T12:00:05"
      },
      "report_count": 0,
      "views": 5,
      "applications": 0
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 50,
  "pages": 1
}
```

#### Admin: Approve Flagged Gig

```
POST /api/admin/ai-flagged-gigs/{gig_id}/approve
```

**Request:**
```json
{
  "notes": "Reviewed manually - content is halal compliant"
}
```

**Response:**
```json
{
  "message": "Gig approved successfully",
  "gig_id": 123,
  "new_status": "open"
}
```

#### Admin: Reject Flagged Gig

```
POST /api/admin/ai-flagged-gigs/{gig_id}/reject
```

**Request:**
```json
{
  "reason": "Contains prohibited content",
  "notes": "References non-halal business activities"
}
```

**Response:**
```json
{
  "message": "Gig rejected successfully",
  "gig_id": 123,
  "new_status": "blocked"
}
```

### 4. Frontend: Real-time Feedback

**File:** `templates/post_gig.html`

**Features:**

- 🔍 **Debounced checking** - Waits 1.5 seconds after user stops typing
- 🎨 **Visual status badges** - Color-coded feedback (green/yellow/red)
- 📊 **Confidence display** - Shows AI confidence percentage
- ⚠️ **Violation details** - Lists specific Shariah violations if found
- 🌐 **Bilingual** - English and Malay messages

**Status Badge States:**

| Status | Icon | Color | Meaning |
|--------|------|-------|---------|
| Checking | 🔍 | Gray | AI is analyzing content |
| Approved | ✅ | Green | Halal-compliant, ready to submit |
| Flagged | ⚠️ | Yellow | Needs admin review |
| Rejected | ❌ | Red | Contains haram elements |

**User Experience:**

1. User types gig title and description
2. Badge appears: "Checking halal compliance..."
3. After 1.5 seconds (debounced):
   - API call to `/api/check-halal-compliance`
   - Badge updates with result
4. If rejected: User must revise content before submitting
5. If flagged: Submission succeeds but goes to admin review
6. If approved: Green checkmark, can submit immediately

---

## Setup & Configuration

### 1. Get Groq API Key

1. Visit [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account
3. Generate an API key
4. Copy the key (starts with `gsk_...`)

### 2. Configure Environment Variable

Add to your `.env` file:

```bash
GROQ_API_KEY=gsk_your-actual-groq-api-key-here
```

### 3. Install Dependencies

Already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

The AI moderation uses the `requests` library (already included) - no additional packages needed!

### 4. Run Database Migration

```bash
python migrations/048_add_ai_moderation.py
```

Or manually:

```sql
ALTER TABLE gig ADD COLUMN ai_moderation_result TEXT;
```

### 5. Restart Flask Application

```bash
# Development
python app.py

# Production (with gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 6. Test the System

**Manual Test:**

```bash
python groq_moderation.py
```

This runs built-in test cases:
- ✅ Halal content (should approve)
- ❌ Haram content (should reject)
- ⚠️ Borderline content (should flag)

**Health Check:**

```python
from groq_moderation import check_groq_api_health

is_healthy, message = check_groq_api_health()
print(f"API Status: {message}")
```

---

## Usage Guide

### For Users (Posting Gigs)

1. **Navigate to "Post Gig"** page
2. **Fill in title and description** as usual
3. **Watch for real-time feedback:**
   - ✅ Green badge: Your gig is halal-compliant!
   - ⚠️ Yellow badge: Your gig will be reviewed by admin
   - ❌ Red badge: Contains prohibited content - please revise

4. **If rejected:**
   - Read the AI reason carefully
   - Review the violations listed
   - Modify your content to remove haram elements
   - Wait for the badge to update

5. **Submit your gig:**
   - Approved gigs go live immediately
   - Flagged gigs wait for admin review
   - You'll be notified of the outcome

### For Admins (Reviewing Flagged Gigs)

1. **Access Admin Dashboard:**
   - Navigate to `/api/admin/ai-flagged-gigs`
   - Filter by action: `flag`, `reject`, or `all`

2. **Review Each Flagged Gig:**
   - Read the title, description, and category
   - Check AI reasoning and violations
   - Review confidence score
   - Consider cultural and business context

3. **Make Decision:**
   - **Approve:** Gig goes live, status changes to `open`
   - **Reject:** Gig is blocked, client is notified

4. **Add Notes:**
   - Document your reasoning
   - Helps improve future AI decisions
   - Creates audit trail

---

## API Cost & Performance

### Groq API Pricing

- **Free Tier:** 14,400 requests/day (~10 requests/minute)
- **Cost:** $0 for free tier, very affordable for paid plans
- **Speed:** ~2-5 seconds per request (Llama-3.1-70b-versatile)

### Optimization Features

**1. Caching:**
```python
# Identical title+description pairs are cached
result = get_cached_moderation(title, description)
```

**2. Debouncing (Frontend):**
- Waits 1.5 seconds after user stops typing
- Prevents excessive API calls

**3. Smart Filtering:**
- Keyword check first (free, instant)
- AI check only if keywords pass
- Skips AI check for very short content (<10 chars)

### Estimated Usage

| Users/Day | Gig Posts/Day | AI Checks/Day | Cost/Month (est.) |
|-----------|---------------|---------------|-------------------|
| 100 | 20 | 20 | FREE |
| 500 | 100 | 100 | FREE |
| 1,000 | 200 | 200 | FREE |
| 5,000 | 1,000 | 1,000 | ~$5-10 |

**Note:** With caching, duplicate content is checked only once!

---

## Error Handling & Fallbacks

### Graceful Degradation

If AI moderation fails (API down, timeout, etc.), the system:

1. ✅ **Logs the error** for debugging
2. 🔄 **Falls back to "flag for review"** (safe default)
3. ✅ **Still creates the gig** (status: `pending_review`)
4. 👤 **Admin reviews manually**

### Error Response Example

```json
{
  "success": false,
  "is_halal": null,
  "confidence": 0.0,
  "reason": "AI moderation unavailable: API timeout",
  "violations": [],
  "action": "flag",
  "model": "fallback",
  "timestamp": "2026-01-04T12:00:00",
  "error": "API request timeout"
}
```

### Retry Logic

The system automatically retries failed API calls:

- **Max retries:** 2
- **Timeout:** 15 seconds
- **Fallback:** Flag for manual review

---

## Security & Privacy

### Data Protection

✅ **No data stored by Groq:** Only title and description are sent
✅ **Encrypted in transit:** HTTPS for all API calls
✅ **Audit logging:** All AI decisions are logged
✅ **Admin oversight:** Humans can override AI decisions

### Security Best Practices

1. **Restrict API Key:**
   - Store in environment variables only
   - Never commit to version control
   - Rotate periodically

2. **Rate Limiting:**
   - Frontend: Debounced (1.5s delay)
   - Backend: 60 requests/minute per user

3. **Input Validation:**
   - Sanitize all inputs
   - Max length enforcement
   - SQL injection prevention

4. **Audit Trail:**
   - All AI decisions logged to `security_audit_log`
   - Admin actions logged
   - Timestamped and traceable

---

## Monitoring & Maintenance

### Health Checks

```python
from groq_moderation import check_groq_api_health

# Returns: (is_healthy: bool, message: str)
is_healthy, message = check_groq_api_health()

if not is_healthy:
    # Alert admins, log to monitoring system
    print(f"⚠️ AI Moderation Down: {message}")
```

### Key Metrics to Monitor

1. **AI Moderation Success Rate**
   ```sql
   SELECT
     COUNT(*) FILTER (WHERE ai_moderation_result::jsonb->>'success' = 'true') * 100.0 / COUNT(*) as success_rate
   FROM gig
   WHERE ai_moderation_result IS NOT NULL;
   ```

2. **Flagged Gigs Pending Review**
   ```sql
   SELECT COUNT(*)
   FROM gig
   WHERE status = 'pending_review';
   ```

3. **Average Confidence Score**
   ```sql
   SELECT AVG((ai_moderation_result::jsonb->>'confidence')::float) as avg_confidence
   FROM gig
   WHERE ai_moderation_result IS NOT NULL;
   ```

4. **Action Distribution**
   ```sql
   SELECT
     ai_moderation_result::jsonb->>'action' as action,
     COUNT(*) as count
   FROM gig
   WHERE ai_moderation_result IS NOT NULL
   GROUP BY action;
   ```

### Clear Cache (if needed)

```python
from groq_moderation import clear_moderation_cache

clear_moderation_cache()
print("✅ AI moderation cache cleared")
```

---

## Troubleshooting

### Problem: "GROQ_API_KEY not configured"

**Solution:**
1. Check `.env` file exists
2. Verify `GROQ_API_KEY=gsk_...` is present
3. Restart Flask application
4. Test: `echo $GROQ_API_KEY`

### Problem: "AI moderation timeout"

**Solution:**
1. Check internet connectivity
2. Verify Groq API status: [https://status.groq.com](https://status.groq.com)
3. Increase timeout in `groq_moderation.py`:
   ```python
   GROQ_TIMEOUT = 30  # Increase to 30 seconds
   ```

### Problem: "Rate limit exceeded"

**Solution:**
1. Implement stricter frontend debouncing
2. Increase cache size:
   ```python
   @lru_cache(maxsize=5000)  # Increase from 1000
   ```
3. Upgrade to paid Groq plan

### Problem: "Too many false positives"

**Solution:**
1. Adjust confidence thresholds in `groq_moderation.py`:
   ```python
   CONFIDENCE_THRESHOLD_AUTO_APPROVE = 0.85  # Lower from 0.90
   CONFIDENCE_THRESHOLD_AUTO_REJECT = 0.90   # Raise from 0.85
   ```
2. Refine system prompt for Malaysian context
3. Train admins to provide feedback for edge cases

### Problem: "Database column doesn't exist"

**Solution:**
```bash
python migrations/048_add_ai_moderation.py
```

Or manually:
```sql
ALTER TABLE gig ADD COLUMN IF NOT EXISTS ai_moderation_result TEXT;
```

---

## Customization

### Adjust Confidence Thresholds

Edit `groq_moderation.py`:

```python
# Current defaults
CONFIDENCE_THRESHOLD_AUTO_APPROVE = 0.90  # More strict (90%)
CONFIDENCE_THRESHOLD_AUTO_REJECT = 0.85   # High confidence needed to auto-reject

# For more lenient moderation:
CONFIDENCE_THRESHOLD_AUTO_APPROVE = 0.80  # Auto-approve at 80%
CONFIDENCE_THRESHOLD_AUTO_REJECT = 0.95   # Only auto-reject at 95%

# For stricter moderation:
CONFIDENCE_THRESHOLD_AUTO_APPROVE = 0.95  # Require 95% to auto-approve
CONFIDENCE_THRESHOLD_AUTO_REJECT = 0.75   # Reject at 75% if haram
```

### Modify System Prompt

Edit the `HALAL_COMPLIANCE_SYSTEM_PROMPT` in `groq_moderation.py` to:
- Add Malaysian-specific context
- Include more prohibited categories
- Adjust strictness level
- Change language or tone

### Change AI Model

Switch to a different Groq model:

```python
# In groq_moderation.py
GROQ_MODEL = 'llama-3.1-70b-versatile'  # Current (balanced)
# Or:
GROQ_MODEL = 'llama-3.1-8b-instant'     # Faster, cheaper, less accurate
GROQ_MODEL = 'mixtral-8x7b-32768'       # Alternative model
```

---

## Testing

### Unit Tests

```bash
# Test AI moderation module
python groq_moderation.py
```

Expected output:
```
Testing AI Halal Moderation System
==================================================

✅ Test 1: Halal content
{
  "is_halal": true,
  "action": "approve",
  "confidence": 0.95,
  ...
}

❌ Test 2: Haram content
{
  "is_halal": false,
  "action": "reject",
  "confidence": 0.98,
  "violations": ["alcohol", "nightclub"],
  ...
}

⚠️ Test 3: Borderline content
{
  "is_halal": null,
  "action": "flag",
  "confidence": 0.65,
  ...
}

🏥 API Health Check
Status: ✅ Healthy
Message: Groq API is healthy
```

### Integration Test

1. Create test gig with halal content
2. Verify AI approval (status: `open`)
3. Create test gig with haram content
4. Verify AI rejection (blocked)
5. Create borderline gig
6. Verify flagging (status: `pending_review`)
7. Admin approves flagged gig
8. Verify status changes to `open`

---

## Production Deployment

### Pre-deployment Checklist

- [ ] ✅ GROQ_API_KEY set in production environment
- [ ] ✅ Database migration applied
- [ ] ✅ Dependencies installed (`pip install -r requirements.txt`)
- [ ] ✅ Health check passing
- [ ] ✅ Test cases passing
- [ ] ✅ Admin accounts configured
- [ ] ✅ Monitoring alerts set up
- [ ] ✅ Cache size appropriate for traffic
- [ ] ✅ Rate limits configured
- [ ] ✅ Error logging enabled
- [ ] ✅ Backup GROQ_API_KEY stored securely

### Deployment Steps

```bash
# 1. Pull latest code
git pull origin main

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migration
python migrations/048_add_ai_moderation.py

# 5. Set environment variable
export GROQ_API_KEY=gsk_your-actual-key-here

# 6. Restart application
sudo systemctl restart gighala

# 7. Verify health
curl http://localhost:5000/api/check-halal-compliance \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","description":"Halal test gig"}'
```

---

## Future Enhancements

### Planned Features

1. **Multi-language Support**
   - Analyze Malay, Arabic, English content
   - Translate violations to user's language

2. **Confidence Tuning**
   - Machine learning to improve thresholds
   - A/B testing for optimal accuracy

3. **Image Analysis**
   - Scan uploaded gig photos for haram content
   - Detect logos, text in images

4. **Batch Moderation**
   - Re-analyze all existing gigs
   - Find legacy haram content

5. **AI Feedback Loop**
   - Track admin overrides
   - Fine-tune prompts based on patterns

6. **Performance Optimization**
   - Redis caching for distributed systems
   - Background async processing

7. **Advanced Analytics**
   - Dashboard showing AI accuracy
   - Trends in violation types
   - Client education suggestions

---

## Support & Contact

For questions or issues with AI moderation:

- **GitHub Issues:** [hamkasu/GigHala/issues](https://github.com/hamkasu/GigHala/issues)
- **Documentation:** This file + inline code comments
- **Email:** support@gighala.com

---

## License

This AI moderation system is part of GigHala and follows the same license.

**Important:** The Groq API is subject to [Groq's Terms of Service](https://groq.com/terms/).

---

## Acknowledgments

- **Groq AI** for providing fast, affordable LLM inference
- **Meta AI** for the Llama 3.1 model
- **Islamic Scholars** consulted for Shariah compliance guidelines
- **GigHala Community** for feedback and testing

---

## Appendix: Example AI Responses

### Approved Gig

**Input:**
```
Title: Graphic Designer for Halal Restaurant Menu
Description: We need a talented graphic designer to create a modern, appealing menu for our halal-certified restaurant. The design should reflect Islamic aesthetics and appeal to Muslim customers.
```

**AI Response:**
```json
{
  "is_halal": true,
  "confidence": 0.96,
  "reason": "The gig is for designing a menu for a halal-certified restaurant, which is completely permissible in Islam. There are no prohibited elements.",
  "violations": [],
  "action": "approve"
}
```

### Rejected Gig

**Input:**
```
Title: Bartender Needed for Weekend Shifts
Description: Experienced bartender needed for our nightclub. Must know how to mix cocktails and serve alcoholic beverages.
```

**AI Response:**
```json
{
  "is_halal": false,
  "confidence": 0.99,
  "reason": "This gig involves serving alcohol at a nightclub, which is strictly prohibited (haram) in Islam.",
  "violations": [
    "Alcohol service",
    "Nightclub employment",
    "Promotion of intoxicants"
  ],
  "action": "reject"
}
```

### Flagged Gig

**Input:**
```
Title: Event Photographer Needed
Description: Looking for photographer for corporate events and parties. Must be available on weekends.
```

**AI Response:**
```json
{
  "is_halal": null,
  "confidence": 0.70,
  "reason": "While photography is generally permissible, the nature of the events (parties) needs clarification to ensure they don't involve haram activities like alcohol or inappropriate mixing.",
  "violations": [],
  "action": "flag"
}
```

---

**End of Documentation** 🎉

*Last Updated: January 4, 2026*
*Version: 1.0*
