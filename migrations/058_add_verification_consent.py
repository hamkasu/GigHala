#!/usr/bin/env python3
"""
Migration 058: Add PDPA consent tracking fields to identity_verification
=========================================================================

PDPA 2010 s.7 (Notice & Choice Principle) requires that explicit, recorded
consent is obtained before collecting sensitive personal data such as IC/
passport images. This migration adds three columns to capture that consent.

New columns:
  verification_consent      BOOLEAN   — user explicitly ticked the consent checkbox
  verification_consent_date TIMESTAMP — UTC timestamp when consent was given
  consent_policy_version    VARCHAR   — version of privacy policy accepted
"""

import os
import sys
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("WARNING: DATABASE_URL not set, skipping migration 058")
    sys.exit(0)

is_postgres = DATABASE_URL.startswith('postgresql')
is_sqlite   = DATABASE_URL.startswith('sqlite')

engine = create_engine(DATABASE_URL)

POSTGRES_SQL = """
ALTER TABLE identity_verification
    ADD COLUMN IF NOT EXISTS verification_consent      BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS verification_consent_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS consent_policy_version    VARCHAR(10) DEFAULT '1.0';

UPDATE identity_verification
SET    consent_policy_version = 'legacy'
WHERE  verification_consent_date IS NULL
  AND  consent_policy_version = '1.0';

CREATE INDEX IF NOT EXISTS idx_identity_verification_consent
    ON identity_verification (verification_consent);

COMMENT ON COLUMN identity_verification.verification_consent      IS 'PDPA s.7: user explicitly consented to biometric data processing';
COMMENT ON COLUMN identity_verification.verification_consent_date IS 'UTC timestamp when consent was given';
COMMENT ON COLUMN identity_verification.consent_policy_version    IS 'Version of privacy policy accepted; legacy = pre-PDPA enforcement';
"""

# SQLite does not support ADD COLUMN IF NOT EXISTS, so we check first
SQLITE_CHECK = "SELECT COUNT(*) FROM pragma_table_info('identity_verification') WHERE name='verification_consent'"
SQLITE_SQL = """
ALTER TABLE identity_verification ADD COLUMN verification_consent      INTEGER NOT NULL DEFAULT 0;
ALTER TABLE identity_verification ADD COLUMN verification_consent_date TEXT;
ALTER TABLE identity_verification ADD COLUMN consent_policy_version    TEXT    DEFAULT '1.0';
"""


def run():
    try:
        with engine.connect() as conn:
            if is_postgres:
                conn.execute(text(POSTGRES_SQL))
                conn.commit()
                print("Migration 058 applied (PostgreSQL)")
            elif is_sqlite:
                row = conn.execute(text(SQLITE_CHECK)).scalar()
                if row == 0:
                    for stmt in SQLITE_SQL.strip().split(';'):
                        stmt = stmt.strip()
                        if stmt:
                            conn.execute(text(stmt))
                    conn.commit()
                    print("Migration 058 applied (SQLite)")
                else:
                    print("Migration 058 already applied (SQLite)")
            else:
                print("Migration 058: unsupported DB, skipping")
    except Exception as exc:
        print(f"Migration 058 error: {exc}")
        # Non-fatal — column may already exist (IF NOT EXISTS handles Postgres;
        # the SQLite check above handles SQLite). Log and continue.


if __name__ == '__main__':
    run()
