"""Receitas metrics (legacy module delegating to service)."""

from __future__ import annotations

import pandas as pd

from services.metrics_service import MetricsService


_metrics = MetricsService()


def filtrar_por_periodo(df, data_inicio=None, data_fim=None):
    if df is None or getattr(df, "empty", True) or "data" not in df.columns:
        return pd.DataFrame() if df is None else df

    work_df = df.copy()
    work_df["data"] = pd.to_datetime(work_df["data"], errors="coerce")
    if data_inicio:
        work_df = work_df[work_df["data"] >= pd.to_datetime(data_inicio)]
    if data_fim:
        work_df = work_df[work_df["data"] <= pd.to_datetime(data_fim)]
    return work_df


def receita_total(df):
    return _metrics.receita_total(df)


def receita_media_diaria(df):
    return _metrics.receita_media_diaria(df)


def receita_maxima(df):
    if df is None or getattr(df, "empty", True) or "valor" not in df.columns:
        return 0.0
    return float(pd.to_numeric(df["valor"], errors="coerce").fillna(0.0).max())


def receita_minima(df):
    if df is None or getattr(df, "empty", True) or "valor" not in df.columns:
        return 0.0
    return float(pd.to_numeric(df["valor"], errors="coerce").fillna(0.0).min())


def km_total(df):
    return _metrics.km_total(df)


def receita_por_km(df):
    return _metrics.receita_por_km(df)


def dias_trabalhados(df):
    return _metrics.dias_trabalhados(df)


def dias_meta_batida(df, meta=300):
    return _metrics.dias_meta_batida(df, meta)


def percentual_meta_batida(df, meta=300):
    return _metrics.percentual_meta_batida(df, meta)


def desvio_padrao_receita(df):
    if df is None or getattr(df, "empty", True) or "valor" not in df.columns or len(df) < 2:
        return 0.0
    return float(pd.to_numeric(df["valor"], errors="coerce").fillna(0.0).std())


def coeficiente_variacao(df):
    media = receita_media_diaria(df)
    if media == 0:
        return 0.0
    return float((desvio_padrao_receita(df) / media) * 100)
