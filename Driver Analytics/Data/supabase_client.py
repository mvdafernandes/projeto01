import os


def _get_secret(key):
    try:
        import streamlit as st
    except Exception:
        return None

    try:
        return st.secrets.get(key)
    except Exception:
        return None


def get_supabase():
    url = os.environ.get("SUPABASE_URL") or _get_secret("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or _get_secret("SUPABASE_KEY")
    if not url or not key:
        return None

    from supabase import create_client

    return create_client(url, key)
