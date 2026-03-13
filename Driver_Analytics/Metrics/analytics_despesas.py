"""Despesas metrics (legacy module delegating to service)."""

from __future__ import annotations

import pandas as pd

from domain.validators import safe_divide
from services.metrics_service import MetricsService


_metrics = MetricsService()


def despesa_total(df):
    return _metrics.despesa_total(df)


def despesa_media(df):
    return _metrics.despesa_media(df)


def despesa_por_categoria(df):
    serie = _metrics.despesa_por_categoria(df)
    return None if serie.empty else serie


def percentual_por_categoria(df):
    serie = _metrics.despesa_por_categoria(df)
    if serie.empty:
        return None
    total = float(serie.sum())
    if total == 0:
        return serie * 0
    return (serie / total * 100).sort_values(ascending=False)


def km_total(df_receitas):
    return _metrics.km_total(df_receitas)


def custo_por_km(df_despesas, df_receitas):
    return float(safe_divide(despesa_total(df_despesas), km_total(df_receitas), default=0.0))


def evolucao_mensal(df):
    if df is None or getattr(df, "empty", True) or "data" not in df.columns or "valor" not in df.columns:
        return None
    work_df = df.copy()
    work_df["data"] = pd.to_datetime(work_df["data"], errors="coerce")
    work_df["mes_ano"] = work_df["data"].dt.to_period("M")
    return work_df.groupby("mes_ano")["valor"].sum().sort_index()


def pareto_despesas(df):
    serie = _metrics.despesa_por_categoria(df)
    if serie.empty:
        return None
    out = serie.to_frame(name="Total").reset_index().rename(columns={"categoria": "Categoria"})
    total = float(out["Total"].sum())
    out["Percentual"] = out["Total"] / total * 100 if total else 0.0
    out["Acumulado"] = out["Percentual"].cumsum()
    return out
