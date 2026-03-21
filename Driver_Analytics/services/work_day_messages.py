"""Neutral message helpers for work day flows."""

from __future__ import annotations


WORK_DAY_MIGRATION_FILE = "sql/migrations/20260316130000__add_work_days_module.sql"
WORK_KM_MIGRATION_FILE = "sql/migrations/20260317090000__add_daily_goal_and_work_km_periods.sql"


def work_day_bootstrap_message(exc: Exception) -> str:
    message = str(exc or "")
    if "work_days" in message or "work_day_events" in message or "work_km_periods" in message:
        return (
            "O modulo Jornada ainda nao esta disponivel neste ambiente. "
            f"Aplique as migrations `{WORK_DAY_MIGRATION_FILE}` e `{WORK_KM_MIGRATION_FILE}` no projeto Supabase usado pelo deploy e reinicie o app."
        )
    return f"Falha ao carregar Jornada: {message}"
