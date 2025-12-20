# SOCSO Manual Data Update Queries

## Overview
These SQL queries allow you to manually update SOCSO contribution records when needed. Use these for data corrections, testing, or special adjustments.

---

## 1. VIEW SOCSO CONTRIBUTIONS
### See all SOCSO contributions with freelancer details
```sql
SELECT 
    sc.id,
    u.username,
    u.email,
    u.ic_number,
    sc.contribution_month,
    sc.gross_amount,
    sc.platform_commission,
    sc.net_earnings,
    sc.socso_amount,
    sc.final_payout,
    sc.remitted_to_socso,
    sc.created_at
FROM socso_contribution sc
JOIN "user" u ON sc.freelancer_id = u.id
ORDER BY sc.created_at DESC
LIMIT 100;
```

### Check SOCSO contributions for a specific freelancer
```sql
SELECT 
    sc.id,
    sc.contribution_month,
    sc.gross_amount,
    sc.platform_commission,
    sc.net_earnings,
    sc.socso_amount,
    sc.final_payout,
    sc.remitted_to_socso,
    sc.created_at
FROM socso_contribution sc
WHERE sc.freelancer_id = (SELECT id FROM "user" WHERE username = 'USERNAME_HERE')
ORDER BY sc.created_at DESC;
```

### View monthly SOCSO summary
```sql
SELECT 
    DATE_TRUNC('month', sc.created_at)::date AS month,
    COUNT(*) AS transaction_count,
    SUM(sc.gross_amount) AS total_gross,
    SUM(sc.platform_commission) AS total_commission,
    SUM(sc.net_earnings) AS total_net_earnings,
    SUM(sc.socso_amount) AS total_socso_deducted,
    SUM(sc.final_payout) AS total_payout,
    COUNT(CASE WHEN sc.remitted_to_socso = true THEN 1 END) AS remitted_count
FROM socso_contribution sc
GROUP BY DATE_TRUNC('month', sc.created_at)
ORDER BY month DESC;
```

---

## 2. UPDATE SOCSO AMOUNTS (Corrections)
### Recalculate SOCSO amount for specific contribution
```sql
UPDATE socso_contribution
SET socso_amount = ROUND(net_earnings * 0.0125, 2),
    final_payout = ROUND(net_earnings - (net_earnings * 0.0125), 2),
    updated_at = NOW()
WHERE id = CONTRIBUTION_ID_HERE;
```

### Bulk recalculate SOCSO for a specific month
```sql
UPDATE socso_contribution
SET socso_amount = ROUND(net_earnings * 0.0125, 2),
    final_payout = ROUND(net_earnings - (net_earnings * 0.0125), 2),
    updated_at = NOW()
WHERE DATE_TRUNC('month', created_at) = '2025-12-01'::date
  AND freelancer_id = (SELECT id FROM "user" WHERE username = 'USERNAME_HERE');
```

### Fix incorrect net earnings (if commission was calculated wrong)
```sql
-- First check the transaction
SELECT * FROM transaction WHERE id = TRANSACTION_ID_HERE;

-- Then update the SOCSO record
UPDATE socso_contribution
SET net_earnings = CORRECT_NET_EARNINGS_HERE,
    socso_amount = ROUND(CORRECT_NET_EARNINGS_HERE * 0.0125, 2),
    final_payout = ROUND(CORRECT_NET_EARNINGS_HERE - (CORRECT_NET_EARNINGS_HERE * 0.0125), 2),
    updated_at = NOW()
WHERE id = CONTRIBUTION_ID_HERE;
```

---

## 3. UPDATE REMITTANCE STATUS
### Mark contribution as remitted to SOCSO
```sql
UPDATE socso_contribution
SET remitted_to_socso = true,
    updated_at = NOW()
WHERE id = CONTRIBUTION_ID_HERE;
```

### Mark all pending contributions for a month as remitted
```sql
UPDATE socso_contribution
SET remitted_to_socso = true,
    updated_at = NOW()
WHERE DATE_TRUNC('month', created_at) = '2025-12-01'::date
  AND remitted_to_socso = false;
```

