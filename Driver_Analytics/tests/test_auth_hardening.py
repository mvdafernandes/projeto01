"""Authentication/session hardening regression tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core import auth
from core.security.passwords import legacy_hash_password, verify_password


class AuthHardeningTests(unittest.TestCase):
    def test_plaintext_password_fallback_is_removed(self):
        self.assertFalse(verify_password("admin", "admin"))

    def test_legacy_sha256_password_still_verifies(self):
        raw = "Senha@123"
        self.assertTrue(verify_password(raw, legacy_hash_password(raw)))

    def test_cookie_session_roundtrip_uses_signature(self):
        with patch("core.auth._session_signing_secret", return_value="secret"):
            encoded = auth._encode_cookie_session("sid-1", "tok-1")
            self.assertEqual(auth._decode_cookie_session(encoded), ("sid-1", "tok-1"))

    def test_cookie_session_tampering_is_rejected(self):
        with patch("core.auth._session_signing_secret", return_value="secret"):
            encoded = auth._encode_cookie_session("sid-1", "tok-1")
            tampered = f"{encoded[:-1]}{'A' if encoded[-1] != 'A' else 'B'}"
            self.assertIsNone(auth._decode_cookie_session(tampered))

    def test_remote_rate_limit_hash_is_stable(self):
        one = auth._rate_limit_key_hash("login", "Admin")
        two = auth._rate_limit_key_hash("login", "admin")
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
