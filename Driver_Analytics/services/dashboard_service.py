"""Application service orchestrating repositories and metrics."""

from __future__ import annotations

import pandas as pd

from repositories.categorias_despesas_repository import CategoriasDespesasRepository
from repositories.controle_litros_repository import ControleLitrosRepository
from repositories.controle_km_repository import ControleKMRepository
from repositories.despesas_repository import DespesasRepository
from repositories.investimentos_repository import InvestimentosRepository
from repositories.receitas_repository import ReceitasRepository
from services.metrics_service import MetricsService


class DashboardService:
    """Facade service consumed by Streamlit UI pages."""

    def __init__(self) -> None:
        self.receitas_repo = ReceitasRepository()
        self.despesas_repo = DespesasRepository()
        self.controle_km_repo = ControleKMRepository()
        self.controle_litros_repo = ControleLitrosRepository()
        self.investimentos_repo = InvestimentosRepository()
        self.categorias_repo = CategoriasDespesasRepository()
        self.metrics = MetricsService()

    @staticmethod
    def _to_date_str(value) -> str:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return ""
        return parsed.date().isoformat()

    @staticmethod
    def _to_float(value) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _normalize_title(value: str) -> str:
        return " ".join(str(value).strip().split()).title()

    def listar_categorias_despesas(self) -> list[str]:
        """Return normalized list of expense categories."""

        df = self.categorias_repo.listar()
        if df.empty or "nome" not in df.columns:
            return []
        values = [self._normalize_title(v) for v in df["nome"].dropna().astype(str).tolist() if str(v).strip()]
        return sorted(set(values))

    def garantir_categoria_despesa(self, nome: str) -> str:
        """Ensure category exists and return normalized display value."""

        normalized = self._normalize_title(nome)
        if not normalized:
            raise ValueError("Informe uma categoria válida.")

        existentes = {v.casefold(): v for v in self.listar_categorias_despesas()}
        if normalized.casefold() not in existentes:
            self.categorias_repo.inserir(normalized)
        return normalized

    def _receita_duplicada(
        self,
        data: str,
        valor: float,
        km: float,
        tempo_trabalhado: int,
        km_rodado_total: float = 0.0,
        ignore_id: int | None = None,
    ) -> bool:
        df = self.listar_receitas()
        if df.empty:
            return False
        df_cmp = df.copy()
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["valor_cmp"] = pd.to_numeric(df_cmp["valor"], errors="coerce").fillna(0.0)
        df_cmp["km_cmp"] = pd.to_numeric(df_cmp["km"], errors="coerce").fillna(0.0)
        if "km_rodado_total" not in df_cmp.columns:
            df_cmp["km_rodado_total"] = 0.0
        df_cmp["km_rodado_total_cmp"] = pd.to_numeric(df_cmp["km_rodado_total"], errors="coerce").fillna(0.0)
        df_cmp["tempo_cmp"] = pd.to_numeric(df_cmp["tempo trabalhado"], errors="coerce").fillna(0).astype(int)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["valor_cmp"] == self._to_float(valor))
            & (df_cmp["km_cmp"] == self._to_float(km))
            & (df_cmp["km_rodado_total_cmp"] == self._to_float(km_rodado_total))
            & (df_cmp["tempo_cmp"] == self._to_int(tempo_trabalhado))
        ).any()

    def _despesa_duplicada(self, data: str, categoria: str, valor: float, ignore_id: int | None = None) -> bool:
        df = self.listar_despesas()
        if df.empty:
            return False
        df_cmp = df.copy()
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp["data"], errors="coerce").dt.date.astype(str)
        df_cmp["categoria_cmp"] = df_cmp["categoria"].astype(str).str.strip().str.lower()
        df_cmp["valor_cmp"] = pd.to_numeric(df_cmp["valor"], errors="coerce").fillna(0.0)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["categoria_cmp"] == str(categoria).strip().lower())
            & (df_cmp["valor_cmp"] == self._to_float(valor))
        ).any()

    @staticmethod
    def _normalize_tipo_despesa(value: str) -> str:
        raw = str(value or "").strip().upper()
        if raw in {"RECORRENTE", "FIXA", "VARIAVEL"}:
            return raw
        return "VARIAVEL"

    @staticmethod
    def _normalize_esfera_despesa(value: str) -> str:
        raw = str(value or "").strip().upper()
        if raw in {"NEGOCIO", "PESSOAL"}:
            return raw
        return "NEGOCIO"

    def _investimento_duplicado(
        self,
        data: str,
        categoria: str,
        aporte: float,
        rendimento: float,
        ignore_id: int | None = None,
    ) -> bool:
        df = self.listar_investimentos()
        if df.empty:
            return False
        df_cmp = df.copy()
        if "categoria" not in df_cmp.columns:
            df_cmp["categoria"] = "Renda Fixa"
        data_base_col = "data_fim" if "data_fim" in df_cmp.columns else "data"
        df_cmp["data_cmp"] = pd.to_datetime(df_cmp[data_base_col], errors="coerce").dt.date.astype(str)
        df_cmp["categoria_cmp"] = df_cmp["categoria"].astype(str).str.strip().str.lower()
        df_cmp["aporte_cmp"] = pd.to_numeric(df_cmp["aporte"], errors="coerce").fillna(0.0)
        df_cmp["rendimento_cmp"] = pd.to_numeric(df_cmp["rendimento"], errors="coerce").fillna(0.0)
        if ignore_id is not None and "id" in df_cmp.columns:
            df_cmp = df_cmp[df_cmp["id"] != int(ignore_id)]
        return (
            (df_cmp["data_cmp"] == self._to_date_str(data))
            & (df_cmp["categoria_cmp"] == str(categoria).strip().lower())
            & (df_cmp["aporte_cmp"] == self._to_float(aporte))
            & (df_cmp["rendimento_cmp"] == self._to_float(rendimento))
        ).any()

    def calcular_aporte_investimento(
        self,
        data: str,
        categoria: str,
        patrimonio_total: float,
        rendimento_total: float,
        ignore_id: int | None = None,
    ) -> float:
        """Infer aporte from current patrimônio/rendimento and previous snapshot in same categoria."""

        patrimonio_atual = self._to_float(patrimonio_total)
        rendimento_atual = self._to_float(rendimento_total)
        if patrimonio_atual < 0 or rendimento_atual < 0:
            raise ValueError("Patrimônio e rendimento devem ser não negativos.")

        aporte_total_atual = patrimonio_atual - rendimento_atual
        if aporte_total_atual < 0:
            raise ValueError("Rendimento não pode ser maior que o patrimônio total.")

        df = self.listar_investimentos()
        if df.empty:
            return aporte_total_atual

        work_df = df.copy()
        if "categoria" not in work_df.columns:
            work_df["categoria"] = "Renda Fixa"
        work_df["data"] = pd.to_datetime(work_df["data"], errors="coerce")
        work_df["patrimonio total"] = pd.to_numeric(work_df["patrimonio total"], errors="coerce").fillna(0.0)
        work_df["rendimento"] = pd.to_numeric(work_df["rendimento"], errors="coerce").fillna(0.0)
        work_df = work_df[work_df["categoria"].astype(str).str.strip().str.lower() == str(categoria).strip().lower()]
        if ignore_id is not None and "id" in work_df.columns:
            work_df = work_df[work_df["id"] != int(ignore_id)]

        data_atual = pd.to_datetime(data, errors="coerce")
        if pd.isna(data_atual):
            raise ValueError("Data do investimento inválida.")

        anteriores = work_df[work_df["data"] < data_atual]
        if anteriores.empty:
            aporte_total_anterior = 0.0
        else:
            ultimo = anteriores.sort_values(by=["data", "id"], ascending=[True, True]).iloc[-1]
            aporte_total_anterior = float(ultimo["patrimonio total"]) - float(ultimo["rendimento"])

        aporte_atual = aporte_total_atual - aporte_total_anterior
        if aporte_atual < 0:
            # Prevent negative aporte snapshots when user reports no rendimento/market oscillation.
            return 0.0

        return float(aporte_atual)

    def listar_receitas(self) -> pd.DataFrame:
        return self.receitas_repo.listar()

    def listar_despesas(self) -> pd.DataFrame:
        return self.despesas_repo.listar()

    def listar_controle_km(self) -> pd.DataFrame:
        return self.controle_km_repo.listar()

    def listar_controle_litros(self) -> pd.DataFrame:
        return self.controle_litros_repo.listar()

    def listar_investimentos(self) -> pd.DataFrame:
        return self.investimentos_repo.listar()

    def criar_controle_km(self, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        self.controle_km_repo.inserir(data_inicio, data_fim, km_total_rodado)

    def atualizar_controle_km(self, item_id: int, data_inicio: str, data_fim: str, km_total_rodado: float) -> None:
        self.controle_km_repo.atualizar(item_id, data_inicio, data_fim, km_total_rodado)

    def deletar_controle_km(self, item_id: int) -> None:
        self.controle_km_repo.deletar(item_id)

    def criar_controle_litros(self, data: str, litros: float) -> None:
        self.controle_litros_repo.inserir(data, litros)

    def atualizar_controle_litros(self, item_id: int, data: str, litros: float) -> None:
        self.controle_litros_repo.atualizar(item_id, data, litros)

    def deletar_controle_litros(self, item_id: int) -> None:
        self.controle_litros_repo.deletar(item_id)

    def criar_receita(
        self,
        data: str,
        valor: float,
        km: float,
        tempo_trabalhado: int,
        observacao: str = "",
        km_rodado_total: float = 0.0,
    ) -> None:
        if self._receita_duplicada(data, valor, km, tempo_trabalhado, km_rodado_total=km_rodado_total):
            raise ValueError("Registro já existente.")
        self.receitas_repo.inserir(data, valor, km, tempo_trabalhado, observacao, km_rodado_total=km_rodado_total)

    def atualizar_receita(
        self,
        item_id: int,
        data: str,
        valor: float,
        km: float,
        tempo_trabalhado: int,
        observacao: str,
        km_rodado_total: float = 0.0,
    ) -> None:
        if self._receita_duplicada(data, valor, km, tempo_trabalhado, km_rodado_total=km_rodado_total, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        self.receitas_repo.atualizar(
            item_id,
            data,
            valor,
            km,
            tempo_trabalhado,
            observacao,
            km_rodado_total=km_rodado_total,
        )

    def deletar_receita(self, item_id: int) -> None:
        self.receitas_repo.deletar(item_id)

    def criar_despesa(
        self,
        data: str,
        categoria: str,
        valor: float,
        observacao: str = "",
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
    ) -> None:
        categoria_ok = self.garantir_categoria_despesa(categoria)
        if self._despesa_duplicada(data, categoria_ok, valor):
            raise ValueError("Registro já existente.")
        tipo_ok = self._normalize_tipo_despesa(tipo_despesa)
        esfera_ok = self._normalize_esfera_despesa(esfera_despesa)
        subcat_ok = str(subcategoria_fixa or "").strip()
        if tipo_ok == "FIXA":
            subcat_ok = subcat_ok or str(observacao or "").strip() or "Sem subcategoria"
        else:
            subcat_ok = ""

        if tipo_ok == "VARIAVEL" and not subcat_ok:
            self.despesas_repo.inserir(data, categoria_ok, valor, observacao, esfera_despesa=esfera_ok, litros=litros)
        else:
            self.despesas_repo.inserir(
                data,
                categoria_ok,
                valor,
                observacao,
                tipo_despesa=tipo_ok,
                subcategoria_fixa=subcat_ok,
                esfera_despesa=esfera_ok,
                litros=litros,
            )

    def atualizar_despesa(
        self,
        item_id: int,
        data: str,
        categoria: str,
        valor: float,
        observacao: str,
        tipo_despesa: str = "VARIAVEL",
        subcategoria_fixa: str = "",
        esfera_despesa: str = "NEGOCIO",
        litros: float = 0.0,
    ) -> None:
        categoria_ok = self.garantir_categoria_despesa(categoria)
        if self._despesa_duplicada(data, categoria_ok, valor, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        tipo_ok = self._normalize_tipo_despesa(tipo_despesa)
        esfera_ok = self._normalize_esfera_despesa(esfera_despesa)
        subcat_ok = str(subcategoria_fixa or "").strip()
        if tipo_ok == "FIXA":
            subcat_ok = subcat_ok or str(observacao or "").strip() or "Sem subcategoria"
        else:
            subcat_ok = ""

        if tipo_ok == "VARIAVEL" and not subcat_ok:
            self.despesas_repo.atualizar(
                item_id,
                data,
                categoria_ok,
                valor,
                observacao,
                esfera_despesa=esfera_ok,
                litros=litros,
            )
        else:
            self.despesas_repo.atualizar(
                item_id,
                data,
                categoria_ok,
                valor,
                observacao,
                tipo_despesa=tipo_ok,
                subcategoria_fixa=subcat_ok,
                esfera_despesa=esfera_ok,
                litros=litros,
            )

    def deletar_despesa(self, item_id: int) -> None:
        self.despesas_repo.deletar(item_id)

    def criar_investimento(
        self,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        tipo_movimentacao: str | None = None,
    ) -> None:
        categoria_ok = str(categoria).strip() or "Renda Fixa"
        if self._investimento_duplicado(data, categoria_ok, aporte, rendimento):
            raise ValueError("Registro já existente.")
        self.investimentos_repo.inserir(
            data,
            categoria_ok,
            aporte,
            total_aportado,
            rendimento,
            patrimonio_total,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_movimentacao=tipo_movimentacao,
        )
        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

    def atualizar_investimento(
        self,
        item_id: int,
        data: str,
        categoria: str,
        aporte: float,
        total_aportado: float,
        rendimento: float,
        patrimonio_total: float,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        tipo_movimentacao: str | None = None,
    ) -> None:
        categoria_ok = str(categoria).strip() or "Renda Fixa"
        if self._investimento_duplicado(data, categoria_ok, aporte, rendimento, ignore_id=item_id):
            raise ValueError("Registro já existente.")
        self.investimentos_repo.atualizar(
            item_id,
            data,
            categoria_ok,
            aporte,
            total_aportado,
            rendimento,
            patrimonio_total,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo_movimentacao=tipo_movimentacao,
        )
        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

    def deletar_investimento(self, item_id: int) -> None:
        self.investimentos_repo.deletar(item_id)
        self.investimentos_repo.recalcular_total_aportado()
        self.investimentos_repo.recalcular_patrimonio_total()

    def recalcular_total_aportado(self) -> None:
        self.investimentos_repo.recalcular_total_aportado()

    def recalcular_patrimonio_total(self) -> None:
        self.investimentos_repo.recalcular_patrimonio_total()

    def resumo_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> dict:
        return self.metrics.resumo_mensal(df_receitas, df_despesas)

    def score_mensal(self, df_receitas: pd.DataFrame, df_despesas: pd.DataFrame) -> int:
        return self.metrics.score_mensal(df_receitas, df_despesas)
