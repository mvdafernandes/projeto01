"""Domain models for records and dashboard summary."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from domain.validators import sanitize_nullable_text, safe_float, safe_int, to_iso_date


@dataclass
class Receita:
    """Receita record model."""

    data: str
    valor: float
    km: float
    tempo_trabalhado: int
    observacao: str = ""

    @classmethod
    def from_raw(cls, payload: dict) -> "Receita":
        """Build sanitized Receita from untrusted payload."""

        return cls(
            data=to_iso_date(payload.get("data"), fallback=""),
            valor=safe_float(payload.get("valor"), 0.0),
            km=safe_float(payload.get("km"), 0.0),
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
