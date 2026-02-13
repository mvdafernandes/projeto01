import streamlit as st
import pandas as pd

from Data.CRUD import (
    inserir_receita,
    listar_receitas,
    atualizar_receita,
    deletar_receita,
)
from Metrics.analytics_receitas import (
    receita_total,
    receita_media_diaria,
    dias_trabalhados,
    percentual_meta_batida,
)
from UI.components import card_kpi, titulo_secao


def pagina_receitas():
    st.header("💰 Receitas")

    df = listar_receitas()
    if not df.empty and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"])
    if not df.empty and "tempo trabalhado" in df.columns:
        df["tempo trabalhado"] = pd.to_numeric(df["tempo trabalhado"], errors="coerce").fillna(0).astype(int)

    # -----------------------------
    # FILTRO MÊS
    # -----------------------------
    col1, col2 = st.columns(2)
    with col1:
        ano = st.number_input("Ano", min_value=2020, max_value=2100, value=pd.Timestamp.today().year)
    with col2:
        mes = st.number_input("Mês", min_value=1, max_value=12, value=pd.Timestamp.today().month)

    df_mes = df.copy()
    if not df_mes.empty and "data" in df_mes.columns:
        df_mes = df_mes[
            (df_mes["data"].dt.year == int(ano)) &
            (df_mes["data"].dt.month == int(mes))
        ]

    def _format_hms(total_seconds):
        total_seconds = int(total_seconds)
        horas = total_seconds // 3600
        minutos = (total_seconds % 3600) // 60
        segundos = total_seconds % 60
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    # -----------------------------
    # MÉTRICAS
    # -----------------------------
    titulo_secao("Resumo do Mês")

    total = receita_total(df_mes)
    media = receita_media_diaria(df_mes)
    dias = dias_trabalhados(df_mes)
    meta_pct = percentual_meta_batida(df_mes)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        card_kpi("Total", f"R$ {total:,.2f}")
    with col2:
        card_kpi("Média diária", f"R$ {media:,.2f}")
    with col3:
        card_kpi("Dias trabalhados", dias)
    with col4:
        card_kpi("% Meta 300", f"{meta_pct:.1f}%")

    # -----------------------------
    # GRÁFICO
    # -----------------------------
    titulo_secao("Evolução Diária")

    if not df_mes.empty and "data" in df_mes.columns and "valor" in df_mes.columns:
        resumo = df_mes.groupby("data")["valor"].sum()
        st.line_chart(resumo)
    else:
        st.info("Sem dados no período.")

    # -----------------------------
    # TABELA
    # -----------------------------
    titulo_secao("Registros")

    df_tabela = df_mes.copy()
    if not df_tabela.empty and "data" in df_tabela.columns:
        df_tabela["data"] = df_tabela["data"].dt.date
    if not df_tabela.empty and "tempo trabalhado" in df_tabela.columns:
        df_tabela["tempo trabalhado"] = df_tabela["tempo trabalhado"].apply(_format_hms)
    st.dataframe(df_tabela, width="stretch")

    # -----------------------------
    # FORMULÁRIO
    # -----------------------------
    titulo_secao("Adicionar Receita")

    with st.form("form_receita"):
        data = st.date_input("Data", key="data_r")
        valor = st.number_input("Valor", min_value=0.0, key="valor_r")
        km = st.number_input("KM", min_value=0.0, key="km_r")
        tempo = st.time_input("Tempo trabalhado (hh:mm:ss)", value=pd.Timestamp("00:00:00").time(), key="tempo_r")
        observacao = st.text_input("Observação", key="obs_r")

        submit = st.form_submit_button("Salvar")

        if submit:
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second
            inserir_receita(data.isoformat(), valor, km, tempo_total, observacao)
            st.success("Receita salva.")
            st.rerun()

    # -----------------------------
    # EDITAR / EXCLUIR
    # -----------------------------
    titulo_secao("Editar / Excluir Receita")

    if df_mes.empty:
        st.info("Sem dados no período para editar ou excluir.")
        return

    ids = df_mes["id"].tolist()
    receita_id = st.selectbox("Selecione o ID", ids, key="edit_id_r")
    registro = df_mes[df_mes["id"] == receita_id].iloc[0]

    with st.form("form_edit_receita"):
        data_e = st.date_input("Data", value=registro["data"].date(), key="edit_data_r")
        valor_e = st.number_input("Valor", min_value=0.0, value=float(registro["valor"]), key="edit_valor_r")
        km_e = st.number_input("KM", min_value=0.0, value=float(registro["km"]), key="edit_km_r")
        tempo_e = st.time_input(
            "Tempo trabalhado (hh:mm:ss)",
            value=pd.Timestamp(seconds=int(registro["tempo trabalhado"])).time(),
            key="edit_tempo_r",
        )
        observacao_e = st.text_input("Observação", value=str(registro.get("observacao", "")), key="edit_obs_r")

        col1, col2 = st.columns(2)
        with col1:
            salvar = st.form_submit_button("Atualizar")
        with col2:
            excluir = st.form_submit_button("Excluir")

        if salvar:
            tempo_total = tempo_e.hour * 3600 + tempo_e.minute * 60 + tempo_e.second
            atualizar_receita(
                int(receita_id),
                data_e.isoformat(),
                valor_e,
                km_e,
                tempo_total,
                observacao_e,
            )
            st.success("Receita atualizada.")
            st.rerun()
        if excluir:
            deletar_receita(int(receita_id))
            st.success("Receita excluída.")
            st.rerun()