### Revert remittance status (if uploaded by mistake)
```sql
UPDATE socso_contribution
SET remitted_to_socso = false,
    updated_at = NOW()
WHERE id = CONTRIBUTION_ID_HERE;
```

---

## 4. DELETE RECORDS (Use Carefully)
### Delete a single incorrect SOCSO record
```sql
DELETE FROM socso_contribution
WHERE id = CONTRIBUTION_ID_HERE;
```

### Delete all SOCSO records for a specific freelancer
```sql
DELETE FROM socso_contribution
WHERE freelancer_id = (SELECT id FROM "user" WHERE username = 'USERNAME_HERE');
```

### Delete all SOCSO records for a specific month
```sql
DELETE FROM socso_contribution
WHERE DATE_TRUNC('month', created_at) = '2025-12-01'::date;
```

---

## 5. FREELANCER SOCSO CONSENT MANAGEMENT
### View freelancers with SOCSO consent
```sql
SELECT 
    id,
    username,
    email,
    ic_number,
    socso_consent,
    created_at
FROM "user"
WHERE role = 'freelancer'
  AND socso_consent = true
ORDER BY username;
```

### Update SOCSO consent for a freelancer
```sql
UPDATE "user"
SET socso_consent = true,
    ic_number = 'IC_NUMBER_HERE'
WHERE username = 'USERNAME_HERE';
```

### View freelancers missing IC number
```sql
SELECT 
    id,
    username,
    email,
    socso_consent,
    ic_number
FROM "user"
WHERE role = 'freelancer'
  AND (ic_number IS NULL OR ic_number = '')
  AND socso_consent = true
ORDER BY username;
```

---

## 6. COMPLIANCE CHECKS
### Find pending SOCSO remittances for a period
```sql
SELECT 
    u.username,
    u.email,
    u.ic_number,
    COUNT(*) AS pending_count,
    SUM(sc.socso_amount) AS total_pending_socso
FROM socso_contribution sc
JOIN "user" u ON sc.freelancer_id = u.id
WHERE sc.remitted_to_socso = false
  AND DATE_TRUNC('month', sc.created_at) >= '2025-11-01'::date
GROUP BY u.id, u.username, u.email, u.ic_number
ORDER BY total_pending_socso DESC;
```

### Identify freelancers with incomplete data (blocking payouts)
```sql
SELECT 
    u.id,
    u.username,
    u.email,
    CASE 
        WHEN u.ic_number IS NULL OR u.ic_number = '' THEN 'Missing IC Number'
        WHEN u.socso_consent = false THEN 'No SOCSO Consent'
        ELSE 'Complete'
    END AS status,
    COUNT(CASE WHEN t.status = 'completed' THEN 1 END) AS completed_gigs
FROM "user" u
LEFT JOIN transaction t ON u.id = t.freelancer_id
WHERE u.role = 'freelancer'
GROUP BY u.id, u.username, u.email, u.ic_number, u.socso_consent
ORDER BY u.username;
```

### Monthly compliance summary
```sql
SELECT 
    DATE_TRUNC('month', sc.created_at)::date AS month,
    COUNT(DISTINCT sc.freelancer_id) AS unique_freelancers,
    COUNT(*) AS total_transactions,
    SUM(sc.socso_amount) AS total_socso,
    COUNT(CASE WHEN sc.remitted_to_socso = true THEN 1 END) AS remitted_count,
    COUNT(CASE WHEN sc.remitted_to_socso = false THEN 1 END) AS pending_count
FROM socso_contribution sc
GROUP BY DATE_TRUNC('month', sc.created_at)
ORDER BY month DESC;
```

---

