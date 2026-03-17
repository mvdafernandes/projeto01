"""Shared form helpers plus backup UI page."""

from __future__ import annotations

from datetime import datetime, time

import pandas as pd
import streamlit as st

from services.dashboard_service import DashboardService
from services.backup_service import BackupService
from UI.components import formatar_moeda, titulo_secao


service = DashboardService()
backup_service = BackupService()
INVEST_CATEGORIAS = ["Renda Fixa", "Renda Variável"]
DESPESAS_CATEGORIAS_NEGOCIO = sorted(
    [
        "Combustível",
        "Estacionamento",
        "Financiamento",
        "Impostos CNPJ",
        "IPVA",
        "Lava-Jato",
        "Manutenção",
        "Multas",
        "Pedágio",
        "Seguro",
        "Telefonia",
    ]
)
DESPESAS_CATEGORIAS_PESSOAL = sorted(
    [
        "Alimentação",
        "Contas da Casa",
        "Educação",
        "Faturas de Cartão",
        "Impostos CPF",
        "Lazer",
        "Outros",
        "Plano de Saúde",
        "Serviços Domésticos",
    ]
)
TIPOS_DESPESA_LABELS = {
    "VARIAVEL": "Variável",
    "RECORRENTE": "Recorrente",
    "FIXA": "Fixa",
}
TIPOS_DESPESA_OPTIONS = list(TIPOS_DESPESA_LABELS.values())
ESFERAS_DESPESA_LABELS = {
    "NEGOCIO": "Negócio",
    "PESSOAL": "Pessoal",
}
ESFERAS_DESPESA_OPTIONS = list(ESFERAS_DESPESA_LABELS.values())
RECORRENCIA_DESPESA_LABELS = {
    "INDETERMINADO": "Indeterminado",
    "PERSONALIZADO": "Personalizado (N meses)",
}
RECORRENCIA_DESPESA_OPTIONS = list(RECORRENCIA_DESPESA_LABELS.values())


def _categorias_por_esfera(esfera_label: str) -> list[str]:
    if str(esfera_label).strip().lower() == "pessoal":
        return DESPESAS_CATEGORIAS_PESSOAL
    return DESPESAS_CATEGORIAS_NEGOCIO


def _sync_categoria_despesa_por_esfera() -> None:
    esfera_label = str(st.session_state.get("cad_despesa_esfera", "Negócio"))
    categorias = _categorias_por_esfera(esfera_label)
    categoria_default = "Outros" if "Outros" in categorias else (categorias[0] if categorias else "")
    ultima_esfera = str(st.session_state.get("cad_despesa_last_esfera", ""))
    categoria_atual = str(st.session_state.get("cad_despesa_categoria_select", ""))

    if esfera_label != ultima_esfera:
        st.session_state["cad_despesa_categoria_select"] = categoria_default
    elif categoria_atual not in categorias:
        st.session_state["cad_despesa_categoria_select"] = categoria_default

    st.session_state["cad_despesa_last_esfera"] = esfera_label


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


def _reset_fields(keys: list[str]) -> None:
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def _set_receita_fields(row: pd.Series | None) -> None:
    st.session_state["cad_receita_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_receita_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_receita_km"] = float(row["km"]) if row is not None else 0.0
    st.session_state["cad_receita_tempo"] = _time_from_seconds(row["tempo trabalhado"] if row is not None else 0)
    st.session_state["cad_receita_obs"] = str(row.get("observacao", "")) if row is not None else ""
    st.session_state["cad_receita_confirmar_exclusao"] = False


