"""Backup/import service for user business data."""

from __future__ import annotations

import json
from io import StringIO
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from core.auth import get_logged_username
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
    BACKUP_TABLES = ["receitas", "despesas", "investimentos", "controle_km", "controle_litros", "categorias_despesas"]

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
        rows: list[dict[str, Any]] = [
            {
                "record_type": "meta",
                "format": str(payload.get("format", self.BACKUP_FORMAT)),
                "version": int(payload.get("version", self.BACKUP_VERSION)),
                "generated_at": str(payload.get("generated_at", "")),
                "username": str(payload.get("username", "")),
                "table": "",
                "row_data": "",
            }
        ]
        data = payload.get("data", {})
        for table in self.BACKUP_TABLES:
            records = data.get(table, []) if isinstance(data, dict) else []
            if not records:
                rows.append(
                    {
                        "record_type": "table",
                        "format": "",
                        "version": "",
                        "generated_at": "",
                        "username": "",
                        "table": table,
                        "row_data": "",
                    }
                )
                continue
            for item in records:
                rows.append(
                    {
                        "record_type": "row",
                        "format": "",
                        "version": "",
                        "generated_at": "",
                        "username": "",
                        "table": table,
                        "row_data": json.dumps(dict(item), ensure_ascii=False),
                    }
                )
        frame = pd.DataFrame(rows)
        return frame.to_csv(index=False).encode("utf-8")

    def loads_backup(self, raw: bytes) -> dict[str, Any]:
        try:
            text = raw.decode("utf-8-sig")
            frame = pd.read_csv(StringIO(text), dtype=str).fillna("")
        except Exception as exc:
            raise ValueError("Arquivo inválido. Use um backup CSV gerado pelo Driver Analytics.") from exc
        if frame.empty:
            raise ValueError("Estrutura de backup CSV inválida.")

        required_cols = {"record_type", "format", "version", "generated_at", "username", "table", "row_data"}
        if not required_cols.issubset(set(frame.columns)):
            raise ValueError("Colunas obrigatórias do backup CSV estão ausentes.")

        meta_rows = frame[frame["record_type"] == "meta"]
        if meta_rows.empty:
            raise ValueError("Metadados do backup CSV não encontrados.")
        meta = meta_rows.iloc[0]
        try:
            version = int(str(meta.get("version", "")).strip() or "0")
        except Exception:
            version = 0

        data: dict[str, list[dict[str, Any]]] = {name: [] for name in self.BACKUP_TABLES}
        for _, row in frame.iterrows():
            if str(row.get("record_type", "")).strip() != "row":
                continue
            table = str(row.get("table", "")).strip()
            if table not in data:
                continue
            row_data = str(row.get("row_data", "")).strip()
            if not row_data:
                continue
            try:
                parsed = json.loads(row_data)
            except Exception as exc:
                raise ValueError(f"Linha inválida para tabela '{table}' no backup CSV.") from exc
            if isinstance(parsed, dict):
                data[table].append(parsed)

        counts = {key: len(values) for key, values in data.items()}
        return {
            "format": str(meta.get("format", "")).strip(),
            "version": version,
            "generated_at": str(meta.get("generated_at", "")).strip(),
            "username": str(meta.get("username", "")).strip(),
            "counts": counts,
            "data": data,
        }

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
        for key in self.BACKUP_TABLES:
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
        tables = self.BACKUP_TABLES
        if not client:
            raise RuntimeError("Supabase remoto indisponível para limpeza antes da importação.")
        for table in tables:
            try:
                client.table(table).delete().eq("user_id", int(user_id)).execute()
                deleted += 1
            except Exception:
                # Ignore unsupported tables/legacy schemas and continue with what is possible.
                pass

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
                recorrencia_tipo=self._safe_str(row.get("recorrencia_tipo"), ""),
                recorrencia_meses=int(self._safe_float(row.get("recorrencia_meses"), 0.0)),
                recorrencia_serie_id=self._safe_str(row.get("recorrencia_serie_id"), ""),
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
