"""Domain models for records and dashboard summary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from domain.validators import sanitize_nullable_text, safe_float, safe_int, to_iso_date


@dataclass
class Receita:
    """Receita record model."""

    data: str
    valor: float
    km: float = 0.0
    tempo_trabalhado: int = 0
    km_rodado_total: float = 0.0
    observacao: str = ""

    @classmethod
    def from_raw(cls, payload: dict) -> "Receita":
        """Build sanitized Receita from untrusted payload."""

        return cls(
            data=to_iso_date(payload.get("data"), fallback=""),
            valor=safe_float(payload.get("valor"), 0.0),
            km=safe_float(payload.get("km"), 0.0),
            km_rodado_total=safe_float(payload.get("km_rodado_total", payload.get("km rodado total", 0.0)), 0.0),
            tempo_trabalhado=safe_int(payload.get("tempo trabalhado", payload.get("tempo_trabalhado", 0)), 0),
            observacao=sanitize_nullable_text(payload.get("observacao", "")),
        )

    def to_record(self) -> dict:
        """Return database-ready Receita dict."""

        record = asdict(self)
        record["tempo trabalhado"] = record.pop("tempo_trabalhado")
        return record


@dataclass
class Despesa:
    """Despesa record model."""

    data: str
    categoria: str
    valor: float
    observacao: str = ""
    tipo_despesa: str = "VARIAVEL"
    subcategoria_fixa: str = ""
    esfera_despesa: str = "NEGOCIO"
    litros: float = 0.0
    recorrencia_tipo: str = ""
    recorrencia_meses: int = 0
    recorrencia_serie_id: str = ""

    @classmethod
    def from_raw(cls, payload: dict) -> "Despesa":
        """Build sanitized Despesa from untrusted payload."""

        return cls(
            data=to_iso_date(payload.get("data"), fallback=""),
            categoria=sanitize_nullable_text(payload.get("categoria", "")),
            valor=safe_float(payload.get("valor"), 0.0),
            observacao=sanitize_nullable_text(payload.get("observacao", "")),
            tipo_despesa=sanitize_nullable_text(payload.get("tipo_despesa", "VARIAVEL")).upper() or "VARIAVEL",
            subcategoria_fixa=sanitize_nullable_text(payload.get("subcategoria_fixa", "")),
            esfera_despesa=sanitize_nullable_text(payload.get("esfera_despesa", "NEGOCIO")).upper() or "NEGOCIO",
            litros=safe_float(payload.get("litros", 0.0), 0.0),
            recorrencia_tipo=sanitize_nullable_text(payload.get("recorrencia_tipo", "")).upper(),
            recorrencia_meses=safe_int(payload.get("recorrencia_meses", 0), 0),
            recorrencia_serie_id=sanitize_nullable_text(payload.get("recorrencia_serie_id", "")),
        )

    def to_record(self) -> dict:
        """Return database-ready Despesa dict."""

        return asdict(self)


@dataclass
class ResumoMensal:
    """Dashboard monthly summary model."""

    receita_total: float = 0.0
    despesa_total: float = 0.0
    lucro: float = 0.0
    margem_pct: float = 0.0
    dias_trabalhados: int = 0
    meta_batida_pct: float = 0.0
    receita_por_km: float = 0.0
    lucro_por_km: float = 0.0

    def to_dict(self) -> dict:
        """Return backward-compatible summary payload."""

        return {
            "receita_total": float(self.receita_total),
            "despesa_total": float(self.despesa_total),
            "lucro": float(self.lucro),
            "margem_%": float(self.margem_pct),
            "dias_trabalhados": int(self.dias_trabalhados),
            "%_meta_batida": float(self.meta_batida_pct),
            "receita_por_km": float(self.receita_por_km),
            "lucro_por_km": float(self.lucro_por_km),
        }


@dataclass
class ControleKM:
    """Controle record model for total driven kilometers."""

    data_inicio: str
    data_fim: str
    km_total_rodado: float

    @classmethod
    def from_raw(cls, payload: dict) -> "ControleKM":
        return cls(
            data_inicio=to_iso_date(payload.get("data_inicio", payload.get("data", "")), fallback=""),
            data_fim=to_iso_date(payload.get("data_fim", payload.get("data", "")), fallback=""),
            km_total_rodado=safe_float(payload.get("km_total_rodado", payload.get("km total rodado", 0.0)), 0.0),
        )

    def to_record(self) -> dict:
        return asdict(self)


@dataclass
class ControleLitros:
    """Controle record model for fueled liters."""

    data: str
    litros: float
    odometro: float | None = None
    valor_total: float = 0.0
    tanque_cheio: bool = False
    tipo_combustivel: str = ""
    observacao: str = ""

    @classmethod
    def from_raw(cls, payload: dict) -> "ControleLitros":
        raw_tanque_cheio = payload.get("tanque_cheio", False)
        if isinstance(raw_tanque_cheio, str):
            tanque_cheio = raw_tanque_cheio.strip().lower() in {"1", "true", "t", "sim", "yes", "y"}
        else:
            tanque_cheio = bool(raw_tanque_cheio)
        return cls(
            data=to_iso_date(payload.get("data", ""), fallback=""),
            litros=safe_float(payload.get("litros", 0.0), 0.0),
            odometro=safe_float(payload.get("odometro"), 0.0) if payload.get("odometro") not in (None, "") else None,
            valor_total=safe_float(payload.get("valor_total", 0.0), 0.0),
            tanque_cheio=tanque_cheio,
            tipo_combustivel=sanitize_nullable_text(payload.get("tipo_combustivel", "")),
            observacao=sanitize_nullable_text(payload.get("observacao", "")),
        )

    def to_record(self) -> dict:
        return asdict(self)


@dataclass
class WorkDay:
    """Work day model used by automatic and manual journey flows."""

    work_date: str
    start_time: str = ""
    end_time: str = ""
    start_time_source: str = "auto"
    end_time_source: str = "auto"
    start_km: float | None = None
    end_km: float | None = None
    km_remunerado: float | None = None
    km_nao_remunerado_antes: float | None = None
    worked_minutes_calculated: int | None = None
    worked_minutes_manual: int | None = None
    worked_minutes_final: int | None = None
    status: str = "partial"
    is_manually_adjusted: bool = False
    notes: str = ""

    @classmethod
    def from_raw(cls, payload: dict[str, Any]) -> "WorkDay":
        return cls(
            work_date=to_iso_date(payload.get("work_date", payload.get("work_date", "")), fallback=""),
            start_time=sanitize_nullable_text(payload.get("start_time", "")),
            end_time=sanitize_nullable_text(payload.get("end_time", "")),
            start_time_source=sanitize_nullable_text(payload.get("start_time_source", "auto")).lower() or "auto",
            end_time_source=sanitize_nullable_text(payload.get("end_time_source", "auto")).lower() or "auto",
            start_km=safe_float(payload.get("start_km"), 0.0) if payload.get("start_km") is not None else None,
            end_km=safe_float(payload.get("end_km"), 0.0) if payload.get("end_km") is not None else None,
            km_remunerado=safe_float(payload.get("km_remunerado"), 0.0) if payload.get("km_remunerado") is not None else None,
            km_nao_remunerado_antes=(
                safe_float(payload.get("km_nao_remunerado_antes"), 0.0)
                if payload.get("km_nao_remunerado_antes") is not None
                else None
            ),
            worked_minutes_calculated=(
                safe_int(payload.get("worked_minutes_calculated"), 0)
                if payload.get("worked_minutes_calculated") is not None
                else None
            ),
            worked_minutes_manual=(
                safe_int(payload.get("worked_minutes_manual"), 0) if payload.get("worked_minutes_manual") is not None else None
            ),
            worked_minutes_final=(
                safe_int(payload.get("worked_minutes_final"), 0) if payload.get("worked_minutes_final") is not None else None
            ),
            status=sanitize_nullable_text(payload.get("status", "partial")).lower() or "partial",
            is_manually_adjusted=bool(payload.get("is_manually_adjusted", False)),
            notes=sanitize_nullable_text(payload.get("notes", "")),
        )

    def to_record(self) -> dict:
        record = asdict(self)
        for key in ("start_time", "end_time"):
            if not record[key]:
                record[key] = None
        return record


@dataclass
class WorkDayEvent:
    """Work day event model for check-in/out and manual edits."""

    work_day_id: int
    event_type: str
    event_timestamp: str
    km_value: float | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    notes: str = ""

    @classmethod
    def from_raw(cls, payload: dict[str, Any]) -> "WorkDayEvent":
        return cls(
            work_day_id=safe_int(payload.get("work_day_id"), 0),
            event_type=sanitize_nullable_text(payload.get("event_type", "")).lower(),
            event_timestamp=sanitize_nullable_text(payload.get("event_timestamp", "")),
            km_value=safe_float(payload.get("km_value"), 0.0) if payload.get("km_value") is not None else None,
            old_value=payload.get("old_value") if isinstance(payload.get("old_value"), dict) else None,
            new_value=payload.get("new_value") if isinstance(payload.get("new_value"), dict) else None,
            notes=sanitize_nullable_text(payload.get("notes", "")),
        )

    def to_record(self) -> dict:
        return asdict(self)


@dataclass
class WorkKmPeriod:
    """Historical total-km period model."""

    start_date: str
    end_date: str
    km_total_periodo: float
    notes: str = ""

    @classmethod
    def from_raw(cls, payload: dict[str, Any]) -> "WorkKmPeriod":
        return cls(
            start_date=to_iso_date(payload.get("start_date", ""), fallback=""),
            end_date=to_iso_date(payload.get("end_date", ""), fallback=""),
            km_total_periodo=safe_float(payload.get("km_total_periodo", 0.0), 0.0),
            notes=sanitize_nullable_text(payload.get("notes", "")),
        )

    def to_record(self) -> dict:
        return asdict(self)
