"""Password hashing/verification helpers."""

from __future__ import annotations

import hashlib

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
except Exception:  # pragma: no cover
    PasswordHasher = None
    VerifyMismatchError = Exception

try:
    import bcrypt
except Exception:  # pragma: no cover
    bcrypt = None


_ARGON2_PREFIX = "$argon2"


def legacy_hash_password(plain: str) -> str:
    """Legacy SHA-256 hash kept for migration compatibility."""

    return hashlib.sha256(str(plain).encode("utf-8")).hexdigest()


def is_argon2_hash(value: str) -> bool:
    return str(value or "").startswith(_ARGON2_PREFIX)


def is_bcrypt_hash(value: str) -> bool:
    raw = str(value or "")
    return raw.startswith("$2a$") or raw.startswith("$2b$") or raw.startswith("$2y$")


def needs_password_upgrade(stored_hash: str) -> bool:
    """Return True when stored hash is not Argon2id."""

    return not is_argon2_hash(stored_hash)


def hash_password(plain: str) -> str:
    """Hash password using Argon2id, fallback to bcrypt."""

    plain_s = str(plain)
    if PasswordHasher is not None:
        ph = PasswordHasher()
        return ph.hash(plain_s)
    if bcrypt is not None:
        return bcrypt.hashpw(plain_s.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    raise RuntimeError("Nenhum algoritmo de hash seguro disponível (argon2/bcrypt).")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against Argon2id/bcrypt/legacy SHA256 hash."""

    raw_hash = str(hashed or "")
    plain_s = str(plain)
    if is_argon2_hash(raw_hash):
        if PasswordHasher is None:
            return False
        ph = PasswordHasher()
        try:
            return bool(ph.verify(raw_hash, plain_s))
        except Exception:
            return False
    if is_bcrypt_hash(raw_hash):
        if bcrypt is None:
            return False
        try:
            return bool(bcrypt.checkpw(plain_s.encode("utf-8"), raw_hash.encode("utf-8")))
        except Exception:
            return False
    if raw_hash == legacy_hash_password(plain_s):
        return True
    # Legacy plaintext fallback for upgrade-in-place.
    return raw_hash == plain_s