def _set_despesa_fields(row: pd.Series | None) -> None:
    st.session_state["cad_despesa_data"] = _date_or_today(row["data"] if row is not None else None)
    tipo_raw = str(row.get("tipo_despesa", "VARIAVEL")) if row is not None else "VARIAVEL"
    tipo_key = tipo_raw.strip().upper() if tipo_raw.strip().upper() in TIPOS_DESPESA_LABELS else "VARIAVEL"
    st.session_state["cad_despesa_tipo"] = TIPOS_DESPESA_LABELS[tipo_key]
    esfera_raw = str(row.get("esfera_despesa", "NEGOCIO")) if row is not None else "NEGOCIO"
    esfera_key = esfera_raw.strip().upper() if esfera_raw.strip().upper() in ESFERAS_DESPESA_LABELS else "NEGOCIO"
    esfera_label = ESFERAS_DESPESA_LABELS[esfera_key]
    st.session_state["cad_despesa_esfera"] = esfera_label
    st.session_state["cad_despesa_last_esfera"] = esfera_label
    categorias_validas = _categorias_por_esfera(esfera_label)
    categoria = str(row["categoria"]) if row is not None else "Outros"
    st.session_state["cad_despesa_categoria_select"] = (
        categoria if categoria in categorias_validas else "Outros"
    )
    st.session_state["cad_despesa_valor"] = float(row["valor"]) if row is not None else 0.0
    st.session_state["cad_despesa_litros"] = float(row.get("litros", 0.0)) if row is not None else 0.0
    st.session_state["cad_despesa_obs"] = str(row.get("observacao", "")) if row is not None else ""
    st.session_state["cad_despesa_subcategoria_fixa"] = str(row.get("subcategoria_fixa", "")) if row is not None else ""
    recorrencia_raw = str(row.get("recorrencia_tipo", "INDETERMINADO")) if row is not None else "INDETERMINADO"
    recorrencia_key = (
        recorrencia_raw.strip().upper() if recorrencia_raw.strip().upper() in RECORRENCIA_DESPESA_LABELS else "INDETERMINADO"
    )
    st.session_state["cad_despesa_recorrencia_tipo"] = RECORRENCIA_DESPESA_LABELS[recorrencia_key]
    st.session_state["cad_despesa_recorrencia_meses"] = max(_safe_int(row.get("recorrencia_meses", 0)) if row is not None else 0, 1)
    st.session_state["cad_despesa_confirmar_exclusao"] = False


def _set_invest_aporte_fields(row: pd.Series | None) -> None:
    """Pre-fill aporte form state from selected investment row."""

    st.session_state["cad_inv_aporte_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_inv_aporte_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_inv_aporte_valor"] = float(row.get("aporte", 0.0)) if row is not None else 0.0
    st.session_state["cad_inv_aporte_patrimonio"] = float(row.get("patrimonio total", 0.0)) if row is not None else 0.0
    st.session_state["cad_inv_aporte_confirmar_exclusao"] = False


def _set_invest_rendimento_fields(row: pd.Series | None) -> None:
    """Pre-fill rendimento form state from selected investment row."""

    data_inicio = _date_or_today((row.get("data_inicio") if row is not None else None) or (row["data"] if row is not None else None))
    data_fim = _date_or_today((row.get("data_fim") if row is not None else None) or (row["data"] if row is not None else None))
    st.session_state["cad_inv_rend_data_inicio"] = data_inicio
    st.session_state["cad_inv_rend_data_fim"] = data_fim
    st.session_state["cad_inv_rend_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_inv_rend_rendimento"] = float(row["rendimento"]) if row is not None else 0.0
    st.session_state["cad_inv_rend_patrimonio"] = float(row["patrimonio total"]) if row is not None else 0.0
    st.session_state["cad_inv_rend_confirmar_exclusao"] = False


def _set_invest_retirada_fields(row: pd.Series | None) -> None:
    """Pre-fill retirada form state from selected investment row."""

    st.session_state["cad_inv_ret_data"] = _date_or_today(row["data"] if row is not None else None)
    st.session_state["cad_inv_ret_categoria"] = str(row.get("categoria", "Renda Fixa")) if row is not None else "Renda Fixa"
    st.session_state["cad_inv_ret_valor"] = abs(float(row.get("aporte", 0.0))) if row is not None else 0.0
    st.session_state["cad_inv_ret_patrimonio"] = float(row.get("patrimonio total", 0.0)) if row is not None else 0.0
    st.session_state["cad_inv_ret_confirmar_exclusao"] = False


