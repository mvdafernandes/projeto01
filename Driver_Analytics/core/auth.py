"""Authentication helpers for Streamlit app with optional Supabase backend."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from typing import Any

import streamlit as st

from core.config import get_settings
from core.database import get_sqlite_connection, get_supabase_client


def _ensure_sqlite_users_table() -> None:
    """Ensure local auth table exists before sqlite auth operations."""

    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            cpf TEXT UNIQUE,
            nome_completo TEXT,
            data_nascimento TEXT,
            pergunta_secreta TEXT,
            resposta_secreta_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def _users_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    rel_path = get_settings().users_file
    return os.path.join(base_dir, rel_path)


def _hash_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _normalize_cpf(value: str) -> str:
    return "".join([c for c in str(value) if c.isdigit()])


def _safe_iso_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _json_load_users() -> dict[str, Any]:
    path = _users_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _json_save_users(users: dict[str, Any]) -> None:
    path = _users_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=2)


def _json_get_user(username: str) -> dict[str, Any] | None:
    users = _json_load_users()
    raw = users.get(username)
    if raw is None:
        return None
    # Backward compatibility with old format {"user": "password_hash"}
    if isinstance(raw, str):
        return {
            "username": username,
            "password_hash": raw,
            "cpf": "",
            "nome_completo": "",
            "data_nascimento": "",
            "pergunta_secreta": "",
            "resposta_secreta_hash": "",
        }
    if isinstance(raw, dict):
        raw["username"] = username
        return raw
    return None


def _json_upsert_user(payload: dict[str, Any]) -> None:
    users = _json_load_users()
    users[payload["username"]] = {
        "password_hash": payload["password_hash"],
        "cpf": payload.get("cpf", ""),
        "nome_completo": payload.get("nome_completo", ""),
        "data_nascimento": payload.get("data_nascimento", ""),
        "pergunta_secreta": payload.get("pergunta_secreta", ""),
        "resposta_secreta_hash": payload.get("resposta_secreta_hash", ""),
    }
    _json_save_users(users)


def _sqlite_get_user(username: str) -> dict[str, Any] | None:
    _ensure_sqlite_users_table()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, password_hash, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
        FROM usuarios WHERE username = ?
        """,
        (username,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "username": row[0],
        "password_hash": row[1],
        "cpf": row[2] or "",
        "nome_completo": row[3] or "",
        "data_nascimento": row[4] or "",
        "pergunta_secreta": row[5] or "",
        "resposta_secreta_hash": row[6] or "",
    }


