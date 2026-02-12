import pandas as pd
import numpy as np

# --------------------------------------------------
# BÁSICO
# --------------------------------------------------

def despesa_total(df):
    if df.empty:
        return 0
    return df["valor"].sum()


def despesa_media(df):
    if df.empty:
        return 0
    return df["valor"].mean()


# --------------------------------------------------
# POR CATEGORIA
# --------------------------------------------------

def despesa_por_categoria(df):
    if df.empty:
        return None
    return df.groupby("categoria")["valor"].sum().sort_values(ascending=False)


def percentual_por_categoria(df):
    if df.empty:
        return None

    total = despesa_total(df)
    grupo = df.groupby("categoria")["valor"].sum()
    return (grupo / total * 100).sort_values(ascending=False)


# --------------------------------------------------
# FIXO vs VARIÁVEL
# --------------------------------------------------

# Funções auxiliares para o cálculo de custo por KM
def km_total(df_receitas):
    if df_receitas.empty:
        return 0
    return df_receitas["km"].sum()


def custo_por_km(df_despesas, df_receitas):
    total_despesa = despesa_total(df_despesas)
    total_de_km = km_total(df_receitas)
    if total_de_km == 0:
        return 0
    return total_despesa / total_de_km


# --------------------------------------------------
# EVOLUÇÃO MENSAL
# --------------------------------------------------

def evolucao_mensal(df):
    if df.empty:
        return None

    df["data"] = pd.to_datetime(df["data"])
    df["mes_ano"] = df["data"].dt.to_period("M")
    return df.groupby("mes_ano")["valor"].sum().sort_index()


# --------------------------------------------------
# ANÁLISE DE PARETO (80/20)
# --------------------------------------------------

def pareto_despesas(df):
    if df.empty:
        return None

    df_categoria = df.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    df_categoria = df_categoria.to_frame(name="Total").reset_index()
    df_categoria["Percentual"] = df_categoria["Total"] / df_categoria["Total"].sum() * 100
    df_categoria["Acumulado"] = df_categoria["Percentual"].cumsum()
    return df_categoria