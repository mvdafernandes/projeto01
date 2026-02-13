"""Legacy CRUD API delegating to repositories/services."""

from __future__ import annotations

from services.dashboard_service import DashboardService


_service = DashboardService()


# RECEITAS

def inserir_receita(data, valor, km, tempo_trabalhado, observacao=""):
    _service.criar_receita(data, valor, km, tempo_trabalhado, observacao)


def listar_receitas():
    return _service.listar_receitas()


def buscar_receita_por_id(item_id):
    return _service.receitas_repo.buscar_por_id(int(item_id))


def atualizar_receita(item_id, data, valor, km, tempo_trabalhado, observacao):
    _service.atualizar_receita(int(item_id), data, valor, km, tempo_trabalhado, observacao)


def deletar_receita(item_id):
    _service.deletar_receita(int(item_id))


# DESPESAS

def inserir_despesa(data, categoria, valor, observacao=""):
    _service.criar_despesa(data, categoria, valor, observacao)


def listar_despesas():
    return _service.listar_despesas()


def buscar_despesa_por_id(item_id):
    return _service.despesas_repo.buscar_por_id(int(item_id))


def atualizar_despesa(item_id, data, categoria, valor, observacao):
    _service.atualizar_despesa(int(item_id), data, categoria, valor, observacao)


def deletar_despesa(item_id):
    _service.deletar_despesa(int(item_id))


# INVESTIMENTOS

def inserir_investimento(data, aporte, total_aportado, rendimento, patrimonio_total):
    _service.criar_investimento(data, aporte, total_aportado, rendimento, patrimonio_total)


def listar_investimentos():
    return _service.listar_investimentos()


def buscar_investimento_por_id(item_id):
    return _service.investimentos_repo.buscar_por_id(int(item_id))


def atualizar_investimento(item_id, data, aporte, total_aportado, rendimento, patrimonio_total):
    _service.atualizar_investimento(int(item_id), data, aporte, total_aportado, rendimento, patrimonio_total)


def deletar_investimento(item_id):
    _service.deletar_investimento(int(item_id))


def recalcular_total_aportado():
    _service.recalcular_total_aportado()
