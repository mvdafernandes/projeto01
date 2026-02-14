"""Centralized runtime configuration for Streamlit/Supabase."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import streamlit as st
except Exception:  # pragma: no cover - allows tests without Streamlit runtime
    st = None


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from env vars and Streamlit secrets."""

    supabase_url: str = ""
    supabase_key: str = ""
    db_name: str = "driver_analytics.db"
    users_file: str = ".streamlit/users.json"


if st and hasattr(st, "cache_data"):
    cache_data = st.cache_data
else:
    def cache_data(func):
        return func


if st and hasattr(st, "cache_resource"):
    cache_resource = st.cache_resource
else:
    def cache_resource(func):
        return func


def _get_secret(key: str, default: str = "") -> str:
    """Read a secret from Streamlit when available."""

    if st is None:
        return default

    try:
        value = st.secrets.get(key, default)
    except Exception:
        return default

    return str(value).strip() if value is not None else default


@cache_data
def get_settings() -> Settings:
    """Load effective settings once per cache cycle."""

    return Settings(
        supabase_url=(os.getenv("SUPABASE_URL") or _get_secret("SUPABASE_URL", "")).strip(),
        supabase_key=(os.getenv("SUPABASE_KEY") or _get_secret("SUPABASE_KEY", "")).strip(),
        db_name=(os.getenv("DRIVER_ANALYTICS_DB") or "driver_analytics.db").strip(),
        users_file=(os.getenv("DRIVER_ANALYTICS_USERS_FILE") or ".streamlit/users.json").strip(),
    )
