import pandas as pd
import numpy as np

# --------------------------------------------------
# FILTRO POR PERÍODO
# --------------------------------------------------

def filtrar_por_periodo(df, data_inicio=None, data_fim=None):
    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["data"])

    if data_inicio:
        df = df[df["data"] >= pd.to_datetime(data_inicio)]
    if data_fim:
        df = df[df["data"] <= pd.to_datetime(data_fim)]

    return df


# --------------------------------------------------
# MÉTRICAS BÁSICAS
# --------------------------------------------------

def receita_total(df):
    if df.empty:
        return 0
    return df["valor"].sum()


def receita_media_diaria(df):
    if df.empty:
        return 0
    return df["valor"].mean()


def receita_maxima(df):
    if df.empty:
        return 0
    return df["valor"].max()


def receita_minima(df):
    if df.empty:
        return 0
    return df["valor"].min()


# --------------------------------------------------
# KM
# --------------------------------------------------

def km_total(df):
    if df.empty:
        return 0
    return df["km"].sum()


def receita_por_km(df):
    total_km = km_total(df)
    if total_km == 0:
        return 0
    return receita_total(df) / total_km


# --------------------------------------------------
# META DIÁRIA (R$ 300)
# --------------------------------------------------

def dias_trabalhados(df):
    if df.empty:
        return 0
    return df.shape[0]


def dias_meta_batida(df, meta=300):
    if df.empty:
        return 0
    return df[df["valor"] >= meta].shape[0]


def percentual_meta_batida(df, meta=300):
    dias = dias_trabalhados(df)
    if dias == 0:
        return 0
    return (dias_meta_batida(df, meta) / dias) * 100

# Adicionando as funções que faltavam (desvio_padrao_receita, coeficiente_variacao)
def desvio_padrao_receita(df):
    if df.empty or len(df) < 2:
        return 0
    return df["valor"].std()

def coeficiente_variacao(df):
    media = receita_media_diaria(df)
    if media == 0:
        return 0
    return (desvio_padrao_receita(df) / media) * 100