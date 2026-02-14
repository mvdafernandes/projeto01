"""Cadastros UI page."""

from __future__ import annotations

from datetime import time

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from UI.components import titulo_secao


service = DashboardService()


def _safe_date_or_none(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _safe_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _date_or_today(value):
    date_value = _safe_date_or_none(value)
    if date_value is None:
        return pd.Timestamp.today().date()
    return date_value


def _time_from_seconds(value) -> time:
    total = max(0, _safe_int(value))
    horas = (total // 3600) % 24
    minutos = (total % 3600) // 60
    segundos = total % 60
    return time(horas, minutos, segundos)


def _get_row_by_id(df: pd.DataFrame, selected_id: int | None) -> pd.Series | None:
    if selected_id is None or df.empty or "id" not in df.columns:
        return None
    row = df[df["id"] == int(selected_id)]
    if row.empty:
        return None
    return row.iloc[0]


def _set_receita_fields(row: pd.Series | None) -> None:
    st.session_state["cad_receita_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_receita_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_receita_km"] = float(row["km"]) if row is not None else 0.0
    st.session_state["cad_receita_tempo"] = _time_from_seconds(row["tempo trabalhado"] if row is not None else 0)
    st.session_state["cad_receita_obs"] = str(row["observacao"]) if row is not None else ""


def _set_despesa_fields(row: pd.Series | None) -> None:
    st.session_state["cad_despesa_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_despesa_categoria"] = str(row["categoria"]) if row is not None else ""
    st.session_state["cad_despesa_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_despesa_obs"] = str(row["observacao"]) if row is not None else ""


def _set_investimento_fields(row: pd.Series | None) -> None:
    st.session_state["cad_invest_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_invest_aporte"] = float(row["aporte"]) if row is not None else 0.0
    st.session_state["cad_invest_rendimento"] = float(row["rendimento"]) if row is not None else 0.0
    st.session_state["cad_invest_patrimonio"] = float(row["patrimonio total"]) if row is not None else 0.0


def _sync_edit_state(df: pd.DataFrame, select_key: str, last_key: str, setter) -> int | None:
    selected_id = st.session_state.get(select_key)
    last_selected = st.session_state.get(last_key)
    if selected_id != last_selected:
        setter(_get_row_by_id(df, selected_id))
        st.session_state[last_key] = selected_id
    return selected_id


def _receita_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    return f"ID {item_id} | {data_txt} | R$ {float(row['valor']):.2f}"


def _despesa_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    categoria = str(row["categoria"]).strip() or "Sem categoria"
    return f"ID {item_id} | {data_txt} | {categoria}"


def _investimento_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return f"ID {item_id}"
    data_txt = _date_or_today(row["data"]).isoformat()
    return f"ID {item_id} | {data_txt} | Aporte R$ {float(row['aporte']):.2f}"


def pagina_cadastros() -> None:
    st.header("Cadastros")

    tab_receitas, tab_despesas, tab_investimentos = st.tabs(["Receitas", "Despesas", "Investimentos"])

    with tab_receitas:
        titulo_secao("CRUD de Receitas")
        df_receitas = service.listar_receitas()
        if not df_receitas.empty and "id" in df_receitas.columns:
            df_receitas = df_receitas.sort_values(by="id", ascending=False)
        options = [None] + (df_receitas["id"].astype(int).tolist() if "id" in df_receitas.columns else [])
        with st.form("cad_receita_form"):
            st.selectbox(
                "Registro",
                options=options,
                format_func=lambda x: _receita_label(df_receitas, x),
                key="cad_receita_selected_id",
            )
            _sync_edit_state(df_receitas, "cad_receita_selected_id", "cad_receita_last_selected_id", _set_receita_fields)
            data = st.date_input("Data", key="cad_receita_data")
            valor = st.number_input("Valor", min_value=0.0, key="cad_receita_valor")
            km = st.number_input("KM", min_value=0.0, key="cad_receita_km")
            tempo = st.time_input("Tempo trabalhado (hh:mm:ss)", value=time(0, 0, 0), key="cad_receita_tempo")
            observacao = st.text_input("Observação", key="cad_receita_obs")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_receita_confirmar_exclusao")
            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_receita_selected_id")
            data_valida = _safe_date_or_none(data)
            tempo_total = tempo.hour * 3600 + tempo.minute * 60 + tempo.second

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.criar_receita(data_valida.isoformat(), float(valor), float(km), int(tempo_total), observacao)
                        st.success("Receita salva com sucesso.")
                        st.session_state["cad_receita_selected_id"] = None
                        st.rerun()
                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.atualizar_receita(int(selected_id), data_valida.isoformat(), float(valor), float(km), int(tempo_total), observacao)
                        st.success("Receita atualizada com sucesso.")
                        st.rerun()
                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_receita(int(selected_id))
                        st.success("Receita excluída com sucesso.")
                        st.session_state["cad_receita_selected_id"] = None
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar receita: {exc}")

    with tab_despesas:
        titulo_secao("CRUD de Despesas")
        df_despesas = service.listar_despesas()
        if not df_despesas.empty and "id" in df_despesas.columns:
            df_despesas = df_despesas.sort_values(by="id", ascending=False)
        options = [None] + (df_despesas["id"].astype(int).tolist() if "id" in df_despesas.columns else [])
        with st.form("cad_despesa_form"):
            st.selectbox(
                "Registro",
                options=options,
                format_func=lambda x: _despesa_label(df_despesas, x),
                key="cad_despesa_selected_id",
            )
            _sync_edit_state(df_despesas, "cad_despesa_selected_id", "cad_despesa_last_selected_id", _set_despesa_fields)
            data = st.date_input("Data", key="cad_despesa_data")
            categoria = st.text_input("Categoria", key="cad_despesa_categoria")
            valor = st.number_input("Valor", min_value=0.0, key="cad_despesa_valor")
            observacao = st.text_input("Observação", key="cad_despesa_obs")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_despesa_confirmar_exclusao")
            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_despesa_selected_id")
            data_valida = _safe_date_or_none(data)

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif not str(categoria).strip():
                        st.warning("Informe uma categoria válida.")
                    else:
                        service.criar_despesa(data_valida.isoformat(), str(categoria).strip(), float(valor), observacao)
                        st.success("Despesa salva com sucesso.")
                        st.session_state["cad_despesa_selected_id"] = None
                        st.rerun()
                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    elif not str(categoria).strip():
                        st.warning("Informe uma categoria válida.")
                    else:
                        service.atualizar_despesa(int(selected_id), data_valida.isoformat(), str(categoria).strip(), float(valor), observacao)
                        st.success("Despesa atualizada com sucesso.")
                        st.rerun()
                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_despesa(int(selected_id))
                        st.success("Despesa excluída com sucesso.")
                        st.session_state["cad_despesa_selected_id"] = None
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar despesa: {exc}")

    with tab_investimentos:
        titulo_secao("CRUD de Investimentos")
        df_investimentos = service.listar_investimentos()
        if not df_investimentos.empty and "id" in df_investimentos.columns:
            df_investimentos = df_investimentos.sort_values(by="id", ascending=False)
        options = [None] + (df_investimentos["id"].astype(int).tolist() if "id" in df_investimentos.columns else [])
        with st.form("cad_investimento_form"):
            st.selectbox(
                "Registro",
                options=options,
                format_func=lambda x: _investimento_label(df_investimentos, x),
                key="cad_invest_selected_id",
            )
            _sync_edit_state(df_investimentos, "cad_invest_selected_id", "cad_invest_last_selected_id", _set_investimento_fields)
            data = st.date_input("Data", key="cad_invest_data")
            aporte = st.number_input("Aporte", min_value=0.0, key="cad_invest_aporte")
            rendimento = st.number_input("Rendimento", min_value=0.0, key="cad_invest_rendimento")
            patrimonio_total = st.number_input("Patrimônio total", min_value=0.0, key="cad_invest_patrimonio")
            confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_invest_confirmar_exclusao")
            col1, col2, col3 = st.columns(3)
            salvar = col1.form_submit_button("Salvar (novo)")
            atualizar = col2.form_submit_button("Atualizar")
            excluir = col3.form_submit_button("Excluir")

            selected_id = st.session_state.get("cad_invest_selected_id")
            data_valida = _safe_date_or_none(data)

            try:
                if salvar:
                    if data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.criar_investimento(data_valida.isoformat(), float(aporte), 0.0, float(rendimento), float(patrimonio_total))
                        st.success("Investimento salvo com sucesso.")
                        st.session_state["cad_invest_selected_id"] = None
                        st.rerun()
                if atualizar:
                    if selected_id is None:
                        st.warning("Selecione um registro para atualizar.")
                    elif data_valida is None:
                        st.warning("Selecione uma data válida.")
                    else:
                        service.atualizar_investimento(
                            int(selected_id),
                            data_valida.isoformat(),
                            float(aporte),
                            0.0,
                            float(rendimento),
                            float(patrimonio_total),
                        )
                        st.success("Investimento atualizado com sucesso.")
                        st.rerun()
                if excluir:
                    if selected_id is None:
                        st.warning("Selecione um registro para excluir.")
                    elif not confirmar_exclusao:
                        st.warning("Confirme a exclusão para continuar.")
                    else:
                        service.deletar_investimento(int(selected_id))
                        st.success("Investimento excluído com sucesso.")
                        st.session_state["cad_invest_selected_id"] = None
                        st.rerun()
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f"Erro ao processar investimento: {exc}")
