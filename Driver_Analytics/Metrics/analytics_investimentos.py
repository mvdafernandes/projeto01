import pandas as pd
import numpy as np

# --------------------------------------------------
# FUNÇÕES BÁSICAS
# --------------------------------------------------

def patrimonio_atual(df):
    if df.empty or "data" not in df.columns or "patrimonio_total" not in df.columns:
        return 0
    return df.sort_values("data")["patrimonio_total"].iloc[-1]


def patrimonio_inicial(df):
    if df.empty or "data" not in df.columns or "patrimonio_total" not in df.columns:
        return 0
    return df.sort_values("data")["patrimonio_total"].iloc[0]


def total_aportado(df):
    if df.empty or "aporte" not in df.columns:
        return 0
    return df["aporte"].sum()


def lucro_acumulado(df):
    return patrimonio_atual(df) - total_aportado(df)


def rentabilidade_percentual(df):
    aporte = total_aportado(df)
    if aporte == 0:
        return 0
    return (lucro_acumulado(df) / aporte) * 100


# --------------------------------------------------
# CAGR
# --------------------------------------------------

def calcular_cagr(df):
    """
    Calcula CAGR baseado no patrimônio inicial e final
    """

    if len(df) < 2 or "data" not in df.columns or "patrimonio_total" not in df.columns:
        return 0

    df = df.sort_values("data")

    valor_inicial = df["patrimonio_total"].iloc[0]
    valor_final = df["patrimonio_total"].iloc[-1]

    data_inicial = pd.to_datetime(df["data"].iloc[0])
    data_final = pd.to_datetime(df["data"].iloc[-1])

    anos = (data_final - data_inicial).days / 365.25

    if anos <= 0 or valor_inicial == 0:
        return 0

    cagr = (valor_final / valor_inicial) ** (1 / anos) - 1

    return cagr * 100


# --------------------------------------------------
# CDI
# --------------------------------------------------

def cdi_acumulado(df_cdi):
    if df_cdi.empty or "taxa_cdi_mensal" not in df_cdi.columns:
        return 0
    return (np.prod(1 + df_cdi["taxa_cdi_mensal"]) - 1) * 100


def percentual_do_cdi(df_invest, df_cdi):
    rent = rentabilidade_percentual(df_invest)
    cdi = cdi_acumulado(df_cdi)
    if cdi == 0:
        return 0
    return (rent / cdi) * 100


# --------------------------------------------------
# PROJEÇÃO
# --------------------------------------------------

def projecao_com_aporte(df_invest, taxa_mensal, meses, aporte_mensal):
    P = patrimonio_atual(df_invest)
    i = taxa_mensal
    n = meses
    A = aporte_mensal

    if i == 0:
        return P + A * n

    return P * (1 + i) ** n + A * (((1 + i) ** n - 1) / i)
