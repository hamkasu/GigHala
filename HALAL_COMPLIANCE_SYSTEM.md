# GigHala Halal Compliance System

## 📋 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Implementation Components](#implementation-components)
- [Validation Rules](#validation-rules)
- [API Integration](#api-integration)
- [Frontend Implementation](#frontend-implementation)
- [Admin Controls](#admin-controls)
- [Testing & Verification](#testing--verification)
- [Future Enhancements](#future-enhancements)

---

## Overview

**GigHala** is a **strictly halal-certified gig economy platform** serving the Muslim community in Malaysia. The Halal Compliance System ensures that **ONLY** halal-compliant gigs are posted on the platform, protecting users from inadvertently participating in haram activities.

### Islamic Principles
- **Better to reject borderline cases** than allow potentially haram content
- Protect users from haram activities
- Maintain platform integrity as a trusted halal marketplace
- Serve the Muslim community with confidence

### Key Features
✅ **Predefined Halal-Approved Categories** - 29 vetted categories
✅ **Prohibited Keyword Detection** - 200+ haram keywords in Malay & English
✅ **Multi-Layer Validation** - Frontend + Backend + API enforcement
✅ **Mandatory Halal Certification** - Required checkbox on gig submission
✅ **Security Audit Logging** - Track all violation attempts
✅ **Admin Verification System** - Manual review for edge cases

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   USER SUBMITS GIG                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│            FRONTEND VALIDATION (JavaScript)                 │
│  • Halal checkbox mandatory                                 │
│  • Client-side keyword checking                             │
│  • Category restriction                                     │
│  • Real-time feedback                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│            BACKEND VALIDATION (Flask/Python)                │
│  • Comprehensive keyword detection (200+ keywords)          │
│  • Category whitelist enforcement                           │
│  • Multi-field validation (title, description, skills)      │
│  • Security logging                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATABASE STORAGE                           │
│  • halal_compliant: boolean (user-declared)                 │
│  • halal_verified: boolean (admin-verified)                 │
│  • Audit logs in security_events table                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              ADMIN REVIEW (Optional)                        │
│  • Manual verification for edge cases                       │
│  • Set halal_verified flag                                  │
│  • Review violation logs                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Components

### 1. **halal_compliance.py** - Core Validation Module

**Location:** `/home/user/GigHala/halal_compliance.py`

**Purpose:**
Centralized module containing all halal compliance logic, constants, and validation functions.

**Key Components:**

#### A. Halal-Approved Categories (29 Categories)
```python
HALAL_APPROVED_CATEGORIES = [
    {
        'slug': 'design',
        'name_en': 'Graphic Design',
        'name_ms': 'Reka Bentuk Grafik',
        'description_en': 'Logo design, branding, flyers (halal content only)',
        'description_ms': 'Reka bentuk logo, jenama, risalah (kandungan halal sahaja)',
        'icon': '🎨'
    },
    # ... 28 more categories
]
```

**Full Category List:**
1. 🎨 Graphic Design / Reka Bentuk Grafik
2. ✍️ Writing & Translation / Penulisan & Terjemahan
3. 🎬 Video & Animation / Video & Animasi
4. 📚 Tutoring & Education / Pengajaran & Pendidikan
5. 📱 Content Creation / Penciptaan Kandungan
6. 💻 Web Development / Pembangunan Web
7. ⚙️ Programming & Tech / Pengaturcaraan & Teknologi
8. 📈 Digital Marketing / Pemasaran Digital
9. 📋 Admin & Customer Support / Admin & Sokongan Pelanggan
10. 🚗 Delivery Services / Perkhidmatan Penghantaran
11. 🧹 Cleaning Services / Khidmat Pembersihan
12. 🔧 Handyman & Repairs / Tukang & Pembaikan
13. 📷 Photography & Videography / Fotografi & Videografi
14. 💼 Business Consulting / Perundingan Perniagaan
15. 🎯 Coaching & Mentoring / Bimbingan & Mentoring
16. 🎉 Event Planning / Perancangan Acara
17. 📊 Data Entry & Research / Kemasukan Data & Penyelidikan
18. 🎨 Arts & Crafts / Seni & Kraf
19. 🎵 Music & Audio / Muzik & Audio (Islamic content only)
20. 👨‍⚕️ Caregiving & Nursing / Penjagaan & Kejururawatan
21. 🐱 Pet Care / Penjagaan Haiwan (halal pets only)
22. 🌱 Gardening & Landscaping / Berkebun & Landskap
23. 💰 Accounting & Bookkeeping / Perakaunan & Simpan Kira (NO riba)
24. 🧳 Tour Guide & Travel / Pemandu Pelancong & Pelancongan
25. 🛒 Online Selling & E-commerce / Jualan Online & E-dagang (halal products)
26. 💼 Virtual Assistant / Pembantu Maya
27. ✅ Micro-Tasks / Tugas Mikro
28. 📐 Engineering & CAD / Kejuruteraan & CAD
29. 🎭 Other Creative Services / Perkhidmatan Kreatif Lain

#### B. Prohibited Keywords (200+ Keywords)

Organized by category with bilingual support (Malay & English):

**Categories:**
- **Alcohol & Intoxicants** (الخمر): alcohol, beer, wine, whiskey, vodka, rum, arak, tuak, etc.
- **Gambling & Betting** (القمار): gambling, judi, casino, betting, lottery, poker, 4D, etc.
- **Pork & Pig-Related** (الخنزير): pork, babi, pig, ham, bacon, char siew, etc.
- **Adult & Sexual Content** (الفاحشة): porn, escort, prostitution, xxx, nude, etc.
- **Interest & Usury** (الربا): interest, faedah, riba, loan shark, along, etc.
- **Fraud & Scams** (الغش): scam, fraud, ponzi, pyramid scheme, money game, etc.
- **Drugs & Narcotics** (المخدرات): drugs, dadah, marijuana, cocaine, heroin, syabu, etc.
- **Tobacco** (التبغ): cigarette, rokok, tobacco, vape, shisha, etc.
- **Religious Defamation**: blasphemy, anti-islam, islamophobia, etc.
- **Black Magic & Occult** (السحر): black magic, sihir, bomoh, fortune telling, tarot, etc.
- **Other Haram**: dating service, valentine, tattoo, body piercing, etc.

#### C. Validation Functions

##### `validate_gig_halal_compliance(title, description, category, skills)`
**Main validation function** - Comprehensive check of all gig fields.

**Returns:**
```python
(is_compliant: bool, validation_result: dict)

# validation_result structure:
{
    'is_compliant': bool,
    'errors': List[str],
    'violations': {
        'category': bool,
        'title': List[str],
        'description': List[str],
        'skills': List[str]
    },
    'message_en': str,
    'message_ms': str
}
```

**Example Usage:**
```python
is_halal, result = validate_gig_halal_compliance(
    title="Need help delivering beer to party",
    description="Looking for someone to deliver alcohol",
    category="delivery",
    skills="driving, delivery"
)

# Result:
# is_halal = False
# result['violations']['title'] = ['beer']
# result['violations']['description'] = ['alcohol']
```

##### `check_prohibited_keywords(text)`
**Keyword detection function** - Scans text for prohibited content.

**Features:**
- Case-insensitive matching
- Word boundary detection (avoids false positives)
- Regex-based pattern matching

**Returns:**
```python
(is_compliant: bool, violations: List[str])
```

##### `validate_category(category)`
**Category validation** - Ensures category is in approved list.

**Returns:**
```python
(is_valid: bool, error_message: str)
```

---

### 2. **Backend Integration (app.py)**

**Location:** `/home/user/GigHala/app.py`

**Modified Endpoints:**

#### A. `/post-gig` (Line ~2956)
**Form-based gig creation endpoint**

**Validation Flow:**
1. Sanitize all inputs
2. Validate budget and deadline
3. **🔒 HALAL COMPLIANCE CHECK** (Line 3041-3072)
4. Create gig if validation passes
5. Log violations if validation fails

**Code:**
```python
# HALAL COMPLIANCE VALIDATION
skills_text = ' '.join(skills_required) if skills_required else ''
is_halal_compliant, halal_result = validate_gig_halal_compliance(
    title=title,
    description=description,
    category=category,
    skills=skills_text
)

if not is_halal_compliant:
    # Log violation
    log_security_event(
        event_type='halal_violation_attempt',
        user_id=user_id,
        details={
            'action': 'create_gig',
            'violations': halal_result['violations'],
            'title': title[:100],
            'category': category
        },
        ip_address=request.headers.get('X-Forwarded-For', request.remote_addr)
    )

    # Show error to user
    flash(error_message, 'error')
    return render_template(...)
```

#### B. `/edit-gig/<int:gig_id>` (Line ~3115)
**Gig editing endpoint**

Same validation logic as create, with `action: 'edit_gig'` in logs.

#### C. `/api/gigs` POST (Line ~5127)
**API-based gig creation**

**Returns JSON response:**
```python
if not is_halal_compliant:
    return jsonify({
        'error': 'Halal compliance violation',
        'message_en': halal_result['message_en'],
        'message_ms': halal_result['message_ms'],
        'violations': halal_result['violations']
    }), 400
```

---

### 3. **Frontend Implementation (post_gig.html)**

**Location:** `/home/user/GigHala/templates/post_gig.html`

#### A. Halal Compliance Notice Section (Line 720-767)

**Visual Design:**
- Green background (#E8F5E9) with green left border (#2E7D32)
- Prominent ☪️ icon
- Bilingual notice (Malay & English)
- Expandable details sections for prohibited and allowed content

**Prohibited Content Details:**
```html
<details>
    <summary>❌ PROHIBITED Content & Activities</summary>
    <ul>
        <li>❌ Alcohol, beer, wine...</li>
        <li>❌ Gambling, betting...</li>
        <li>❌ Pork, ham, bacon...</li>
        <!-- ... 10 categories total -->
    </ul>
</details>
```

**Allowed Content Examples:**
```html
<details>
    <summary>✅ ALLOWED Gigs Examples</summary>
    <ul>
        <li>✅ Halal logo design</li>
        <li>✅ Article writing</li>
        <!-- ... 8 examples total -->
    </ul>
</details>
```

#### B. Mandatory Halal Checkbox (Line 784-796)

**Features:**
- `required` attribute (HTML5 validation)
- Pre-checked by default
- Visual emphasis (green border, green background)
- **WAJIB/REQUIRED** label
- Bilingual confirmation text

**Code:**
```html
<label class="checkbox-item" style="border: 2px solid #2E7D32; background: #E8F5E9;">
    <input type="checkbox" id="halal_compliant" name="halal_compliant" required checked>
    <div>
        <div class="checkbox-label" style="color: #1B5E20; font-weight: 600;">
            ☪️ Halal Compliant <span style="color: #D32F2F;">*WAJIB/REQUIRED</span>
        </div>
        <div class="checkbox-desc" style="color: #2E7D32; font-weight: 500;">
            Saya mengesahkan gig ini 100% halal...
        </div>
    </div>
</label>
```

#### C. JavaScript Validation (Line 900-987)

**Prohibited Keywords Array:**
```javascript
const prohibitedKeywords = [
    'alcohol', 'alkohol', 'beer', 'gambling', 'judi', 'pork', 'babi',
    'porn', 'escort', 'riba', 'scam', 'drugs', 'cigarette', 'sihir',
    // ... ~50 most common keywords
];
```

**Validation Checks:**

1. **Mandatory Checkbox Check:**
```javascript
if (!halalCheckbox.checked) {
    e.preventDefault();
    showAlert('⚠️ You MUST confirm this gig is halal...');
    halalCheckbox.scrollIntoView({ behavior: 'smooth' });
    halalCheckbox.parentElement.parentElement.style.animation = 'shake 0.5s';
    return;
}
```

2. **Title Keyword Check:**
```javascript
const titleViolation = checkProhibitedContent(title);
if (titleViolation) {
    e.preventDefault();
    showAlert(`❌ Title contains prohibited content: "${titleViolation}"`);
    document.getElementById('title').style.borderColor = '#D32F2F';
    return;
}
```

3. **Description Keyword Check:**
```javascript
const descViolation = checkProhibitedContent(description);
if (descViolation) {
    e.preventDefault();
    showAlert(`❌ Description contains prohibited content: "${descViolation}"`);
    document.getElementById('description').style.borderColor = '#D32F2F';
    return;
}
```

**Helper Function:**
```javascript
function checkProhibitedContent(text) {
    if (!text) return null;
    const lowerText = text.toLowerCase();
    for (const keyword of prohibitedKeywords) {
        const regex = new RegExp('\\b' + keyword + '\\b', 'i');
        if (regex.test(lowerText)) {
            return keyword;
        }
    }
    return null;
}
```

#### D. Shake Animation CSS (Line 352-357)

```css
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
    20%, 40%, 60%, 80% { transform: translateX(5px); }
}
```

---

## Validation Rules

### Multi-Layer Validation Strategy

| Layer | Technology | Scope | Purpose |
|-------|------------|-------|---------|
| **Frontend** | JavaScript | ~50 keywords | Fast feedback, user experience |
| **Backend** | Python | 200+ keywords | Comprehensive enforcement |
| **Database** | PostgreSQL | Schema constraints | Data integrity |
| **Admin** | Manual Review | Edge cases | Human oversight |

### Validation Sequence

```
1. User fills form
   ↓
2. Category selection (restricted to 29 approved categories)
   ↓
3. User checks mandatory halal checkbox
   ↓
4. User clicks Submit
   ↓
5. Frontend JavaScript validation
   • Checkbox checked?
   • Title contains prohibited keywords?
   • Description contains prohibited keywords?
   ↓
6. Backend Python validation
   • Category in approved list?
   • Title contains prohibited keywords? (full list)
   • Description contains prohibited keywords? (full list)
   • Skills contain prohibited keywords? (full list)
   ↓
7. Security logging (if violation detected)
   ↓
8. Database insertion (if all validations pass)
   ↓
9. Admin review (optional, for halal_verified flag)
```

### Category Enforcement

**Strict Whitelisting:**
- Only 29 predefined categories allowed
- No free-text category input
- Radio button selection only
- Backend validates against `HALAL_APPROVED_CATEGORY_SLUGS`

**Example Categories:**
```python
HALAL_APPROVED_CATEGORY_SLUGS = [
    'design', 'writing', 'video', 'tutoring', 'content', 'web',
    'marketing', 'admin', 'delivery', 'general', 'programming',
    'consulting', 'engineering', 'music', 'photography', 'finance',
    'crafts', 'garden', 'coaching', 'data', 'pets', 'handyman',
    'tours', 'events', 'online-selling', 'virtual-assistant',
    'micro-tasks', 'caregiving', 'creative-other'
]
```

### Keyword Detection Algorithm

**Word Boundary Matching:**
```python
pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
if re.search(pattern, text_normalized):
    violations.append(keyword)
```

**Benefits:**
- Avoids false positives (e.g., "bacon" matches but not "aback on")
- Case-insensitive matching
- Handles multi-word phrases (e.g., "loan shark", "black magic")

**Limitations:**
- Cannot detect intentional misspellings (e.g., "b33r", "alc0hol")
- Cannot detect context (e.g., "anti-alcohol campaign" would trigger)

**Mitigation:**
- Admin review system for flagged gigs
- User education about prohibited content
- Conservative approach (better to reject than allow)

---

## API Integration

### Gig Creation API

**Endpoint:** `POST /api/gigs`

**Request Body:**
```json
{
    "title": "Need graphic designer for halal restaurant",
    "description": "Design menu and signage for halal restaurant",
    "category": "design",
    "budget_min": 100,
    "budget_max": 500,
    "duration": "1 week",
    "location": "Kuala Lumpur",
    "is_remote": false,
    "halal_compliant": true,
    "skills_required": ["graphic design", "adobe illustrator"]
}
```

**Success Response (200):**
```json
{
    "id": 123,
    "gig_code": "GIG-00123",
    "title": "Need graphic designer for halal restaurant",
    "status": "open",
    "halal_compliant": true,
    "halal_verified": false,
    "created_at": "2025-01-15T10:30:00Z"
}
```

**Halal Violation Error (400):**
```json
{
    "error": "Halal compliance violation",
    "message_en": "This gig cannot be posted because it contains non-halal elements...",
    "message_ms": "Gig ini tidak boleh dipos kerana mengandungi elemen yang tidak halal...",
    "violations": {
        "category": false,
        "title": [],
        "description": ["beer", "alcohol"],
        "skills": []
    }
}
```

**Security Event Log:**
```python
{
    'event_type': 'halal_violation_attempt',
    'user_id': 456,
    'details': {
        'action': 'create_gig_api',
        'violations': {
            'description': ['beer', 'alcohol']
        },
        'title': 'Need delivery person for party supplies',
        'category': 'delivery'
    },
    'ip_address': '203.0.113.45',
    'timestamp': '2025-01-15T10:30:00Z'
}
```

---

## Admin Controls

### Database Fields

**Gig Model:**
```python
class Gig(db.Model):
    # ... other fields ...
    halal_compliant = db.Column(db.Boolean, default=True)  # User-declared
    halal_verified = db.Column(db.Boolean, default=False)  # Admin-verified
```

### Admin Dashboard Integration

**Admin Update Endpoint:** `PUT /api/admin/gigs/<id>`

**Admin can update:**
```python
{
    "halal_verified": true,  # Mark as admin-verified
    "status": "open",
    "approved_budget": 350.00
}
```

### Violation Monitoring

**Security Events Table:**
```sql
SELECT
    event_type,
    user_id,
    details->>'title' as gig_title,
    details->>'violations' as violations,
    created_at
FROM security_events
WHERE event_type = 'halal_violation_attempt'
ORDER BY created_at DESC
LIMIT 100;
```

**Admin Actions:**
1. Review violation logs daily
2. Identify repeat offenders
3. Contact users for education
4. Suspend accounts for intentional violations
5. Update prohibited keyword list based on patterns

---

## Testing & Verification

### Test Cases

#### ✅ **Valid Halal Gig**
```python
# Input
title = "Need Malay-English translator for halal cookbook"
description = "Translate recipes for traditional Malay halal cooking"
category = "writing"
skills = "translation, Malay, English"

# Expected Result
is_halal = True
violations = {}
```

#### ❌ **Invalid - Alcohol Keywords**
```python
# Input
title = "Deliver beer to party venue"
description = "Need someone to transport alcoholic beverages"
category = "delivery"

# Expected Result
is_halal = False
violations = {
    'title': ['beer'],
    'description': ['alcoholic']
}
```

#### ❌ **Invalid - Gambling Keywords**
```python
# Input
title = "Build online casino website"
description = "Develop gambling platform with slot machines"
category = "web"

# Expected Result
is_halal = False
violations = {
    'title': ['casino'],
    'description': ['gambling', 'slot machines']
}
```

#### ❌ **Invalid - Interest/Riba Keywords**
```python
# Input
title = "Financial advisor for interest-based loans"
description = "Help clients get conventional bank loans with interest"
category = "consulting"

# Expected Result
is_halal = False
violations = {
    'title': ['interest-based', 'loans'],
    'description': ['conventional bank', 'interest']
}
```

#### ❌ **Invalid - Category Not Approved**
```python
# Input
category = "adult-entertainment"

# Expected Result
is_halal = False
error = "Category 'adult-entertainment' is not in the approved halal category list"
```

### Manual Testing Checklist

- [ ] Try posting gig with alcohol keywords in title
- [ ] Try posting gig with gambling keywords in description
- [ ] Try unchecking halal checkbox (should prevent submission)
- [ ] Try selecting each of the 29 approved categories
- [ ] Try submitting gig with valid halal content
- [ ] Verify security event logging in database
- [ ] Test API endpoint with prohibited keywords
- [ ] Verify admin can update halal_verified flag
- [ ] Test frontend keyword validation (immediate feedback)
- [ ] Test shake animation on checkbox validation failure

---

## Future Enhancements

### 1. **AI-Powered Content Moderation**

**Objective:** Detect subtle violations that keyword matching misses.

**Approach:**

#### A. **Local LLM Integration (Recommended)**
```python
from transformers import pipeline

# Load a lightweight text classification model
classifier = pipeline("text-classification", model="cross-encoder/nli-deberta-v3-small")

def ai_halal_check(text):
    """
    Use NLI (Natural Language Inference) to detect haram content.
    """
    prompt = f"The following text describes a halal-compliant service: {text}"
    result = classifier(prompt)

    # If confidence in "contradiction" is high, text may be haram
    if result[0]['label'] == 'CONTRADICTION' and result[0]['score'] > 0.85:
        return False, "AI detected potential non-halal content"
    return True, ""
```

**Benefits:**
- Catches context-aware violations (e.g., "deliver party supplies" + "ethanol cleaner")
- No external API calls (privacy-friendly)
- Can run on Railway/cloud with GPU

**Limitations:**
- Requires model fine-tuning for halal/haram classification
- Adds processing time (~500ms per gig)
- May have false positives

#### B. **Rules-Based Enhancement**
```python
# Detect suspicious patterns
SUSPICIOUS_PATTERNS = [
    r'deliver.*party',  # Could be alcohol delivery
    r'casino.*software',
    r'adult.*content',
    r'\d{2,3}d',  # 4D, 6D lottery
]

def check_suspicious_patterns(text):
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Suspicious pattern detected: {pattern}"
    return False, ""
```

#### C. **OpenAI Moderation API (External)**
```python
import openai

def openai_moderation_check(text):
    """
    Use OpenAI's Moderation API to detect harmful content.
    Free tier: 100 requests/min
    """
    response = openai.Moderation.create(input=text)
    result = response['results'][0]

    if result['flagged']:
        return False, f"Flagged categories: {result['categories']}"
    return True, ""
```

**Benefits:**
- Very accurate for sexual content, violence, hate speech
- Pre-trained, no setup needed

**Limitations:**
- External API dependency
- Privacy concerns (sends data to OpenAI)
- Cost at scale
- Not specifically trained for halal/haram concepts

### 2. **User Reputation System**

Track user compliance history:
```python
class User(db.Model):
    # ... existing fields ...
    halal_violations_count = db.Column(db.Integer, default=0)
    halal_compliance_score = db.Column(db.Float, default=100.0)  # 0-100

def update_compliance_score(user_id, violation_severity):
    user = User.query.get(user_id)
    user.halal_violations_count += 1
    user.halal_compliance_score -= violation_severity  # e.g., -10 for minor, -50 for severe

    if user.halal_compliance_score < 50:
        # Require admin review for all future gigs
        user.requires_halal_review = True

    if user.halal_compliance_score < 20:
        # Suspend account
        user.account_status = 'suspended'
        send_email(user.email, "Account suspended due to halal violations")
```

### 3. **Dynamic Keyword Updates**

Admin panel to add keywords without code changes:
```python
class ProhibitedKeyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # 'alcohol', 'gambling', etc.
    language = db.Column(db.String(10))  # 'en', 'ms'
    severity = db.Column(db.String(20))  # 'high', 'medium', 'low'
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Load from database instead of hardcoded list
def load_prohibited_keywords():
    keywords = ProhibitedKeyword.query.all()
    return [k.keyword for k in keywords]
```

### 4. **Multilingual Support Expansion**

Add support for more languages:
- Arabic (العربية) - for Islamic terms
- Chinese (中文) - for Malaysian Chinese community
- Tamil (தமிழ்) - for Malaysian Indian community

### 5. **Halal Certification Badges**

Visual trust indicators:
```html
<div class="gig-badges">
    <span class="badge badge-halal-verified">☪️ HALAL VERIFIED</span>
    <span class="badge badge-halal-compliant">✓ HALAL COMPLIANT</span>
    <span class="badge badge-needs-review">⏳ PENDING REVIEW</span>
</div>
```

### 6. **Automated Image Content Analysis**

Scan uploaded gig photos for prohibited content:
```python
from PIL import Image
import pytesseract

def scan_gig_photo(image_path):
    """
    Extract text from image and check for prohibited keywords.
    """
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)

    is_compliant, violations = check_prohibited_keywords(text)
    return is_compliant, violations
```

### 7. **Community Reporting System**

Allow users to report non-halal gigs:
```python
class GigReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gig_id = db.Column(db.Integer, db.ForeignKey('gig.id'))
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reason = db.Column(db.String(50))  # 'alcohol', 'gambling', 'adult', etc.
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'reviewed', 'action_taken'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

---

## Contact & Support

**Halal Compliance Team:**
📧 Email: halal@gighala.my
📱 WhatsApp: +60 12-345-6789
🌐 Website: https://gighala.my/halal-compliance

**Report Violations:**
If you encounter a gig that violates halal compliance, please report it immediately.

---

## Appendix: Complete Code Reference

### A. File Locations

| File | Path | Purpose |
|------|------|---------|
| Halal Module | `/home/user/GigHala/halal_compliance.py` | Core validation logic |
| Backend App | `/home/user/GigHala/app.py` | Flask routes & integration |
| Gig Form Template | `/home/user/GigHala/templates/post_gig.html` | Frontend form |
| Documentation | `/home/user/GigHala/HALAL_COMPLIANCE_SYSTEM.md` | This file |

### B. Database Schema

```sql
-- Gig table (relevant fields)
CREATE TABLE gig (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    halal_compliant BOOLEAN DEFAULT TRUE,
    halal_verified BOOLEAN DEFAULT FALSE,
    skills_required TEXT,  -- JSON array
    client_id INTEGER REFERENCES user(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Security events table (for logging violations)
CREATE TABLE security_event (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES user(id),
    details JSONB,  -- Contains violation details
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster violation queries
CREATE INDEX idx_security_event_type ON security_event(event_type);
CREATE INDEX idx_security_event_user ON security_event(user_id);
```

### C. API Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 400 | `Halal compliance violation` | Gig contains prohibited content |
| 400 | `Category not in approved list` | Invalid category selected |
| 400 | `Missing required fields` | Missing title, description, or category |
| 401 | `Unauthorized` | User not logged in |
| 403 | `Account suspended` | User suspended for repeated violations |
| 500 | `Internal server error` | Server-side error |

---

**Last Updated:** 2025-01-15
**Version:** 1.0.0
**Author:** GigHala Development Team

---

## 🤲 Doa for Platform Success

**Bahasa Melayu:**
> Ya Allah, kurniakanlah keberkatan kepada platform ini dan jadikanlah ia bermanfaat untuk umat Islam. Lindungilah kami daripada segala perkara yang haram dan peliharalah platform ini dalam kepatuhan Syariah-Mu. Ameen.

**English:**
> O Allah, grant blessings to this platform and make it beneficial for the Muslim ummah. Protect us from all haram matters and preserve this platform in compliance with Your Shariah. Ameen.

---

**☪️ Alhamdulillah - All praise is due to Allah**
