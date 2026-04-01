import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL', '').replace(
    'postgres://', 'postgresql://', 1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

checks = {
    'gig': [
        'listing_type', 'commitment_days_per_week',
        'engagement_duration_months', 'rate_type',
        'monthly_retainer_amount', 'min_years_experience',
        'industry_focus', 'remote_onsite'
    ],
    'user': [
        'available_for_fractional', 'fractional_days_available',
        'max_concurrent_clients', 'min_engagement_months',
        'monthly_retainer_rate', 'fractional_industries',
        'linkedin_url', 'years_experience'
    ],
    'escrow': [
        'retainer_start_date', 'retainer_next_due',
        'termination_requested', 'termination_requested_by',
        'termination_notice_date'
    ],
    'fractional_application': ['id', 'gig_id', 'applicant_id', 'status']
}

all_ok = True
for table, columns in checks.items():
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s
    """, (table,))
    existing = {row[0] for row in cur.fetchall()}
    for col in columns:
        status = '✓' if col in existing else '✗ MISSING'
        if col not in existing:
            all_ok = False
        print(f"  {status}  {table}.{col}")

cur.close()
conn.close()
print()
print("All columns present ✓" if all_ok else
      "Some columns missing — check errors above ✗")
