"""Jornada de trabalho UI page."""

from __future__ import annotations

from datetime import date, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from UI.cadastros_ui import _ensure_selected_option, _reset_fields
from UI.components import render_kpi_grid, show_empty_data, titulo_secao
from services.work_day_messages import work_day_bootstrap_message
from services.work_day_service import WorkDayService


service = WorkDayService()
APP_TZ = ZoneInfo("America/Sao_Paulo")
STATUS_LABELS = {
    "open": "Em andamento",
    "closed": "Fechada",
    "partial": "Incompleta",
    "adjusted": "Ajustada",
    "manual": "Manual",
}
EVENT_LABELS = {
    "check_in": "Check-in",
    "check_out": "Check-out",
    "manual_create": "Criação manual",
    "manual_edit": "Edição manual",
    "manual_complete": "Complemento manual",
}
def _safe_dt(value):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    dt = parsed.to_pydatetime()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=APP_TZ)
    return dt.astimezone(APP_TZ)


def _date_value(value):
    parsed = _safe_dt(value)
    return parsed.date() if parsed is not None else date.today()


def _time_value(value):
    parsed = _safe_dt(value)
    return parsed.time().replace(microsecond=0) if parsed is not None else time(0, 0, 0)


def _format_minutes(value) -> str:
    try:
        total = int(value)
    except Exception:
        return "-"
    horas = total // 60
    minutos = total % 60
    return f"{horas:02d}h {minutos:02d}m"


def _format_dt(value) -> str:
    parsed = _safe_dt(value)
    return parsed.strftime("%d/%m/%Y %H:%M") if parsed is not None else "-"


def _format_km(value) -> str:
    try:
        return f"{float(value):,.1f} km"
    except Exception:
        return "-"


def _status_label(value: str) -> str:
    return STATUS_LABELS.get(str(value or "").strip().lower(), str(value or "-"))


def _bool_default(row: dict, key: str) -> bool:
    return row.get(key) not in (None, "", [])


def _get_work_day_by_id(jornadas: list[dict], selected_id: int | None) -> dict | None:
    if selected_id is None:
        return None
    return next((row for row in jornadas if int(row["id"]) == int(selected_id)), None)


def _sorted_jornadas(jornadas: list[dict]) -> list[dict]:
    return sorted(
        jornadas,
        key=lambda row: (str(row.get("id", 0)).isdigit(), int(row.get("id", 0)) if str(row.get("id", 0)).isdigit() else 0),
        reverse=True,
    )


def _display_number_from_records(records: list[dict], item_id: int | None) -> int | None:
    if item_id is None:
        return None
    ordered = _sorted_jornadas(records)
    for index, row in enumerate(ordered, start=1):
        if int(row["id"]) == int(item_id):
            return index
    return None


def _jornada_label(jornadas: list[dict], item_id: int | None) -> str:
    if item_id is None:
        return "Nova jornada"
    row = _get_work_day_by_id(jornadas, item_id)
    display_number = _display_number_from_records(jornadas, item_id)
    if row is None or display_number is None:
        return "Registro ?"
    return f"Registro {display_number} | {row.get('work_date') or '-'} | {_status_label(str(row.get('status') or ''))}"


def _km_period_label(periodos: list[dict], item_id: int | None) -> str:
    if item_id is None:
        return "Novo período"
    ordered = sorted(periodos, key=lambda row: int(row.get("id", 0)), reverse=True)
    display_number = next((index for index, row in enumerate(ordered, start=1) if int(row["id"]) == int(item_id)), None)
    row = _get_km_period_by_id(periodos, item_id)
    if row is None or display_number is None:
        return "Registro ?"
    return (
        f"Registro {display_number} | {row['start_date']} até {row['end_date']} | "
        f"{_format_km(row['km_total_periodo'])}"
    )


def _sync_jornada_edit_state(jornadas: list[dict]) -> tuple[int | None, dict | None]:
    jornadas = _sorted_jornadas(jornadas)
    options = [row["id"] for row in jornadas]
    _ensure_selected_option("wd_edit_selected_id", options)
    selected_id = st.session_state.get("wd_edit_selected_id")
    last_selected = st.session_state.get("wd_edit_last_selected_id")
    row = _get_work_day_by_id(jornadas, selected_id)
    if selected_id != last_selected:
        _set_jornada_edit_fields(row)
        st.session_state["wd_edit_last_selected_id"] = selected_id
    return selected_id, row


