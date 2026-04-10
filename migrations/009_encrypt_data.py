"""
Migration 009 — Encrypt existing plain-text sensitive fields in the database.

Run AFTER applying migrations/009_encrypt_sensitive_fields.sql.

Usage:
    FIELD_ENCRYPTION_KEY=<your-key> python migrations/009_encrypt_data.py

The script is idempotent: already-encrypted values (valid Fernet tokens)
are skipped so it can safely be re-run.
"""

import os
import sys

# Ensure the app root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.fernet import Fernet, InvalidToken

KEY = os.environ.get('FIELD_ENCRYPTION_KEY', '').strip()
if not KEY:
    print("ERROR: FIELD_ENCRYPTION_KEY env var is not set.", file=sys.stderr)
    sys.exit(1)

fernet = Fernet(KEY.encode())


def is_encrypted(value: str) -> bool:
    """Return True if the value is already a valid Fernet token."""
    if not value:
        return True
    try:
        fernet.decrypt(value.encode())
        return True
    except (InvalidToken, Exception):
        return False


def encrypt(value: str) -> str:
    return fernet.encrypt(value.encode()).decode()


# ---------------------------------------------------------------------------
# Bootstrap minimal Flask + SQLAlchemy context (no full app startup)
# ---------------------------------------------------------------------------

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

mini_app = Flask(__name__)
mini_app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'sqlite:///gighala.db')
    .replace('postgres://', 'postgresql+psycopg2://', 1)
    .replace('postgresql://', 'postgresql+psycopg2://', 1)
)
mini_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
mini_db = SQLAlchemy(mini_app)

# Reflect existing tables (no model definitions needed)
with mini_app.app_context():
    mini_db.engine.connect()   # verify connection
    conn = mini_db.engine.connect()

    TASKS = [
        # (table, column_list)
        ('"user"',               ['phone', 'ic_number', 'bank_account_number', 'bank_account_holder']),
        ('identity_verification', ['ic_number', 'full_name']),
        ('payout',                ['account_number', 'account_name']),
    ]

    from sqlalchemy import text

    total_updated = 0

    for table, columns in TASKS:
        # Fetch all rows with at least one non-null target column
        col_list = ', '.join(['id'] + columns)
        rows = conn.execute(text(f'SELECT {col_list} FROM {table}')).fetchall()

        for row in rows:
            row_dict = dict(zip(['id'] + columns, row))
            updates = {}
            for col in columns:
                val = row_dict[col]
                if val and not is_encrypted(val):
                    updates[col] = encrypt(val)

            if updates:
                set_clause = ', '.join([f'{c} = :{c}' for c in updates])
                updates['_id'] = row_dict['id']
                conn.execute(
                    text(f'UPDATE {table} SET {set_clause} WHERE id = :_id'),
                    updates
                )
                total_updated += 1

        conn.commit()
        print(f"  {table}: processed {len(rows)} rows")

    print(f"\nDone. {total_updated} rows encrypted.")
    conn.close()
