# Data Breach Notification — Standard Operating Procedure

**Document owner:** Data Protection Officer (DPO)
**Contact:** dpo@gighala.my
**Company:** Calmic Sdn Bhd (1466852W / 202201021155)
**Platform:** GigHala (gighala.com)
**Legal basis:** Personal Data Protection Act 2010 (Malaysia)
**Version:** 1.0
**Last reviewed:** April 2026

> **CONFIDENTIAL — INTERNAL USE ONLY**
> Do not share outside of authorised personnel.

---

## 1. What Constitutes a Breach

A personal data breach is any event where personal data held by GigHala is:

- **Accessed** without authorisation (hacking, insider access, accidental exposure)
- **Disclosed** to unintended recipients (wrong email, misconfigured storage, public URL)
- **Lost or destroyed** without recovery (accidental deletion, ransomware)
- **Altered** without authorisation (data tampering)

### High-Risk Data on GigHala

The following data warrants **immediate escalation** due to its sensitivity under PDPA 2010:

| Data Type | Location | Risk Level |
|---|---|---|
| IC/MyKad number | `identity_verification.ic_number` (encrypted) | Critical |
| IC/Passport images | `/uploads/verification/` (encrypted at rest) | Critical |
| Bank account numbers | `user.bank_account_number` (encrypted) | Critical |
| Full name + IC combination | `identity_verification` table | Critical |
| Email addresses | `user.email` | High |
| Phone numbers | `user.phone` (encrypted) | High |
| Transaction records | `transaction`, `payout` tables | High |
| Profile photos | `/uploads/profile_photos/` | Medium |

---

## 2. Incident Response Team

| Role | Person | Contact |
|---|---|---|
| **DPO (Lead)** | *(assign name)* | dpo@gighala.my |
| **Technical Lead** | *(assign name)* | *(internal contact)* |
| **Legal / Compliance** | *(assign name or external counsel)* | *(contact)* |
| **Communications** | *(assign name)* | *(contact)* |
| **CEO / Director** | *(assign name)* | *(contact)* |

All incidents **must be escalated to the DPO immediately** upon discovery, regardless of time.

---

## 3. The 7-Step Response Procedure

### Step 1 — Detect & Report (Hour 0)

**Who:** Anyone (developer, admin, support staff, user complaint)

**Actions:**
- Do not attempt to fix silently — report immediately
- Email `dpo@gighala.my` and `security@gighala.my` with:
  - What you found
  - When you found it
  - How you think it happened (if known)
  - Screenshot or log excerpt if safe to capture
- Do **not** delete logs or modify anything before the DPO is notified

---

### Step 2 — Contain (Hours 0–4)

**Who:** Technical Lead + DPO

**Actions — execute in this order:**

1. **Isolate the affected system** if actively being exploited (take offline if necessary)
2. **Revoke compromised credentials:**
   - Reset admin account passwords
   - Rotate `FIELD_ENCRYPTION_KEY` if the key itself may be exposed (this requires re-encrypting all data — treat as last resort)
   - Rotate `SECRET_KEY` (invalidates all active sessions)
   - Revoke any OAuth tokens
3. **Preserve evidence:**
   - Export application logs before rotation
   - Take a database snapshot
   - Document the state of `/uploads/verification/` directory
4. **Patch the vector** — block the IP range / revoke the access method that caused the breach
5. **Confirm containment** — verify no ongoing unauthorised access

> **Note on encryption key rotation:** If `FIELD_ENCRYPTION_KEY` must be rotated, all existing encrypted fields (IC numbers, phone numbers, bank account numbers, verification images) will need to be decrypted with the old key and re-encrypted with the new key before the app can restart. Coordinate with Technical Lead for a maintenance window.

---

### Step 3 — Assess (Hours 4–24)

**Who:** DPO + Technical Lead

**Document the following:**

| Question | Answer |
|---|---|
| What data was accessed/leaked? | *(e.g. IC images, IC numbers, emails)* |
| How many users are affected? | *(count from DB query)* |
| What is the timeframe of exposure? | *(from logs — first access to containment)* |
| Is IC/passport image data involved? | Yes / No |
| Is the breach ongoing or contained? | Ongoing / Contained |
| What is the likely cause? | *(e.g. SQL injection, misconfigured S3, insider)* |
| Is there evidence of data exfiltration? | Yes / No / Unknown |

