"""
Field-level and file-level encryption service for PDPA compliance.

Algorithm: AES-128-CBC + HMAC-SHA256 (via cryptography.Fernet).
This is equivalent in security to PostgreSQL pgcrypto's pgp_sym_encrypt()
but keeps the encryption key out of SQL query logs.

Setup:
    Generate a key once and store in the environment:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    Set env var:
        FIELD_ENCRYPTION_KEY=<the 44-char base64 key>

Encrypted columns are stored as Text in PostgreSQL (typically ~120-200 bytes
as base64 ciphertext). The TypeDecorator is transparent to application code:
reads return plain strings, writes encrypt automatically.

Legacy plain-text values are returned as-is on decrypt (graceful migration
path). The next write will encrypt them.
"""

import os
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import types

# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get('FIELD_ENCRYPTION_KEY', '').strip()
        if not key:
            raise RuntimeError(
                "FIELD_ENCRYPTION_KEY environment variable is not set.\n"
                "Generate a key with:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "Then add it to your .env file as FIELD_ENCRYPTION_KEY=<key>"
            )
        _fernet = Fernet(key.encode())
    return _fernet


# ---------------------------------------------------------------------------
# String helpers
# ---------------------------------------------------------------------------

def encrypt_value(plaintext: str) -> str:
    """Encrypt a string. Returns a URL-safe base64 Fernet token."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt a Fernet token back to the original string.
    If decryption fails (e.g. legacy plain-text data), returns the value as-is.
    The next write will encrypt it.
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy unencrypted value — return as-is
        return ciphertext


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt raw bytes (for file-at-rest encryption)."""
    return _get_fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    """
    Decrypt raw bytes.
    Raises InvalidToken if the data is corrupt or not a valid Fernet token.
    """
    return _get_fernet().decrypt(data)


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator
# ---------------------------------------------------------------------------

class EncryptedString(types.TypeDecorator):
    """
    SQLAlchemy column type that transparently encrypts on write and decrypts
    on read. Drop-in replacement for String/Text columns storing sensitive PII.

    Usage:
        ic_number = db.Column(EncryptedString)

    The underlying DB column is TEXT. Queries using WHERE on encrypted columns
    are not supported (use hashed lookups or application-level filtering).
    """
    impl = types.Text   # Encrypted ciphertext stored as TEXT in PostgreSQL
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Python → Database: encrypt before INSERT/UPDATE."""
        if value is None:
            return None
        return encrypt_value(str(value))

    def process_result_value(self, value, dialect):
        """Database → Python: decrypt after SELECT."""
        if value is None:
            return None
        return decrypt_value(value)