def _sqlite_upsert_user(payload: dict[str, Any]) -> None:
    _ensure_sqlite_users_table()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO usuarios (username, password_hash, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            password_hash=excluded.password_hash,
            cpf=excluded.cpf,
            nome_completo=excluded.nome_completo,
            data_nascimento=excluded.data_nascimento,
            pergunta_secreta=excluded.pergunta_secreta,
            resposta_secreta_hash=excluded.resposta_secreta_hash
        """,
        (
            payload["username"],
            payload["password_hash"],
            payload.get("cpf", ""),
            payload.get("nome_completo", ""),
            payload.get("data_nascimento", ""),
            payload.get("pergunta_secreta", ""),
            payload.get("resposta_secreta_hash", ""),
        ),
    )
    conn.commit()
    conn.close()


def _supabase_get_user(username: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = client.table("usuarios").select("*").eq("username", username).limit(1).execute().data
    except Exception:
        return None
    if not data:
        return None
    return data[0]


def _supabase_upsert_user(payload: dict[str, Any]) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        existing = client.table("usuarios").select("id").eq("username", payload["username"]).limit(1).execute().data
        if existing:
            client.table("usuarios").update(payload).eq("username", payload["username"]).execute()
        else:
            client.table("usuarios").insert(payload).execute()
        return True
    except Exception:
        return False


def _get_user(username: str) -> dict[str, Any] | None:
    user = _supabase_get_user(username)
    if user is not None:
        return user
    user = _sqlite_get_user(username)
    if user is not None:
        return user
    return _json_get_user(username)


def _supabase_has_non_admin_user() -> bool:
    """Return True when there is at least one non-admin user in Supabase."""

    client = get_supabase_client()
    if not client:
        return False
    try:
        rows = client.table("usuarios").select("username").neq("username", "admin").limit(1).execute().data
        return bool(rows)
    except Exception:
        return False


def _sqlite_has_non_admin_user() -> bool:
    """Return True when there is at least one non-admin user in SQLite."""

    _ensure_sqlite_users_table()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM usuarios
        WHERE username <> 'admin'
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    return bool(row)


def _json_has_non_admin_user() -> bool:
    """Return True when there is at least one non-admin user in JSON fallback."""

    users = _json_load_users()
    for username in users.keys():
        if str(username).strip().lower() != "admin":
            return True
    return False


def _registration_locked() -> bool:
    """Lock registration after first non-admin user is created."""

    return _supabase_has_non_admin_user() or _sqlite_has_non_admin_user() or _json_has_non_admin_user()


def _upsert_user(payload: dict[str, Any]) -> None:
    if _supabase_upsert_user(payload):
        return
    try:
        _sqlite_upsert_user(payload)
        return
    except Exception:
        _json_upsert_user(payload)


def _find_user_for_recovery(cpf: str, data_nascimento: str, pergunta: str, resposta_hash: str) -> dict[str, Any] | None:
    cpf_norm = _normalize_cpf(cpf)
    data_iso = _safe_iso_date(data_nascimento)
    pergunta_norm = str(pergunta).strip()

    client = get_supabase_client()
    if client:
        try:
            rows = (
                client.table("usuarios")
                .select("*")
                .eq("cpf", cpf_norm)
                .eq("data_nascimento", data_iso)
                .eq("pergunta_secreta", pergunta_norm)
                .eq("resposta_secreta_hash", resposta_hash)
                .limit(1)
                .execute()
                .data
            )
            if rows:
                return rows[0]
        except Exception:
            pass

    _ensure_sqlite_users_table()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, password_hash, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
        FROM usuarios
        WHERE cpf = ? AND data_nascimento = ? AND pergunta_secreta = ? AND resposta_secreta_hash = ?
        LIMIT 1
        """,
        (cpf_norm, data_iso, pergunta_norm, resposta_hash),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "username": row[0],
            "password_hash": row[1],
            "cpf": row[2] or "",
            "nome_completo": row[3] or "",
            "data_nascimento": row[4] or "",
            "pergunta_secreta": row[5] or "",
            "resposta_secreta_hash": row[6] or "",
        }

    users = _json_load_users()
    for username, raw in users.items():
        if isinstance(raw, str):
            continue
        if not isinstance(raw, dict):
            continue
        if (
            _normalize_cpf(raw.get("cpf", "")) == cpf_norm
            and str(raw.get("data_nascimento", "")).strip() == data_iso
            and str(raw.get("pergunta_secreta", "")).strip() == pergunta_norm
            and str(raw.get("resposta_secreta_hash", "")).strip() == resposta_hash
        ):
            out = dict(raw)
            out["username"] = username
            return out
    return None


def ensure_default_admin() -> None:
    if _get_user("admin"):
        return
    _upsert_user(
        {
            "username": "admin",
            "password_hash": _hash_text("admin"),
            "cpf": "",
            "nome_completo": "Administrador",
            "data_nascimento": "",
            "pergunta_secreta": "",
            "resposta_secreta_hash": "",
        }
    )


