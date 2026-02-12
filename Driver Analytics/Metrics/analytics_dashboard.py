import pandas as pd
from Metrics.analytics_receitas import (
    receita_total,
    dias_trabalhados,
    percentual_meta_batida,
    receita_por_km
)
from Metrics.analytics_lucro import (
    despesa_total,
    lucro_bruto,
    margem_lucro,
    lucro_por_km
)

# --------------------------------------------------
# FILTRO MÊS ATUAL
# --------------------------------------------------

def filtrar_mes_atual(df):
    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["data"])
    hoje = pd.Timestamp.today()

    return df[
        (df["data"].dt.month == hoje.month) &
        (df["data"].dt.year == hoje.year)
    ]


# --------------------------------------------------
# RESUMO EXECUTIVO
# --------------------------------------------------

def resumo_mensal(df_receitas, df_despesas):

    df_r = filtrar_mes_atual(df_receitas.copy())
    df_d = filtrar_mes_atual(df_despesas.copy())

    receita = receita_total(df_r)
    despesa = despesa_total(df_d)
    lucro = lucro_bruto(df_r, df_d)
    margem = margem_lucro(df_r, df_d)
    dias = dias_trabalhados(df_r)
    meta_pct = percentual_meta_batida(df_r)
    r_km = receita_por_km(df_r)
    l_km = lucro_por_km(df_r, df_d)

    return {
        "receita_total": receita,
        "despesa_total": despesa,
        "lucro": lucro,
        "margem_%": margem,
        "dias_trabalhados": dias,
        "%_meta_batida": meta_pct,
        "receita_por_km": r_km,
        "lucro_por_km": l_km
    }


# --------------------------------------------------
# SCORE DO MÊS
# --------------------------------------------------

def score_mensal(df_receitas, df_despesas):

    resumo = resumo_mensal(df_receitas, df_despesas)

    score = 0

    # Margem de lucro
    if resumo["margem_%"] >= 40:
        score += 30
    elif resumo["margem_%"] >= 25:
        score += 20
    else:
        score += 10

    # Meta diária
    if resumo["%_meta_batida"] >= 80:
        score += 30
    elif resumo["%_meta_batida"] >= 50:
        score += 20
    else:
        score += 10

    # Receita por KM
    if resumo["receita_por_km"] >= 3:
        score += 20
    else:
        score += 10

    # Lucro positivo
    if resumo["lucro"] > 0:
        score += 20

    return score