def _set_jornada_edit_fields(row: dict | None) -> None:
    work_date = row.get("work_date") if row else None
    start_time = row.get("start_time") if row else None
    end_time = row.get("end_time") if row else None
    st.session_state["wd_edit_date"] = _date_value(work_date)
    st.session_state["wd_edit_has_start"] = _bool_default(row or {}, "start_time")
    st.session_state["wd_edit_has_end"] = _bool_default(row or {}, "end_time")
    st.session_state["wd_edit_start_date"] = _date_value(start_time or work_date)
    st.session_state["wd_edit_start_time"] = _time_value(start_time)
    st.session_state["wd_edit_end_date"] = _date_value(end_time or work_date)
    st.session_state["wd_edit_end_time"] = _time_value(end_time)
    st.session_state["wd_edit_has_start_km"] = _bool_default(row or {}, "start_km")
    st.session_state["wd_edit_start_km"] = float((row or {}).get("start_km") or 0.0)
    st.session_state["wd_edit_has_end_km"] = _bool_default(row or {}, "end_km")
    st.session_state["wd_edit_end_km"] = float((row or {}).get("end_km") or 0.0)
    st.session_state["wd_edit_minutes"] = int((row or {}).get("worked_minutes_manual") or 0)
    st.session_state["wd_edit_notes"] = str((row or {}).get("notes") or "")
    st.session_state["wd_edit_override"] = False
    st.session_state["wd_edit_action"] = "Completar"


def _get_km_period_by_id(periodos: list[dict], selected_id: int | None) -> dict | None:
    if selected_id is None:
        return None
    return next((row for row in periodos if int(row["id"]) == int(selected_id)), None)


def _sync_km_period_state(periodos: list[dict]) -> tuple[int | None, dict | None]:
    options = [None] + [row["id"] for row in periodos]
    _ensure_selected_option("wd_km_period_selected_id", options)
    selected_id = st.session_state.get("wd_km_period_selected_id")
    last_selected = st.session_state.get("wd_km_period_last_selected_id")
    row = _get_km_period_by_id(periodos, selected_id)
    if selected_id != last_selected:
        _set_km_period_fields(row)
        st.session_state["wd_km_period_last_selected_id"] = selected_id
    return selected_id, row


def _set_km_period_fields(row: dict | None) -> None:
    st.session_state["wd_km_period_start_date"] = _date_value((row or {}).get("start_date"))
    st.session_state["wd_km_period_end_date"] = _date_value((row or {}).get("end_date"))
    st.session_state["wd_km_period_total"] = float((row or {}).get("km_total_periodo") or 0.0)
    st.session_state["wd_km_period_notes"] = str((row or {}).get("notes") or "")
    st.session_state["wd_km_period_confirm_delete"] = False


def _combine_date_time(enabled: bool, input_date: date, input_time: time) -> str | None:
    if not enabled:
        return None
    return pd.Timestamp.combine(input_date, input_time).tz_localize(APP_TZ).isoformat()


def _event_summary(value) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    keys = ["status", "start_km", "end_km", "start_time", "end_time", "worked_minutes_final"]
    parts: list[str] = []
    for key in keys:
        if key not in value:
            continue
        raw = value.get(key)
        if key in {"start_time", "end_time"}:
            formatted = _format_dt(raw)
        elif key in {"start_km", "end_km"}:
            formatted = _format_km(raw)
        elif key == "worked_minutes_final":
            formatted = _format_minutes(raw)
        elif key == "status":
            formatted = _status_label(str(raw))
        else:
            formatted = str(raw)
        parts.append(f"{key}: {formatted}")
    return " | ".join(parts) if parts else "-"


