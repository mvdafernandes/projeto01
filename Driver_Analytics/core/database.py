"""Remote database access helpers (Supabase only)."""

from __future__ import annotations

from urllib.parse import urlparse

from core.config import cache_resource, get_settings


@cache_resource
def get_supabase_client():
    """Return cached Supabase client when credentials are valid."""

    settings = get_settings()
    if settings.app_db_mode == "local":
        return None
    if not settings.supabase_url or not settings.supabase_key:
        if settings.app_db_mode == "remote":
            raise RuntimeError("APP_DB_MODE=remote exige SUPABASE_URL/SUPABASE_KEY válidos.")
        return None

    parsed = urlparse(settings.supabase_url)
    if not parsed.scheme or not parsed.netloc or parsed.netloc.startswith("."):
        return None

    try:
        from supabase import create_client
    except Exception:
        return None

    try:
        return create_client(settings.supabase_url, settings.supabase_key)
    except Exception:
        return None
