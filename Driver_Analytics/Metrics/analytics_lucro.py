"""Lucro metrics (legacy module delegating to service)."""

from __future__ import annotations

from services.metrics_service import MetricsService


_metrics = MetricsService()


def receita_total(df_receitas):
    return _metrics.receita_total(df_receitas)


def despesa_total(df_despesas):
    return _metrics.despesa_total(df_despesas)


def lucro_bruto(df_receitas, df_despesas):
    return _metrics.lucro_bruto(df_receitas, df_despesas)


def lucro_medio_diario(df_receitas, df_despesas):
    return _metrics.lucro_medio_diario(df_receitas, df_despesas)


def margem_lucro(df_receitas, df_despesas):
    return _metrics.margem_lucro(df_receitas, df_despesas)


def km_total(df_receitas):
    return _metrics.km_total(df_receitas)


def lucro_por_km(df_receitas, df_despesas):
    return _metrics.lucro_por_km(df_receitas, df_despesas)


def ponto_equilibrio(df_despesas, receita_por_km=1.0):
    receita_km = float(receita_por_km or 0.0)
    if receita_km == 0:
        return float("inf")
    return float(_metrics.despesa_total(df_despesas) / receita_km)
