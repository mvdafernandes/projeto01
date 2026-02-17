"""Controle UI page for total driven kilometers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import show_empty_data, titulo_secao


service = DashboardService()


def _safe_date_or_none(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _get_row_by_id(df: pd.DataFrame, selected_id: int | None) -> pd.Series | None:
    if selected_id is None or df.empty or "id" not in df.columns:
        return None
    row = df[df["id"] == int(selected_id)]
    if row.empty:
        return None
    return row.iloc[0]


def pagina_controle() -> None:
    st.header("Controle")
    titulo_secao("KM Total Rodado")

    df = service.listar_controle_km()
    if not df.empty and "id" in df.columns:
        df = df.sort_values(by="id", ascending=False)

    options = [None] + (df["id"].astype(int).tolist() if "id" in df.columns else [])
    selected_id = st.selectbox("Registro", options=options, key="ctrl_selected_id")
    row = _get_row_by_id(df, selected_id)

    today = pd.Timestamp.today().date()
    data_inicio_default = today if row is None else pd.to_datetime(row.get("data_inicio"), errors="coerce").date()
    data_fim_default = today if row is None else pd.to_datetime(row.get("data_fim"), errors="coerce").date()
    km_default = 0.0 if row is None else float(pd.to_numeric(row.get("km_total_rodado", 0.0), errors="coerce"))

    with st.form("ctrl_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            data_inicio = st.date_input("Data inicial", value=data_inicio_default, key="ctrl_data_inicio")
        with col_b:
            data_fim = st.date_input("Data final/atualização", value=data_fim_default, key="ctrl_data_fim")
        km_total_rodado = st.number_input("KM total rodado", min_value=0.0, value=float(km_default), key="ctrl_km_total")
        confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="ctrl_confirmar_exclusao")

        col1, col2, col3 = st.columns(3)
        salvar = col1.form_submit_button("Salvar (novo)")
        atualizar = col2.form_submit_button("Atualizar")
        excluir = col3.form_submit_button("Excluir")

        data_inicio_valida = _safe_date_or_none(data_inicio)
        data_fim_valida = _safe_date_or_none(data_fim)
        try:
            if salvar:
                if data_inicio_valida is None or data_fim_valida is None:
                    st.warning("Selecione datas válidas.")
                elif data_fim_valida < data_inicio_valida:
                    st.warning("A data final deve ser maior ou igual à data inicial.")
                else:
                    service.criar_controle_km(data_inicio_valida.isoformat(), data_fim_valida.isoformat(), float(km_total_rodado))
                    st.success("Controle salvo com sucesso.")
                    st.rerun()

            if atualizar:
                if selected_id is None:
                    st.warning("Selecione um registro para atualizar.")
                elif data_inicio_valida is None or data_fim_valida is None:
                    st.warning("Selecione datas válidas.")
                elif data_fim_valida < data_inicio_valida:
                    st.warning("A data final deve ser maior ou igual à data inicial.")
                else:
                    service.atualizar_controle_km(
                        int(selected_id),
                        data_inicio_valida.isoformat(),
                        data_fim_valida.isoformat(),
                        float(km_total_rodado),
                    )
                    st.success("Controle atualizado com sucesso.")
                    st.rerun()

            if excluir:
                if selected_id is None:
                    st.warning("Selecione um registro para excluir.")
                elif not confirmar_exclusao:
                    st.warning("Confirme a exclusão para continuar.")
                else:
                    service.deletar_controle_km(int(selected_id))
                    st.success("Registro excluído com sucesso.")
                    st.rerun()
        except Exception as exc:
            st.error(f"Erro ao processar controle: {exc}")

    titulo_secao("Registros")
    if df.empty:
        show_empty_data("Sem registros de controle.")
    else:
        tabela = df.copy()
        if "data_inicio" in tabela.columns:
            tabela["data_inicio"] = pd.to_datetime(tabela["data_inicio"], errors="coerce").dt.date
        if "data_fim" in tabela.columns:
            tabela["data_fim"] = pd.to_datetime(tabela["data_fim"], errors="coerce").dt.date
        tabela["km_total_rodado"] = pd.to_numeric(tabela["km_total_rodado"], errors="coerce").fillna(0.0).map(
            lambda x: f"{x:.2f}"
        )
        st.dataframe(tabela, width="stretch")
