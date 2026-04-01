import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

# Fix Railway's postgres:// prefix if needed
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

migrations = [
    'migrations/002_fractional_gig_fields.sql',
    'migrations/003_fractional_user_fields.sql',
    'migrations/004_fractional_escrow_fields.sql',
    'migrations/005_fractional_applications.sql',
]

for filepath in migrations:
    print(f"Applying {filepath}...")
    with open(filepath, 'r') as f:
        sql = f.read()
    try:
        cur.execute(sql)
        print(f"  ✓ {filepath} applied successfully")
    except Exception as e:
        print(f"  ✗ {filepath} failed: {e}")

cur.close()
conn.close()
print("Done.")
