"""Reusable validation and sanitation utilities."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

import pandas as pd


DATE_FORMAT = "%Y-%m-%d"


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert to float safely, replacing invalid values by default."""

    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convert to int safely, replacing invalid values by default."""

    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def safe_divide(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """Guarded division that prevents divide-by-zero and invalid operations."""

    num = safe_float(numerator, default=0.0)
    den = safe_float(denominator, default=0.0)
    if den == 0:
        return default
    return num / den


def sanitize_nullable_text(value: Any) -> str:
    """Return text representation and replace null values with empty string."""

    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def validate_date(value: Any) -> bool:
    """Validate accepted date-like values."""

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return True

    if isinstance(value, str):
        try:
            datetime.strptime(value.strip(), DATE_FORMAT)
            return True
        except Exception:
            return False

    return False


def to_iso_date(value: Any, fallback: str = "") -> str:
    """Convert a date-like value into YYYY-MM-DD."""

    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        try:
            return pd.to_datetime(value, errors="coerce").date().isoformat()
        except Exception:
            return fallback

    return fallback


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Ensure DataFrame contains all expected columns."""

    safe_df = df.copy() if df is not None else pd.DataFrame()
    for col in columns:
        if col not in safe_df.columns:
            safe_df[col] = pd.Series(dtype="object")
    return safe_df.loc[:, list(columns)]


def parse_datetime_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Parse DataFrame column into pandas datetime safely."""

    safe_df = df.copy() if df is not None else pd.DataFrame()
    if column in safe_df.columns:
        safe_df[column] = pd.to_datetime(safe_df[column], errors="coerce")
    return safe_df


def validate_dataframe(df: pd.DataFrame | None, required_columns: Iterable[str]) -> pd.DataFrame:
    """Return safe DataFrame with expected columns and without None values."""

    safe_df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    safe_df = ensure_columns(safe_df, required_columns)
    return safe_df.fillna({col: 0 for col in safe_df.columns if col in {"valor", "km", "tempo trabalhado"}})
