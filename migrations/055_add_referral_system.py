#!/usr/bin/env python3
"""
Database Migration: Add Referral System

This migration adds:
1. referral_code column to user table (unique 8-char code)
2. referred_by_id column to user table (FK to user)
3. referral_bonus_credited column to user table
4. referral table to track referrals and bonus status

Date: 2026-03-28
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import inspect, text
import secrets


def check_column_exists(table_name, column_name):
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_table_exists(table_name):
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def run_migration():
    print("\n=== Referral System Migration ===")

    with app.app_context():
        with db.engine.connect() as conn:

            # 1. Add referral_code to user
            if not check_column_exists('user', 'referral_code'):
                print("Adding referral_code to user table...")
                conn.execute(text("ALTER TABLE \"user\" ADD COLUMN referral_code VARCHAR(10) UNIQUE"))
                conn.commit()
                print("  ✓ referral_code added")
            else:
                print("  - referral_code already exists, skipping")

            # 2. Add referred_by_id to user
            if not check_column_exists('user', 'referred_by_id'):
                print("Adding referred_by_id to user table...")
                conn.execute(text("ALTER TABLE \"user\" ADD COLUMN referred_by_id INTEGER REFERENCES \"user\"(id)"))
                conn.commit()
                print("  ✓ referred_by_id added")
            else:
                print("  - referred_by_id already exists, skipping")

            # 3. Add referral_bonus_credited to user
            if not check_column_exists('user', 'referral_bonus_credited'):
                print("Adding referral_bonus_credited to user table...")
                conn.execute(text("ALTER TABLE \"user\" ADD COLUMN referral_bonus_credited BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("  ✓ referral_bonus_credited added")
            else:
                print("  - referral_bonus_credited already exists, skipping")

            # 4. Create referral table
            if not check_table_exists('referral'):
                print("Creating referral table...")
                conn.execute(text("""
                    CREATE TABLE referral (
                        id SERIAL PRIMARY KEY,
                        referrer_id INTEGER NOT NULL REFERENCES "user"(id),
                        referred_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id),
                        bonus_amount FLOAT DEFAULT 5.0,
                        status VARCHAR(20) DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT NOW(),
                        credited_at TIMESTAMP
                    )
                """))
                conn.commit()
                print("  ✓ referral table created")
            else:
                print("  - referral table already exists, skipping")

            # 5. Backfill referral_code for existing users who don't have one
            print("Backfilling referral codes for existing users...")
            result = conn.execute(text("SELECT id FROM \"user\" WHERE referral_code IS NULL"))
            users_without_code = result.fetchall()
            for (user_id,) in users_without_code:
                while True:
                    code = secrets.token_hex(4).upper()
                    existing = conn.execute(
                        text("SELECT 1 FROM \"user\" WHERE referral_code = :code"),
                        {"code": code}
                    ).fetchone()
                    if not existing:
                        break
                conn.execute(
                    text("UPDATE \"user\" SET referral_code = :code WHERE id = :uid"),
                    {"code": code, "uid": user_id}
                )
            conn.commit()
            print(f"  ✓ Backfilled referral codes for {len(users_without_code)} users")

        print("\n✓ Migration complete!")


if __name__ == '__main__':
    run_migration()
