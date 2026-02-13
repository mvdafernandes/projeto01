import pandas as pd
import numpy as np

# --------------------------------------------------
# FUNÇÕES AUXILIARES
# --------------------------------------------------

def receita_total(df_receitas):
    if df_receitas.empty or "valor" not in df_receitas.columns:
        return 0
    return df_receitas["valor"].sum()


def despesa_total(df_despesas):
    if df_despesas.empty or "valor" not in df_despesas.columns:
        return 0
    return df_despesas["valor"].sum()


# --------------------------------------------------
# LUCRO
# --------------------------------------------------

def lucro_bruto(df_receitas, df_despesas):
    return receita_total(df_receitas) - despesa_total(df_despesas)


def lucro_medio_diario(df_receitas, df_despesas):
    dias = df_receitas.shape[0]
    if dias == 0:
        return 0
    return lucro_bruto(df_receitas, df_despesas) / dias


def margem_lucro(df_receitas, df_despesas):
    receita = receita_total(df_receitas)
    if receita == 0:
        return 0
    return (lucro_bruto(df_receitas, df_despesas) / receita) * 100


# --------------------------------------------------
# KM
# --------------------------------------------------

def km_total(df_receitas):
    if df_receitas.empty or "km" not in df_receitas.columns:
        return 0
    return df_receitas["km"].sum()


def lucro_por_km(df_receitas, df_despesas):
    total_km = km_total(df_receitas)
    if total_km == 0:
        return 0
    return lucro_bruto(df_receitas, df_despesas) / total_km


def ponto_equilibrio(df_despesas, receita_por_km=1.0):
    # Assumindo uma receita_por_km para o cálculo do ponto de equilíbrio
    despesas = despesa_total(df_despesas)
    if receita_por_km == 0:
        return float('inf') # Retorna infinito se não houver receita por km
    return despesas / receita_por_km
