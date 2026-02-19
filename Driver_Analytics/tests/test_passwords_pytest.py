from core.security.passwords import hash_password, needs_password_upgrade, verify_password


def test_hash_and_verify_password_roundtrip():
    raw = "Senha@123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("outra", hashed) is False


def test_legacy_plaintext_upgrade_needed():
    assert needs_password_upgrade("admin") is True
    assert verify_password("admin", "admin") is True