def _render_current_status(jornadas: list[dict]) -> dict | None:
    titulo_secao("Status Atual")
    aberta = next((row for row in jornadas if row.get("status") == "open"), None)
    parcial = next((row for row in jornadas if row.get("status") == "partial"), None)
    if aberta:
        render_kpi_grid(
            [
                ("Status", "Em andamento", None),
                ("Início", _format_dt(aberta.get("start_time")), None),
                ("KM inicial", _format_km(aberta.get("start_km")), None),
                ("Observação", aberta.get("notes") or "-", None),
            ]
        )
        return aberta
    if parcial:
        render_kpi_grid(
            [
                ("Status", "Jornada incompleta", None),
                ("Data", str(parcial.get("work_date") or "-"), None),
                ("Início", _format_dt(parcial.get("start_time")), None),
                ("KM inicial", _format_km(parcial.get("start_km")), None),
            ]
        )
        st.warning("Existe uma jornada incompleta. Use a seção de complemento/edição para concluir ou corrigir o registro.")
        return parcial
    else:
        render_kpi_grid(
            [
                ("Status", "Sem jornada aberta", None),
                ("Hoje", pd.Timestamp.now(tz=APP_TZ).date().isoformat(), None),
                ("Jornadas incompletas", sum(1 for row in jornadas if row.get("status") == "partial"), None),
            ]
        )
    return None


