"""
Migration 060: Backfill socso_membership_number from ic_number.

For users who have an ic_number but no socso_membership_number, copy the
decrypted IC number into socso_membership_number.

ic_number is Fernet-encrypted (EncryptedString), so this must run through the
ORM — a plain SQL UPDATE cannot decrypt the ciphertext.

Usage:
    FIELD_ENCRYPTION_KEY=<key> python migrations/060_backfill_socso_from_ic.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User


def backfill():
    with app.app_context():
        users = (
            db.session.query(User)
            .filter(
                User.ic_number.isnot(None),
                User.ic_number != '',
                db.or_(
                    User.socso_membership_number.is_(None),
                    User.socso_membership_number == '',
                ),
            )
            .all()
        )

        print(f"Found {len(users)} user(s) with IC but no SOCSO number.")

        updated = 0
        for user in users:
            ic = (user.ic_number or '').strip()
            if not ic:
                continue
            if len(ic) > 20:
                print(f"  SKIP  id={user.id} username={user.username!r}: IC too long ({len(ic)} chars)")
                continue
            user.socso_membership_number = ic
            updated += 1
            print(f"  SET   id={user.id} username={user.username!r}: socso_membership_number = {ic!r}")

        db.session.commit()
        print(f"\nDone. Updated {updated} user(s).")


if __name__ == '__main__':
    backfill()
