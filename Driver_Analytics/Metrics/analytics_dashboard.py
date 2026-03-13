"""Dashboard metrics (legacy module delegating to service)."""

from __future__ import annotations

import pandas as pd

from services.metrics_service import MetricsService


_metrics = MetricsService()


def filtrar_mes_atual(df):
    if df is None:
        return pd.DataFrame()
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    return _metrics.filtrar_mes_atual(df)


def resumo_mensal(df_receitas, df_despesas):
    return _metrics.resumo_mensal(df_receitas, df_despesas)


def score_mensal(df_receitas, df_despesas):
    return _metrics.score_mensal(df_receitas, df_despesas)