def _render_auto_flow(open_day: dict | None) -> None:
    titulo_secao("Check-in / Check-out")
    col_start, col_end = st.columns(2)
    with col_start:
        with st.form("work_day_check_in_form"):
            st.caption("Início automático: o sistema registra a data/hora atual e você informa só o KM inicial.")
            start_km = st.number_input("KM inicial", min_value=0.0, step=0.1, key="wd_start_km")
            notes = st.text_area("Observações", key="wd_start_notes")
            submit = st.form_submit_button("Iniciar jornada", disabled=open_day is not None)
            if submit:
                try:
                    service.iniciar_jornada(start_km=start_km, notes=notes)
                    st.success("Jornada iniciada.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    with col_end:
        with st.form("work_day_check_out_form"):
            st.caption("Encerramento automático: o sistema registra a data/hora atual e você informa só o KM final.")
            end_km = st.number_input("KM final", min_value=0.0, step=0.1, key="wd_end_km")
            notes = st.text_area("Observações finais", key="wd_end_notes")
            submit = st.form_submit_button("Encerrar jornada", disabled=open_day is None)
            if submit:
                try:
                    service.encerrar_jornada(end_km=end_km, notes=notes)
                    st.success("Jornada encerrada.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def _render_manual_create() -> None:
    titulo_secao("Criação Manual Excepcional")
    with st.expander("Criar jornada manual completa/incompleta", expanded=False):
        with st.form("work_day_manual_create_form"):
            work_date = st.date_input("Data da jornada", key="wd_manual_date")
            st.caption("Ative apenas os campos que realmente existem para este registro manual.")
            include_start = st.checkbox("Informar início manual", value=True, key="wd_manual_has_start")
            include_end = st.checkbox("Informar término manual", value=False, key="wd_manual_has_end")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Data de início",
                    value=work_date,
                    key="wd_manual_start_date",
                    disabled=not include_start,
                )
                start_clock = st.time_input("Hora de início", key="wd_manual_start_time", disabled=not include_start)
            with col2:
                end_date = st.date_input(
                    "Data de término",
                    value=work_date,
                    key="wd_manual_end_date",
                    disabled=not include_end,
                )
                end_clock = st.time_input("Hora de término", key="wd_manual_end_time", disabled=not include_end)
            include_start_km = st.checkbox("Informar KM inicial", value=True, key="wd_manual_has_start_km")
            start_km = st.number_input(
                "KM inicial manual",
                min_value=0.0,
                step=0.1,
                key="wd_manual_start_km",
                disabled=not include_start_km,
            )
            include_end_km = st.checkbox("Informar KM final", value=False, key="wd_manual_has_end_km")
            end_km = st.number_input(
                "KM final manual",
                min_value=0.0,
                step=0.1,
                key="wd_manual_end_km",
                disabled=not include_end_km,
            )
            worked_manual = st.number_input("Tempo manual (minutos)", min_value=0, step=1, key="wd_manual_minutes")
            notes = st.text_area("Observações", key="wd_manual_notes")
            allow_override = st.checkbox("Permitir ajuste manual excepcional", key="wd_manual_override")
            submit = st.form_submit_button("Salvar jornada manual")
            if submit:
                try:
                    start_time_value = _combine_date_time(include_start, start_date, start_clock)
                    end_time_value = _combine_date_time(include_end, end_date, end_clock)
                    service.criar_jornada_manual(
                        work_date=work_date.isoformat(),
                        start_time=start_time_value,
                        end_time=end_time_value,
                        start_km=start_km if include_start_km else None,
                        end_km=end_km if include_end_km else None,
                        worked_minutes_manual=worked_manual if worked_manual > 0 else None,
                        notes=notes,
                        allow_manual_override=allow_override,
                    )
                    st.success("Jornada manual registrada.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def _render_manual_edit(jornadas: list[dict]) -> None:
    titulo_secao("Complemento / Edição")
    if not jornadas:
        show_empty_data("Nenhuma jornada para editar.")
        return
    jornadas = _sorted_jornadas(jornadas)
    options = [row["id"] for row in jornadas]
    st.selectbox("Selecione a jornada", options=options, format_func=lambda x: _jornada_label(jornadas, x), key="wd_edit_selected_id")
    selected_id, selected_row = _sync_jornada_edit_state(jornadas)
    if selected_id is None or selected_row is None:
        show_empty_data("Nenhuma jornada selecionada.")
        return
    detail = service.detalhar_jornada(int(selected_id))

    with st.form("work_day_manual_edit_form"):
        work_date = st.date_input("Data", key="wd_edit_date")
        has_start = st.checkbox("Manter horário inicial", key="wd_edit_has_start")
        has_end = st.checkbox("Manter horário final", key="wd_edit_has_end")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Data de início",
                key="wd_edit_start_date",
                disabled=not has_start,
            )
            start_clock = st.time_input(
                "Hora de início",
                key="wd_edit_start_time",
                disabled=not has_start,
            )
        with col2:
            end_date = st.date_input(
                "Data de término",
                key="wd_edit_end_date",
                disabled=not has_end,
            )
            end_clock = st.time_input(
                "Hora de término",
                key="wd_edit_end_time",
                disabled=not has_end,
            )
        has_start_km = st.checkbox("Manter KM inicial", key="wd_edit_has_start_km")
        start_km = st.number_input(
            "KM inicial",
            min_value=0.0,
            step=0.1,
            key="wd_edit_start_km",
            disabled=not has_start_km,
        )
        has_end_km = st.checkbox("Manter KM final", key="wd_edit_has_end_km")
        end_km = st.number_input(
            "KM final",
            min_value=0.0,
            step=0.1,
            key="wd_edit_end_km",
            disabled=not has_end_km,
        )
        worked_manual = st.number_input(
            "Tempo manual (minutos)",
            min_value=0,
            step=1,
            key="wd_edit_minutes",
        )
        notes = st.text_area("Observações", key="wd_edit_notes")
        allow_override = st.checkbox("Permitir ajuste manual excepcional", key="wd_edit_override")
        action = st.radio("Ação", ["Completar", "Editar"], horizontal=True, key="wd_edit_action")
        col_save, col_delete = st.columns(2)
        submit = col_save.form_submit_button("Salvar alteração")
        delete = col_delete.form_submit_button("Excluir jornada")
        if submit:
            try:
                start_time_value = _combine_date_time(has_start, start_date, start_clock)
                end_time_value = _combine_date_time(has_end, end_date, end_clock)
                payload = {
                    "work_date": work_date.isoformat(),
                    "start_time": start_time_value,
                    "end_time": end_time_value,
                    "start_km": start_km if has_start_km else None,
                    "end_km": end_km if has_end_km else None,
                    "worked_minutes_manual": worked_manual if worked_manual > 0 else None,
                    "notes": notes,
                }
                if action == "Completar":
                    service.completar_jornada(
                        int(selected_id),
                        start_time=payload["start_time"],
                        end_time=payload["end_time"],
                        start_km=payload["start_km"],
                        end_km=payload["end_km"],
                        worked_minutes_manual=payload["worked_minutes_manual"],
                        notes=payload["notes"],
                        allow_manual_override=allow_override,
                    )
                else:
                    service.editar_jornada(int(selected_id), payload, allow_manual_override=allow_override, notes=notes)
                st.success("Jornada atualizada.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if delete:
            try:
                service.deletar_jornada(int(selected_id))
                st.success("Jornada excluída.")
                _reset_fields(["wd_edit_selected_id", "wd_edit_last_selected_id"])
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    titulo_secao("Eventos da Jornada")
    events = detail["events"]
    if not events:
        show_empty_data("Sem eventos registrados.")
    else:
        events_df = pd.DataFrame(events)
        if "event_type" in events_df.columns:
            events_df["event_type"] = events_df["event_type"].map(EVENT_LABELS).fillna(events_df["event_type"])
        if "event_timestamp" in events_df.columns:
            events_df["event_timestamp"] = events_df["event_timestamp"].apply(_format_dt)
        if "km_value" in events_df.columns:
            events_df["km_value"] = events_df["km_value"].apply(_format_km)
        if "old_value" in events_df.columns:
            events_df["old_value"] = events_df["old_value"].apply(_event_summary)
        if "new_value" in events_df.columns:
            events_df["new_value"] = events_df["new_value"].apply(_event_summary)
        columns = [col for col in ["event_type", "event_timestamp", "km_value", "old_value", "new_value", "notes"] if col in events_df.columns]
        st.dataframe(events_df[columns], use_container_width=True, hide_index=True)


def _render_km_control() -> None:
    titulo_secao("Controle de KM Total Histórico")
    periodos = service.listar_km_periodos()
    periodos = sorted(periodos, key=lambda row: int(row.get("id", 0)), reverse=True)
    options = [None] + [row["id"] for row in periodos]
    st.selectbox(
        "Período cadastrado",
        options=options,
        format_func=lambda x: _km_period_label(periodos, x),
        key="wd_km_period_selected_id",
    )
    selected_id, selected = _sync_km_period_state(periodos)

    with st.form("wd_km_period_form"):
        start_date = st.date_input(
            "Data inicial do período",
            key="wd_km_period_start_date",
        )
        end_date = st.date_input(
            "Data final do período",
            key="wd_km_period_end_date",
        )
        km_total = st.number_input(
            "KM total percorrido no período",
            min_value=0.0,
            step=1.0,
            key="wd_km_period_total",
        )
        notes = st.text_area("Observações", key="wd_km_period_notes")
        confirmar_exclusao = st.checkbox("Confirmo a exclusão deste período", key="wd_km_period_confirm_delete")
        col_save, col_update, col_delete = st.columns(3)
        salvar = col_save.form_submit_button("Salvar (novo)")
        atualizar = col_update.form_submit_button("Atualizar")
        excluir = col_delete.form_submit_button("Excluir")
        try:
            if salvar:
                service.criar_km_periodo(start_date.isoformat(), end_date.isoformat(), km_total, notes=notes)
                st.success("Período salvo.")
                st.rerun()
            if atualizar:
                if selected is None:
                    st.warning("Selecione um período para atualizar.")
                else:
                    service.atualizar_km_periodo(int(selected["id"]), start_date.isoformat(), end_date.isoformat(), km_total, notes=notes)
                    st.success("Período atualizado.")
                    st.rerun()
            if excluir:
                if selected is None:
                    st.warning("Selecione um período para excluir.")
                elif not confirmar_exclusao:
                    st.warning("Confirme a exclusão para continuar.")
                else:
                    service.deletar_km_periodo(int(selected["id"]))
                    st.success("Período excluído.")
                    _reset_fields(["wd_km_period_selected_id", "wd_km_period_last_selected_id"])
                    st.rerun()
        except Exception as exc:
            st.error(str(exc))

    if not periodos:
        show_empty_data("Nenhum período histórico de KM total cadastrado.")
        return

    df = pd.DataFrame(periodos)
    if not df.empty:
        df["registro"] = range(1, len(df) + 1)
    for col in ("km_total_periodo", "km_remunerado_periodo", "km_nao_remunerado_periodo"):
        if col in df.columns:
            df[col] = df[col].apply(_format_km)
    st.dataframe(
        df[[col for col in ["registro", "start_date", "end_date", "km_total_periodo", "km_remunerado_periodo", "km_nao_remunerado_periodo", "notes"] if col in df.columns]],
        use_container_width=True,
        hide_index=True,
    )

    titulo_secao("Reparo Histórico do Hodômetro")
    st.caption(
        "Use esta rotina uma única vez para preencher KM inicial/final ausentes em jornadas antigas. "
        "Ela usa o KM inicial válido mais recente como âncora e retrocede aplicando um intervalo padrão entre dias."
    )
    with st.form("wd_historic_odometer_repair_form"):
        intervalo_padrao = st.number_input(
            "Intervalo padrão entre jornadas (KM)",
            min_value=0.0,
            step=1.0,
            value=10.0,
            key="wd_historic_repair_gap",
        )
        notes = st.text_input(
            "Observação do reparo",
            value="Reparo historico automatico de hodometro.",
            key="wd_historic_repair_notes",
        )
        confirmar = st.checkbox(
            "Confirmo que esta rotina deve preencher apenas registros antigos com KM ausente",
            key="wd_historic_repair_confirm",
        )
        executar = st.form_submit_button("Executar reparo histórico")
        if executar:
            try:
                if not confirmar:
                    st.warning("Confirme a execução para continuar.")
                else:
                    result = service.reparar_hodometro_historico(intervalo_padrao_km=intervalo_padrao, notes=notes)
                    st.success(
                        "Reparo concluído. "
                        f"{int(result['updated_rows'])} jornada(s) atualizada(s) usando a âncora "
                        f"ID {int(result['anchor_work_day_id'])} em {result['anchor_work_date']}."
                    )
                    st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _render_history(jornadas: list[dict]) -> None:
    titulo_secao("Histórico")
    if not jornadas:
        show_empty_data("Nenhuma jornada registrada.")
        return
    jornadas = _sorted_jornadas(jornadas)
    df = pd.DataFrame(jornadas)
    if not df.empty:
        df["registro"] = range(1, len(df) + 1)
    if "status" in df.columns:
        df["status"] = df["status"].map(STATUS_LABELS).fillna(df["status"])
    for col in ("start_time", "end_time", "created_at", "updated_at"):
        if col in df.columns:
            df[col] = df[col].apply(_format_dt)
    if "worked_minutes_final" in df.columns:
        df["worked_minutes_final"] = df["worked_minutes_final"].apply(_format_minutes)
    for col in ("start_km", "end_km", "km_remunerado", "km_nao_remunerado_antes"):
        if col in df.columns:
            df[col] = df[col].apply(_format_km)
    preferred = [
        "registro",
        "work_date",
        "status",
        "start_time",
        "end_time",
        "start_km",
        "end_km",
        "km_remunerado",
        "km_nao_remunerado_antes",
        "worked_minutes_final",
        "notes",
        "updated_at",
    ]
    columns = [col for col in preferred if col in df.columns]
    st.dataframe(df[columns], use_container_width=True, hide_index=True)


def pagina_jornada() -> None:
    st.header("Jornada")
    try:
        jornadas = service.listar_jornadas()
        periodos = service.listar_km_periodos()
    except Exception as exc:
        st.error(work_day_bootstrap_message(exc))
        st.stop()
    aberta = _render_current_status(jornadas)

    if jornadas or periodos:
        total_km_rem = sum(float(row.get("km_remunerado") or 0.0) for row in jornadas)
        total_km_nao_rem = sum(float(row.get("km_nao_remunerado_antes") or 0.0) for row in jornadas)
        total_km_nao_rem += sum(float(row.get("km_nao_remunerado_periodo") or 0.0) for row in periodos)
        total_minutes = sum(int(row.get("worked_minutes_final") or 0) for row in jornadas)
        render_kpi_grid(
            [
                ("KM remunerado", _format_km(total_km_rem), None),
                ("KM não remunerado", _format_km(total_km_nao_rem), None),
                ("Tempo final", _format_minutes(total_minutes), None),
            ]
        )

    tab_operacao, tab_controle, tab_historico = st.tabs(["Operação", "Controle", "Histórico"])

    with tab_operacao:
        _render_auto_flow(aberta)
        _render_manual_create()
        _render_manual_edit(jornadas)

    with tab_controle:
        _render_km_control()

    with tab_historico:
        _render_history(jornadas)
