"""Backup/import service for user business data."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from core.auth import get_logged_username
from core.database import get_sqlite_connection
from repositories.categorias_despesas_repository import CategoriasDespesasRepository
from repositories.controle_km_repository import ControleKMRepository
from repositories.controle_litros_repository import ControleLitrosRepository
from repositories.despesas_repository import DespesasRepository
from repositories.investimentos_repository import InvestimentosRepository
from repositories.receitas_repository import ReceitasRepository


class BackupService:
    """Create and restore structured backups for the current logged user."""

    BACKUP_FORMAT = "driver_analytics_backup"
    BACKUP_VERSION = 1

    def __init__(self) -> None:
        self.receitas_repo = ReceitasRepository()
        self.despesas_repo = DespesasRepository()
        self.investimentos_repo = InvestimentosRepository()
        self.controle_km_repo = ControleKMRepository()
        self.controle_litros_repo = ControleLitrosRepository()
        self.categorias_repo = CategoriasDespesasRepository()

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _safe_str(value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _safe_date_str(value: Any, default: str = "") -> str:
        if isinstance(value, (datetime, date)):
            return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return default
        return pd.Timestamp(parsed).date().isoformat()

    def _current_user_id(self) -> int:
        user_id = self.receitas_repo._current_user_id()
        if user_id is None:
            raise ValueError("Usuário não autenticado. Faça login novamente para usar backup/importação.")
        return int(user_id)

    @staticmethod
    def _json_compatible_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    def _df_to_records(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        work = df.replace({pd.NA: None})
        records = work.to_dict(orient="records")
        out: list[dict[str, Any]] = []
        for row in records:
            clean_row = {str(k): self._json_compatible_value(v) for k, v in dict(row).items()}
            out.append(clean_row)
        return out

    def export_payload(self) -> dict[str, Any]:
        self._current_user_id()
        data = {
            "receitas": self._df_to_records(self.receitas_repo.listar()),
            "despesas": self._df_to_records(self.despesas_repo.listar()),
            "investimentos": self._df_to_records(self.investimentos_repo.listar()),
            "controle_km": self._df_to_records(self.controle_km_repo.listar()),
            "controle_litros": self._df_to_records(self.controle_litros_repo.listar()),
            "categorias_despesas": self._df_to_records(self.categorias_repo.listar()),
        }
        counts = {key: len(value) for key, value in data.items()}
        return {
            "format": self.BACKUP_FORMAT,
            "version": self.BACKUP_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "username": get_logged_username(),
            "counts": counts,
            "data": data,
        }

    def dumps_backup(self, payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    def loads_backup(self, raw: bytes) -> dict[str, Any]:
        try:
            parsed = json.loads(raw.decode("utf-8-sig"))
        except Exception as exc:
            raise ValueError("Arquivo inválido. Use um backup JSON gerado pelo Driver Analytics.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("Estrutura de backup inválida.")
        return parsed

    def _extract_data(self, payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        if str(payload.get("format", "")).strip() != self.BACKUP_FORMAT:
            raise ValueError("Formato de backup não reconhecido.")

        try:
            version = int(payload.get("version", 0))
        except Exception:
            version = 0
        if version > self.BACKUP_VERSION:
            raise ValueError("Versão de backup mais nova que esta aplicação. Atualize o app antes de importar.")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("Bloco de dados de backup inválido.")

        out: dict[str, list[dict[str, Any]]] = {}
        for key in ["receitas", "despesas", "investimentos", "controle_km", "controle_litros", "categorias_despesas"]:
            value = data.get(key, [])
            if value is None:
                value = []
            if not isinstance(value, list):
                raise ValueError(f"Lista '{key}' inválida no backup.")
            out[key] = [dict(item) for item in value if isinstance(item, dict)]
        return out

    def _clear_existing_data(self) -> int:
        user_id = self._current_user_id()
        deleted = 0

        client = self.receitas_repo._supabase()
        tables = ["receitas", "despesas", "investimentos", "controle_km", "controle_litros", "categorias_despesas"]
        if client:
            for table in tables:
                try:
                    client.table(table).delete().eq("user_id", int(user_id)).execute()
                    deleted += 1
                except Exception:
                    # Ignore unsupported tables/legacy schemas and continue with what is possible.
                    pass

        conn = get_sqlite_connection()
        cursor = conn.cursor()
        for table in tables:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (int(user_id),))
                deleted += int(cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0)
            except Exception:
                pass
        conn.commit()
        conn.close()

        return int(deleted)

    def import_payload(self, payload: dict[str, Any], replace_existing: bool = True) -> dict[str, int]:
        self._current_user_id()
        data = self._extract_data(payload)

        cleared = 0
        if replace_existing:
            cleared = self._clear_existing_data()

        for row in data["categorias_despesas"]:
            nome = self._safe_str(row.get("nome"), "").strip()
            if nome:
                self.categorias_repo.inserir(nome)

        for row in data["receitas"]:
            self.receitas_repo.inserir(
                data=self._safe_date_str(row.get("data"), default=""),
                valor=self._safe_float(row.get("valor"), 0.0),
                km=self._safe_float(row.get("km"), 0.0),
                tempo_trabalhado=int(self._safe_float(row.get("tempo trabalhado"), 0.0)),
                observacao=self._safe_str(row.get("observacao"), ""),
                km_rodado_total=self._safe_float(row.get("km_rodado_total"), self._safe_float(row.get("km"), 0.0)),
            )

        for row in data["despesas"]:
            self.despesas_repo.inserir(
                data=self._safe_date_str(row.get("data"), default=""),
                categoria=self._safe_str(row.get("categoria"), "Outros"),
                valor=self._safe_float(row.get("valor"), 0.0),
                observacao=self._safe_str(row.get("observacao"), ""),
                tipo_despesa=self._safe_str(row.get("tipo_despesa"), "VARIAVEL"),
                subcategoria_fixa=self._safe_str(row.get("subcategoria_fixa"), ""),
                esfera_despesa=self._safe_str(row.get("esfera_despesa"), "NEGOCIO"),
                litros=self._safe_float(row.get("litros"), 0.0),
            )

        for row in data["investimentos"]:
            data_base = self._safe_date_str(row.get("data_fim") or row.get("data"), default="")
            self.investimentos_repo.inserir(
                data=data_base,
                categoria=self._safe_str(row.get("categoria"), "Renda Fixa"),
                aporte=self._safe_float(row.get("aporte"), 0.0),
                total_aportado=self._safe_float(row.get("total aportado"), 0.0),
                rendimento=self._safe_float(row.get("rendimento"), 0.0),
                patrimonio_total=self._safe_float(row.get("patrimonio total"), 0.0),
                data_inicio=self._safe_date_str(row.get("data_inicio") or row.get("data"), default=data_base),
                data_fim=self._safe_date_str(row.get("data_fim") or row.get("data"), default=data_base),
                tipo_movimentacao=self._safe_str(row.get("tipo_movimentacao"), ""),
            )

        for row in data["controle_km"]:
            data_inicio = self._safe_date_str(row.get("data_inicio") or row.get("data"), default="")
            data_fim = self._safe_date_str(row.get("data_fim") or row.get("data"), default=data_inicio)
            self.controle_km_repo.inserir(
                data_inicio=data_inicio,
                data_fim=data_fim,
                km_total_rodado=self._safe_float(row.get("km_total_rodado"), 0.0),
            )

        for row in data["controle_litros"]:
            self.controle_litros_repo.inserir(
                data=self._safe_date_str(row.get("data"), default=""),
                litros=self._safe_float(row.get("litros"), 0.0),
            )

        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

        imported = {key: len(values) for key, values in data.items()}
        imported["cleared"] = int(cleared)
        return imported