def _sync_edit_state(df: pd.DataFrame, select_key: str, last_key: str, setter) -> int | None:
    selected_id = st.session_state.get(select_key)
    has_last = last_key in st.session_state
    last_selected = st.session_state.get(last_key)
    if (not has_last) or (selected_id != last_selected):
        setter(_get_row_by_id(df, selected_id))
        st.session_state[last_key] = selected_id
    return selected_id


def _ensure_selected_option(select_key: str, options: list[int | None]) -> None:
    current = st.session_state.get(select_key)
    if current not in options:
        st.session_state[select_key] = options[0] if options else None


def _sort_desc_by_id(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "id" not in df.columns:
        return df.copy()
    return df.sort_values(by="id", ascending=False).reset_index(drop=True)


def _display_record_number(df: pd.DataFrame, item_id: int | None) -> int | None:
    if item_id is None or df.empty or "id" not in df.columns:
        return None
    ordered = _sort_desc_by_id(df)
    matches = ordered.index[ordered["id"] == int(item_id)].tolist()
    return int(matches[0] + 1) if matches else None


def _with_display_order(df: pd.DataFrame, column_name: str = "registro") -> pd.DataFrame:
    ordered = _sort_desc_by_id(df)
    if ordered.empty:
        return ordered
    ordered[column_name] = range(1, len(ordered) + 1)
    return ordered


def _record_label(df: pd.DataFrame, item_id: int | None, summary: str) -> str:
    if item_id is None:
        return "Novo registro"
    display_number = _display_record_number(df, item_id)
    if display_number is None:
        return f"Registro ? | {summary}"
    return f"Registro {display_number} | {summary}"


def _receita_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return "Registro ?"
    data_txt = _date_or_today(row["data"]).isoformat()
    return _record_label(df, item_id, f"{data_txt} | {formatar_moeda(float(row['valor']))}")


def _despesa_label(df: pd.DataFrame, item_id: int | None) -> str:
    if item_id is None:
        return "Novo registro"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return "Registro ?"
    data_txt = _date_or_today(row["data"]).isoformat()
    categoria = str(row["categoria"]).strip() or "Sem categoria"
    return _record_label(df, item_id, f"{data_txt} | {categoria}")


def _investimento_rendimento_label(df: pd.DataFrame, item_id: int | None) -> str:
    """Build friendly label for rendimento-focused selection list."""

    if item_id is None:
        return "Novo lançamento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return "Registro ?"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    rendimento = formatar_moeda(float(row.get("rendimento", 0.0)))
    return _record_label(df, item_id, f"{data_txt} | {cat} | Rend. {rendimento}")


def _investimento_aporte_label(df: pd.DataFrame, item_id: int | None) -> str:
    """Build friendly label for aporte-focused selection list."""

    if item_id is None:
        return "Novo lançamento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return "Registro ?"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    aporte = formatar_moeda(float(row.get("aporte", 0.0)))
    return _record_label(df, item_id, f"{data_txt} | {cat} | Aporte {aporte}")


def _investimento_retirada_label(df: pd.DataFrame, item_id: int | None) -> str:
    """Build friendly label for retirada-focused selection list."""

    if item_id is None:
        return "Novo lançamento"
    row = _get_row_by_id(df, item_id)
    if row is None:
        return "Registro ?"
    data_txt = _date_or_today(row["data"]).isoformat()
    cat = str(row.get("categoria", "Renda Fixa"))
    retirada = formatar_moeda(abs(float(row.get("aporte", 0.0))))
    return _record_label(df, item_id, f"{data_txt} | {cat} | Retirada {retirada}")


def _patrimonio_atual(df: pd.DataFrame) -> float:
    """Return latest patrimonio total snapshot from dataframe."""

    if df is None or df.empty:
        return 0.0
    work = df.copy()
    work["data"] = pd.to_datetime(work["data"], errors="coerce")
    work["patrimonio total"] = pd.to_numeric(work.get("patrimonio total"), errors="coerce").fillna(0.0)
    work = work.sort_values(by=["data", "id"], ascending=[True, True])
    return float(work.iloc[-1]["patrimonio total"]) if not work.empty else 0.0


def render_receitas_cadastro() -> None:
    titulo_secao("Cadastro de Receitas")
    df_receitas = _sort_desc_by_id(service.listar_receitas())
    options = [None] + (df_receitas["id"].astype(int).tolist() if "id" in df_receitas.columns else [])
    st.selectbox("Registro", options=options, format_func=lambda x: _receita_label(df_receitas, x), key="cad_receita_selected_id")
    _sync_edit_state(df_receitas, "cad_receita_selected_id", "cad_receita_last_selected_id", _set_receita_fields)
    with st.form("cad_receita_form"):
        data = st.date_input("Data", key="cad_receita_data")
        valor = st.number_input("Valor", min_value=0.0, key="cad_receita_valor")
        observacao = st.text_input("Observação", key="cad_receita_obs")
        confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_receita_confirmar_exclusao")
        col1, col2, col3 = st.columns(3)
        salvar = col1.form_submit_button("Salvar (novo)")
        atualizar = col2.form_submit_button("Atualizar")
        excluir = col3.form_submit_button("Excluir")
        selected_id = st.session_state.get("cad_receita_selected_id")
        data_valida = _safe_date_or_none(data)
        try:
            if salvar:
                if data_valida is None:
                    st.warning("Selecione uma data válida.")
                else:
                    service.criar_receita(data_valida.isoformat(), float(valor), observacao=observacao)
                    st.success("Receita salva com sucesso.")
                    _reset_fields(["cad_receita_selected_id", "cad_receita_last_selected_id", "cad_receita_data", "cad_receita_valor", "cad_receita_km", "cad_receita_tempo", "cad_receita_obs", "cad_receita_confirmar_exclusao"])
                    st.rerun()
            if atualizar:
                if selected_id is None:
                    st.warning("Selecione um registro para atualizar.")
                elif data_valida is None:
                    st.warning("Selecione uma data válida.")
                else:
                    service.atualizar_receita(int(selected_id), data_valida.isoformat(), float(valor), observacao=observacao)
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
                    _reset_fields(["cad_receita_selected_id", "cad_receita_last_selected_id", "cad_receita_confirmar_exclusao"])
                    st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"Erro ao processar receita: {exc}")