## 7. BULK OPERATIONS
### Generate mock SOCSO data for testing
```sql
-- Add test freelancer earnings and create SOCSO records
INSERT INTO socso_contribution (freelancer_id, gross_amount, platform_commission, net_earnings, socso_amount, final_payout, remitted_to_socso, created_at)
SELECT 
    u.id,
    ROUND((RANDOM() * 500 + 100)::numeric, 2),  -- Random gross 100-600
    ROUND((RANDOM() * 100 + 20)::numeric, 2),   -- Random commission 20-120
    ROUND((RANDOM() * 400 + 50)::numeric, 2),   -- Random net 50-450
    0,
    0,
    false,
    NOW() - (INTERVAL '1 day' * FLOOR(RANDOM() * 30))  -- Random date in last 30 days
FROM "user" u
WHERE u.role = 'freelancer' 
  AND u.socso_consent = true
  AND u.ic_number IS NOT NULL
  AND u.ic_number != ''
LIMIT 5;

-- Then calculate SOCSO amounts properly
UPDATE socso_contribution
SET socso_amount = ROUND(net_earnings * 0.0125, 2),
    final_payout = ROUND(net_earnings - (net_earnings * 0.0125), 2)
WHERE socso_amount = 0;
```

### Export data for ASSIST Portal (CSV format via SQL)
```sql
SELECT 
    u.ic_number,
    DATE_PART('year', sc.created_at)::int AS year,
    DATE_PART('month', sc.created_at)::int AS month,
    ROUND(SUM(sc.net_earnings)::numeric, 2) AS contribution_amount,
    ROUND(SUM(sc.socso_amount)::numeric, 2) AS socso_amount,
    u.username AS employee_name,
    u.email
FROM socso_contribution sc
JOIN "user" u ON sc.freelancer_id = u.id
WHERE sc.remitted_to_socso = true
GROUP BY u.ic_number, u.username, u.email, DATE_PART('year', sc.created_at), DATE_PART('month', sc.created_at)
ORDER BY u.ic_number, DATE_PART('year', sc.created_at), DATE_PART('month', sc.created_at);
```

---

## 8. USEFUL REFERENCE QUERIES
### Get total stats dashboard
```sql
SELECT 
    (SELECT COUNT(*) FROM "user" WHERE role = 'freelancer') AS total_freelancers,
    (SELECT COUNT(*) FROM "user" WHERE role = 'freelancer' AND socso_consent = true) AS freelancers_with_socso,
    (SELECT COUNT(*) FROM socso_contribution) AS total_contributions,
    (SELECT SUM(socso_amount) FROM socso_contribution) AS total_socso_collected,
    (SELECT SUM(socso_amount) FROM socso_contribution WHERE remitted_to_socso = false) AS pending_remittance;
```

### Check for data anomalies
```sql
-- Find contributions where SOCSO != net_earnings * 0.0125
SELECT 
    sc.id,
    u.username,
    sc.net_earnings,
    sc.socso_amount,
    ROUND(sc.net_earnings * 0.0125, 2) AS expected_socso,
    sc.final_payout,
    ROUND(sc.net_earnings - (sc.net_earnings * 0.0125), 2) AS expected_payout
FROM socso_contribution sc
JOIN "user" u ON sc.freelancer_id = u.id
WHERE sc.socso_amount != ROUND(sc.net_earnings * 0.0125, 2)
   OR sc.final_payout != ROUND(sc.net_earnings - (sc.net_earnings * 0.0125), 2);
```

---

## Important Notes:
1. **Always backup** before running UPDATE or DELETE queries
2. **Test with SELECT first** - Run the SELECT version of a query before the UPDATE version
3. **Use transactions** - Consider wrapping multiple updates:
   ```sql
   BEGIN;
   -- Your updates here
   COMMIT;  -- or ROLLBACK; to undo
   ```
4. **Verify 1.25% rate** - Always ensure socso_amount = net_earnings × 0.0125
5. **Check remittance status** - Only mark as remitted when actually uploaded to ASSIST Portal
6. **Preserve audit trail** - The updated_at field tracks when records were modified

---

## Quick Template for Common Tasks:
```sql
-- Template: Update single record
UPDATE socso_contribution
SET [COLUMN] = [NEW_VALUE],
    updated_at = NOW()
WHERE id = [RECORD_ID];

-- Template: Bulk update by date
UPDATE socso_contribution
SET [COLUMN] = [NEW_VALUE],
    updated_at = NOW()
WHERE DATE_TRUNC('month', created_at) = '[YYYY-MM-01]'::date;

-- Template: Verify changes
SELECT * FROM socso_contribution
WHERE [YOUR_CONDITION]
ORDER BY created_at DESC
LIMIT 10;
```
