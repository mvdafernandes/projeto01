"""Legacy compatibility wrapper for Supabase client."""

from core.database import get_supabase_client


def get_supabase():
    """Backward compatible alias."""

    return get_supabase_client()