def login_required() -> bool:
    """Render login screen and stop app flow when unauthenticated."""

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    ensure_default_admin()
    st.title("Login")
    tab_login, tab_register, tab_change, tab_forgot = st.tabs(["Entrar", "Cadastrar-se", "Alterar senha", "Esqueci minha senha"])

    with tab_login:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user = _get_user(username)
            if user and user.get("password_hash") == _hash_text(password):
                st.session_state.authenticated = True
                st.success("Login realizado.")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with tab_register:
        locked = _registration_locked()
        if locked:
            st.warning("Cadastro bloqueado: já existe um usuário principal cadastrado.")
        new_user = st.text_input("Novo usuário", key="novo_user", disabled=locked)
        new_pass = st.text_input("Nova senha", type="password", key="nova_senha", disabled=locked)
        confirm = st.text_input("Confirmar senha", type="password", key="confirmar_senha", disabled=locked)
        nome = st.text_input("Nome completo", key="cad_nome", disabled=locked)
        cpf = st.text_input("CPF", key="cad_cpf", disabled=locked)
        nascimento = st.date_input(
            "Data de nascimento",
            key="cad_nasc",
            min_value=date(1950, 1, 1),
            max_value=date.today(),
            value=date(1990, 1, 1),
            disabled=locked,
        )
        pergunta = st.text_input("Pergunta secreta", key="cad_pergunta", disabled=locked)
        resposta = st.text_input("Resposta secreta", type="password", key="cad_resposta", disabled=locked)

        if st.button("Cadastrar", disabled=locked):
            if _registration_locked():
                st.error("Cadastro bloqueado: somente um usuário pode ser criado.")
            elif not new_user or not new_pass:
                st.error("Preencha usuário e senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            elif not _normalize_cpf(cpf) or not pergunta.strip() or not resposta.strip():
                st.error("CPF, pergunta e resposta secreta são obrigatórios.")
            elif _get_user(new_user):
                st.error("Usuário já existe.")
            else:
                _upsert_user(
                    {
                        "username": new_user.strip(),
                        "password_hash": _hash_text(new_pass),
                        "cpf": _normalize_cpf(cpf),
                        "nome_completo": nome.strip(),
                        "data_nascimento": _safe_iso_date(nascimento),
                        "pergunta_secreta": pergunta.strip(),
                        "resposta_secreta_hash": _hash_text(resposta),
                    }
                )
                st.success("Cadastro realizado. Faça login.")

    with tab_change:
        username = st.text_input("Usuário", key="alt_user")
        current = st.text_input("Senha atual", type="password", key="alt_senha_atual")
        new_pass = st.text_input("Nova senha", type="password", key="alt_nova_senha")
        confirm = st.text_input("Confirmar nova senha", type="password", key="alt_confirmar")
        if st.button("Alterar senha"):
            user = _get_user(username)
            if not user:
                st.error("Usuário não encontrado.")
            elif user.get("password_hash") != _hash_text(current):
                st.error("Senha atual inválida.")
            elif not new_pass:
                st.error("Informe a nova senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            else:
                payload = dict(user)
                payload["username"] = username
                payload["password_hash"] = _hash_text(new_pass)
                _upsert_user(payload)
                st.success("Senha alterada. Faça login.")

    with tab_forgot:
        cpf = st.text_input("CPF", key="rec_cpf")
        nascimento = st.date_input(
            "Data de nascimento",
            key="rec_nasc",
            min_value=date(1950, 1, 1),
            max_value=date.today(),
            value=date(1990, 1, 1),
        )
        pergunta = st.text_input("Pergunta secreta", key="rec_pergunta")
        resposta = st.text_input("Resposta secreta", type="password", key="rec_resposta")
        nova_senha = st.text_input("Nova senha", type="password", key="rec_nova")
        confirma = st.text_input("Confirmar nova senha", type="password", key="rec_confirma")

        if st.button("Redefinir senha"):
            if not cpf.strip() or not pergunta.strip() or not resposta.strip():
                st.error("Preencha CPF, pergunta e resposta secreta.")
            elif not nova_senha or nova_senha != confirma:
                st.error("As senhas não conferem.")
            else:
                user = _find_user_for_recovery(cpf, nascimento, pergunta, _hash_text(resposta))
                if not user:
                    st.error("Dados de recuperação inválidos.")
                else:
                    payload = dict(user)
                    payload["password_hash"] = _hash_text(nova_senha)
                    _upsert_user(payload)
                    st.success("Senha redefinida com sucesso.")

    st.stop()


def render_logout_button() -> None:
    with st.sidebar:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()
