"""Remote database access helpers (Supabase only)."""

from __future__ import annotations

import base64
import json
from urllib.parse import urlparse

from core.config import cache_resource, get_settings


def _decode_jwt_payload(token: str) -> dict:
    parts = str(token or "").split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{payload}{padding}".encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_supabase_key_role(key: str | None = None) -> str:
    """Best-effort classification for the configured Supabase key."""

    raw_key = str(key or get_settings().supabase_key or "").strip()
    if not raw_key:
        return ""
    if raw_key.startswith("sb_secret_"):
        return "secret"
    payload = _decode_jwt_payload(raw_key)
    return str(payload.get("role", "")).strip().lower()


def is_backend_supabase_key(key: str | None = None) -> bool:
    """Return whether the configured key is compatible with backend-only tables."""

    return get_supabase_key_role(key) in {"service_role", "secret"}


@cache_resource
def _create_supabase_client(supabase_url: str, supabase_key: str):
    """Create a cached Supabase client keyed by effective credentials."""

    parsed = urlparse(str(supabase_url or "").strip())
    if not parsed.scheme or not parsed.netloc or parsed.netloc.startswith("."):
        return None

    try:
        from supabase import create_client
    except Exception:
        return None

    try:
        return create_client(str(supabase_url).strip(), str(supabase_key).strip())
    except Exception:
        return None


def get_supabase_client():
    """Return cached Supabase client when credentials are valid."""

    settings = get_settings()
    if settings.app_db_mode == "local":
        return None
    if not settings.supabase_url or not settings.supabase_key:
        if settings.app_db_mode == "remote":
            raise RuntimeError("APP_DB_MODE=remote exige SUPABASE_URL/SUPABASE_KEY válidos.")
        return None
    return _create_supabase_client(settings.supabase_url, settings.supabase_key)