def render_despesas_cadastro() -> None:
    titulo_secao("Cadastro de Despesas")
    df_despesas = _sort_desc_by_id(service.listar_despesas())
    options = [None] + (df_despesas["id"].astype(int).tolist() if "id" in df_despesas.columns else [])
    st.selectbox("Registro", options=options, format_func=lambda x: _despesa_label(df_despesas, x), key="cad_despesa_selected_id")
    _sync_edit_state(df_despesas, "cad_despesa_selected_id", "cad_despesa_last_selected_id", _set_despesa_fields)
    st.selectbox("Escopo da despesa", options=ESFERAS_DESPESA_OPTIONS, key="cad_despesa_esfera")
    _sync_categoria_despesa_por_esfera()
    categorias_despesa = _categorias_por_esfera(str(st.session_state.get("cad_despesa_esfera", "Negócio")))
    with st.form("cad_despesa_form"):
        data = st.date_input("Data", key="cad_despesa_data")
        categoria_escolhida = st.selectbox("Categoria", options=categorias_despesa, key="cad_despesa_categoria_select")
        tipo_despesa_label = st.selectbox("Tipo de despesa", options=TIPOS_DESPESA_OPTIONS, key="cad_despesa_tipo")
        recorrencia_label = RECORRENCIA_DESPESA_LABELS["INDETERMINADO"]
        recorrencia_meses = 1
        if str(tipo_despesa_label).strip().lower() == "recorrente":
            recorrencia_label = st.selectbox("Recorrência", options=RECORRENCIA_DESPESA_OPTIONS, key="cad_despesa_recorrencia_tipo")
            if recorrencia_label == RECORRENCIA_DESPESA_LABELS["PERSONALIZADO"]:
                recorrencia_meses = int(st.number_input("Repetir por quantos meses", min_value=1, step=1, key="cad_despesa_recorrencia_meses"))
        subcategoria_fixa = ""
        if str(tipo_despesa_label).strip().lower() == "fixa":
            subcategoria_fixa = st.text_input("Subcategoria da conta fixa", key="cad_despesa_subcategoria_fixa", placeholder="Ex.: Aluguel, Internet, Energia")
        valor = st.number_input("Valor", min_value=0.0, key="cad_despesa_valor")
        categoria_normalizada = str(categoria_escolhida).strip().lower()
        if categoria_normalizada in {"combustível", "combustivel"}:
            litros = st.number_input("Litros abastecidos", min_value=0.0, step=0.1, key="cad_despesa_litros")
        else:
            litros = 0.0
            st.number_input("Litros abastecidos", value=0.0, disabled=True, key="cad_despesa_litros_disabled")
        observacao = st.text_input("Observação", key="cad_despesa_obs")
        confirmar_exclusao = st.checkbox("Confirmo a exclusão deste registro", key="cad_despesa_confirmar_exclusao")
        col1, col2, col3 = st.columns(3)
        salvar = col1.form_submit_button("Salvar (novo)")
        atualizar = col2.form_submit_button("Atualizar")
        excluir = col3.form_submit_button("Excluir")
        selected_id = st.session_state.get("cad_despesa_selected_id")
        data_valida = _safe_date_or_none(data)
        categoria_escolhida = str(categoria_escolhida).strip()
        tipo_despesa = {"Variável": "VARIAVEL", "Recorrente": "RECORRENTE", "Fixa": "FIXA"}.get(str(tipo_despesa_label), "VARIAVEL")
        esfera_despesa_label = str(st.session_state.get("cad_despesa_esfera", "Negócio"))
        esfera_despesa = {"Negócio": "NEGOCIO", "Pessoal": "PESSOAL"}.get(str(esfera_despesa_label), "NEGOCIO")
        subcategoria_fixa = str(subcategoria_fixa or "").strip()
        recorrencia_tipo = {"Indeterminado": "INDETERMINADO", "Personalizado (N meses)": "PERSONALIZADO"}.get(str(recorrencia_label), "INDETERMINADO")
        recorrencia_meses = int(recorrencia_meses or 1)
        selected_row = _get_row_by_id(df_despesas, selected_id)
        recorrencia_serie_id = str(selected_row.get("recorrencia_serie_id", "") if selected_row is not None else "").strip()
        try:
            if salvar:
                if data_valida is None:
                    st.warning("Selecione uma data válida.")
                elif not categoria_escolhida:
                    st.warning("Informe uma nova categoria ou selecione uma existente.")
                elif tipo_despesa == "FIXA" and not subcategoria_fixa and not str(observacao).strip():
                    st.warning("Para despesa fixa, informe subcategoria fixa ou observação.")
                else:
                    service.criar_despesa(data_valida.isoformat(), categoria_escolhida, float(valor), observacao, tipo_despesa=tipo_despesa, subcategoria_fixa=subcategoria_fixa, esfera_despesa=esfera_despesa, litros=float(litros), recorrencia_tipo=recorrencia_tipo, recorrencia_meses=recorrencia_meses)
                    st.success("Despesa salva com sucesso.")
                    _reset_fields(["cad_despesa_selected_id", "cad_despesa_last_selected_id", "cad_despesa_data", "cad_despesa_categoria_select", "cad_despesa_valor", "cad_despesa_obs", "cad_despesa_confirmar_exclusao", "cad_despesa_tipo", "cad_despesa_esfera", "cad_despesa_last_esfera", "cad_despesa_subcategoria_fixa", "cad_despesa_litros", "cad_despesa_recorrencia_tipo", "cad_despesa_recorrencia_meses", "cad_despesa_litros_disabled"])
                    st.rerun()
            if atualizar:
                if selected_id is None:
                    st.warning("Selecione um registro para atualizar.")
                elif data_valida is None:
                    st.warning("Selecione uma data válida.")
                elif not categoria_escolhida:
                    st.warning("Informe uma nova categoria ou selecione uma existente.")
                elif tipo_despesa == "FIXA" and not subcategoria_fixa and not str(observacao).strip():
                    st.warning("Para despesa fixa, informe subcategoria fixa ou observação.")
                else:
                    service.atualizar_despesa(int(selected_id), data_valida.isoformat(), categoria_escolhida, float(valor), observacao, tipo_despesa=tipo_despesa, subcategoria_fixa=subcategoria_fixa, esfera_despesa=esfera_despesa, litros=float(litros), recorrencia_tipo=recorrencia_tipo, recorrencia_meses=recorrencia_meses, recorrencia_serie_id=recorrencia_serie_id)
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
                    _reset_fields(["cad_despesa_selected_id", "cad_despesa_last_selected_id", "cad_despesa_confirmar_exclusao"])
                    st.rerun()
        except ValueError as exc:
            st.warning(str(exc))
        except Exception as exc:
            st.error(f"Erro ao processar despesa: {exc}")


