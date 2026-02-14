"""Authentication helpers for Streamlit app."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Dict

import streamlit as st

from core.config import get_settings


def _users_path() -> str:
    """Resolve users JSON path from configuration."""

    base_dir = os.path.dirname(os.path.dirname(__file__))
    rel_path = get_settings().users_file
    return os.path.join(base_dir, rel_path)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def load_users() -> Dict[str, str]:
    """Load users from JSON file."""

    path = _users_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_users(users: Dict[str, str]) -> None:
    """Persist users into JSON file."""

    path = _users_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=2)


def ensure_default_admin() -> None:
    """Create default admin account on first run."""

    users = load_users()
    if "admin" not in users:
        users["admin"] = _hash_password("admin")
        save_users(users)


def login_required() -> bool:
    """Render login screen and stop app flow when unauthenticated."""

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    ensure_default_admin()
    st.title("Login")
    tab_login, tab_register, tab_change = st.tabs(["Entrar", "Cadastrar-se", "Alterar senha"])

    with tab_login:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            users = load_users()
            if username in users and users[username] == _hash_password(password):
                st.session_state.authenticated = True
                st.success("Login realizado.")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with tab_register:
        new_user = st.text_input("Novo usuário", key="novo_user")
        new_pass = st.text_input("Nova senha", type="password", key="nova_senha")
        confirm = st.text_input("Confirmar senha", type="password", key="confirmar_senha")
        if st.button("Cadastrar"):
            if not new_user or not new_pass:
                st.error("Preencha usuário e senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            else:
                users = load_users()
                if new_user in users:
                    st.error("Usuário já existe.")
                else:
                    users[new_user] = _hash_password(new_pass)
                    save_users(users)
                    st.success("Cadastro realizado. Faça login.")

    with tab_change:
        username = st.text_input("Usuário", key="alt_user")
        current = st.text_input("Senha atual", type="password", key="alt_senha_atual")
        new_pass = st.text_input("Nova senha", type="password", key="alt_nova_senha")
        confirm = st.text_input("Confirmar nova senha", type="password", key="alt_confirmar")
        if st.button("Alterar senha"):
            users = load_users()
            if username not in users:
                st.error("Usuário não encontrado.")
            elif users[username] != _hash_password(current):
                st.error("Senha atual inválida.")
            elif not new_pass:
                st.error("Informe a nova senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            else:
                users[username] = _hash_password(new_pass)
                save_users(users)
                st.success("Senha alterada. Faça login.")

    st.stop()


def render_logout_button() -> None:
    """Render sidebar logout button."""

    with st.sidebar:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()
