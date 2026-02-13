# app.py

import os
import json
import hashlib
import streamlit as st
from Data.database import criar_banco

from UI.dashboard_ui import pagina_dashboard
from UI.receitas_ui import pagina_receitas
from UI.despesas_ui import pagina_despesas
from UI.investimentos_ui import pagina_investimentos
from UI.cadastros_ui import pagina_cadastros


def _users_path():
    return os.path.join(os.path.dirname(__file__), ".streamlit", "users.json")


def _hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_users():
    path = _users_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users):
    path = _users_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _ensure_default_admin():
    users = _load_users()
    if "admin" not in users:
        users["admin"] = _hash_password("admin")
        _save_users(users)


def _login_required():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    _ensure_default_admin()
    st.title("Login")
    aba_login, aba_cadastro, aba_alterar = st.tabs(["Entrar", "Cadastrar-se", "Alterar senha"])

    with aba_login:
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            users = _load_users()
            if user_input in users and users[user_input] == _hash_password(pass_input):
                st.session_state.authenticated = True
                st.success("Login realizado.")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with aba_cadastro:
        novo_user = st.text_input("Novo usuário", key="novo_user")
        nova_senha = st.text_input("Nova senha", type="password", key="nova_senha")
        confirmar = st.text_input("Confirmar senha", type="password", key="confirmar_senha")
        if st.button("Cadastrar"):
            if not novo_user or not nova_senha:
                st.error("Preencha usuário e senha.")
            elif nova_senha != confirmar:
                st.error("As senhas não conferem.")
            else:
                users = _load_users()
                if novo_user in users:
                    st.error("Usuário já existe.")
                else:
                    users[novo_user] = _hash_password(nova_senha)
                    _save_users(users)
                    st.success("Cadastro realizado. Faça login.")

    with aba_alterar:
        usuario_alterar = st.text_input("Usuário", key="alt_user")
        senha_atual = st.text_input("Senha atual", type="password", key="alt_senha_atual")
        nova_senha_alt = st.text_input("Nova senha", type="password", key="alt_nova_senha")
        confirmar_alt = st.text_input("Confirmar nova senha", type="password", key="alt_confirmar")
        if st.button("Alterar senha"):
            users = _load_users()
            if usuario_alterar not in users:
                st.error("Usuário não encontrado.")
            elif users[usuario_alterar] != _hash_password(senha_atual):
                st.error("Senha atual inválida.")
            elif not nova_senha_alt:
                st.error("Informe a nova senha.")
            elif nova_senha_alt != confirmar_alt:
                st.error("As senhas não conferem.")
            else:
                users[usuario_alterar] = _hash_password(nova_senha_alt)
                _save_users(users)
                st.success("Senha alterada. Faça login.")
    st.stop()


# -----------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------

st.set_page_config(
    page_title="Driver Analytics",
    page_icon="🚗",
    layout="wide"
)


# -----------------------------------
# TÍTULO PRINCIPAL
# -----------------------------------

st.title("🚗 Driver Analytics")

_login_required()

# Logout rápido
with st.sidebar:
    if st.button("Sair"):
        st.session_state.authenticated = False
        st.rerun()

# -----------------------------------
# CONEXÃO COM BANCO
# -----------------------------------

criar_banco()


# -----------------------------------
# MENU LATERAL
# -----------------------------------

menu = st.sidebar.radio(
    "Navegação",
    [
        "Dashboard",
        "Receitas",
        "Despesas",
        "Investimentos",
        "Cadastros"
    ]
)


# -----------------------------------
# ROTEAMENTO
# -----------------------------------

if menu == "Dashboard":
    pagina_dashboard()

elif menu == "Receitas":
    pagina_receitas()

elif menu == "Despesas":
    pagina_despesas()

elif menu == "Investimentos":
    pagina_investimentos()

elif menu == "Cadastros":
    pagina_cadastros()