def render_backup_section() -> None:
    titulo_secao("Backup e Restauração")
    st.caption("Exporte um backup completo dos seus dados e importe quando precisar restaurar. O formato é CSV versionado para facilitar recuperação.")
    try:
        payload = backup_service.export_payload()
        backup_bytes = backup_service.dumps_backup(payload)
        username_safe = (str(payload.get("username", "")).strip() or "usuario").replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"driver_analytics_backup_{username_safe}_{timestamp}.csv"
        st.download_button("Baixar backup (.csv)", data=backup_bytes, file_name=filename, mime="text/csv", key="backup_download_button")
        counts = payload.get("counts", {})
        if isinstance(counts, dict):
            st.caption(
                "Registros no backup: "
                f"receitas={int(counts.get('receitas', 0))}, "
                f"despesas={int(counts.get('despesas', 0))}, "
                f"investimentos={int(counts.get('investimentos', 0))}, "
                f"controle_km={int(counts.get('controle_km', 0))}, "
                f"controle_litros={int(counts.get('controle_litros', 0))}, "
                f"categorias={int(counts.get('categorias_despesas', 0))}."
            )
    except Exception as exc:
        st.error(f"Não foi possível gerar o backup: {exc}")
    with st.form("backup_import_form"):
        arquivo_backup = st.file_uploader("Importar backup (.csv)", type=["csv"], key="backup_file_uploader")
        replace_existing = st.checkbox("Substituir meus dados atuais antes de importar", value=True, key="backup_replace_existing")
        confirmar_import = st.checkbox("Confirmo que desejo importar esse arquivo", key="backup_confirm_import")
        importar_backup = st.form_submit_button("Importar backup")
        if importar_backup:
            if arquivo_backup is None:
                st.warning("Selecione um arquivo de backup para importar.")
            elif not confirmar_import:
                st.warning("Marque a confirmação antes de importar.")
            else:
                try:
                    payload_in = backup_service.loads_backup(arquivo_backup.getvalue())
                    resultado = backup_service.import_payload(payload_in, replace_existing=bool(replace_existing))
                    st.success(
                        "Importação concluída com sucesso. "
                        f"receitas={int(resultado.get('receitas', 0))}, "
                        f"despesas={int(resultado.get('despesas', 0))}, "
                        f"investimentos={int(resultado.get('investimentos', 0))}, "
                        f"controle_km={int(resultado.get('controle_km', 0))}, "
                        f"controle_litros={int(resultado.get('controle_litros', 0))}, "
                        f"categorias={int(resultado.get('categorias_despesas', 0))}."
                    )
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Erro ao importar backup: {exc}")


def pagina_backup() -> None:
    """Render backup page."""

    st.header("Backup")
    render_backup_section()


def pagina_cadastros() -> None:
    """Backward-compatible alias for older app imports."""

    pagina_backup()