**Identify affected users:**
```sql
-- Example: users whose verification images may have been exposed
SELECT u.id, u.email, u.full_name, iv.ic_number, iv.status
FROM "user" u
JOIN identity_verification iv ON iv.user_id = u.id
WHERE iv.created_at BETWEEN '<breach_start>' AND '<breach_end>';
```

**Severity classification:**

| Severity | Criteria |
|---|---|
| **Critical** | IC images or IC numbers exposed; >100 users affected |
| **High** | Email + name combinations exposed; bank data involved |
| **Medium** | Non-sensitive profile data exposed; <10 users affected |
| **Low** | Internal system data with no PII; no user impact |

---

### Step 4 — Notify the Commissioner / JPDP (Within 72 Hours)

**Who:** DPO + Legal

**Regulatory body:** Jabatan Perlindungan Data Peribadi (JPDP)
**Website:** pdp.gov.my
**Hotline:** 03-8911 5800

> **Current legal position (2026):** Mandatory breach reporting is not yet law under PDPA 2010. However, voluntary reporting is strongly recommended and aligns with the incoming PDPA Amendment. Failure to report and subsequent harm to data subjects can result in civil and regulatory liability.

**When reporting to JPDP, include:**
- Company name, registration number, DPO contact
- Nature of the breach (what happened)
- Categories and approximate number of data subjects affected
- Categories of personal data involved
- Likely consequences of the breach
- Measures taken or proposed to address the breach

**For Critical severity breaches:** Notify JPDP within 72 hours even if investigation is incomplete. Provide an interim report and follow up.

---

### Step 5 — Notify Affected Users (Within 72 Hours)

**Who:** DPO + Communications

**Trigger:** Any breach involving IC numbers, IC images, bank data, or email + name combinations.

**Method:** Email to registered email address. Use the template in `docs/internal/breach-notification-email-template.md`.

**What the notification must include (PDPA best practice):**
- Clear plain-language description of what happened
- What personal data was involved
- What GigHala has done to stop it
- What the user should do to protect themselves
- Who to contact for questions

**Do NOT include:**
- Technical details that could help an attacker
- Speculation about the cause before it is confirmed
- Minimising language ("minor incident", "probably nothing")

---

### Step 6 — Document the Incident (Within 7 Days)

**Who:** DPO

**Create an Incident Report containing:**

1. **Timeline** — chronological log from first detection to containment
2. **Root cause analysis** — what vulnerability or process failure caused the breach
3. **Data inventory** — exact records of what data was compromised
4. **Containment actions** — what was done and when
5. **Notification log** — who was notified (JPDP, users), when, and how
6. **Evidence preservation log** — what was captured and where it is stored

Store in: `docs/internal/incidents/YYYY-MM-DD-incident-report.md` (restricted access only).

---

### Step 7 — Post-Mortem & Remediation (Within 30 Days)

**Who:** DPO + Technical Lead + CEO

**Actions:**
- Identify and fix the root cause permanently
- Review whether additional encryption, access controls, or monitoring are needed
- Update this SOP if the incident revealed gaps
- Consider whether a third-party penetration test is warranted
- Brief the board/directors on the incident and remediation

---

## 4. Quick-Reference Checklist

```
HOUR 0      [ ] Incident reported to DPO
            [ ] Incident log started (date, time, reporter)

HOURS 0-4   [ ] System isolated if actively exploited
            [ ] Compromised credentials rotated
            [ ] Evidence (logs, snapshots) preserved
            [ ] Breach vector patched

HOURS 4-24  [ ] Affected users identified (DB query)
            [ ] Data types confirmed
            [ ] Severity classified
            [ ] Legal counsel notified if Critical/High

WITHIN 72H  [ ] JPDP notified (voluntary / mandatory when law changes)
            [ ] Affected users emailed (use template)

WITHIN 7D   [ ] Incident report written and filed

WITHIN 30D  [ ] Root cause fixed
            [ ] SOP updated if needed
            [ ] Board briefing completed
```

---

## 5. Key Contacts & Resources

| Resource | Detail |
|---|---|
| JPDP (Commissioner) | pdp.gov.my · 03-8911 5800 |
| JPDP complaint form | pdp.gov.my/en/complaints |
| NACSA (cyber incidents) | nacsa.gov.my · 1-300-88-2999 |
| GigHala DPO | dpo@gighala.my |
| GigHala Privacy | privacy@gighala.my |
| Internal security | security@gighala.my |

---

## 6. Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | April 2026 | DPO | Initial version |
