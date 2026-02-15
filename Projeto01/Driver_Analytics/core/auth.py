"""Authentication helpers for Streamlit app with optional Supabase backend."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st
try:
    import bcrypt
except Exception:  # pragma: no cover - dependency may not be available in test env
    bcrypt = None

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


def _sessions_path() -> str:
    users = _users_path()
    base_dir = os.path.dirname(users)
    return os.path.join(base_dir, "sessions.json")


def _hash_text(value: str) -> str:
    """Legacy SHA-256 hash kept for backward compatibility/migration."""

    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _is_bcrypt_hash(value: str) -> bool:
    raw = str(value or "")
    return raw.startswith("$2a$") or raw.startswith("$2b$") or raw.startswith("$2y$")


def _hash_password(value: str) -> str:
    if bcrypt is None:
        raise RuntimeError("bcrypt não está disponível no ambiente.")
    hashed = bcrypt.hashpw(str(value).encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(stored_hash: str, plain_password: str) -> bool:
    raw_hash = str(stored_hash or "")
    if _is_bcrypt_hash(raw_hash):
        if bcrypt is None:
            return False
        try:
            return bool(bcrypt.checkpw(str(plain_password).encode("utf-8"), raw_hash.encode("utf-8")))
        except Exception:
            return False
    return raw_hash == _hash_text(plain_password)


def _needs_password_upgrade(stored_hash: str) -> bool:
    return not _is_bcrypt_hash(stored_hash)


def _normalize_username(value: str) -> str:
    return str(value or "").strip()


def _canonical_username(value: str) -> str:
    return _normalize_username(value).casefold()


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


def _json_load_sessions() -> dict[str, Any]:
    path = _sessions_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            raw = json.load(file)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _json_save_sessions(sessions: dict[str, Any]) -> None:
    path = _sessions_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(sessions, file, ensure_ascii=False, indent=2)


def _cleanup_expired_sessions(sessions: dict[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow()
    cleaned: dict[str, Any] = {}
    for token, payload in sessions.items():
        if not isinstance(payload, dict):
            continue
        username = str(payload.get("username", "")).strip()
        expires_at = str(payload.get("expires_at", "")).strip()
        if not username or not expires_at:
            continue
        try:
            expiry = datetime.fromisoformat(expires_at)
        except Exception:
            continue
        if expiry > now:
            cleaned[token] = {"username": username, "expires_at": expiry.isoformat()}
    return cleaned


def _create_session_token(username: str, ttl_days: int = 30) -> str:
    sessions = _cleanup_expired_sessions(_json_load_sessions())
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(days=int(ttl_days))).isoformat()
    sessions[token] = {"username": _normalize_username(username), "expires_at": expires_at}
    _json_save_sessions(sessions)
    return token


def _resolve_session_token(token: str) -> str:
    token_norm = str(token or "").strip()
    if not token_norm:
        return ""
    sessions = _cleanup_expired_sessions(_json_load_sessions())
    payload = sessions.get(token_norm)
    _json_save_sessions(sessions)
    if not isinstance(payload, dict):
        return ""
    return _normalize_username(payload.get("username", ""))


def _revoke_session_token(token: str) -> None:
    token_norm = str(token or "").strip()
    if not token_norm:
        return
    sessions = _cleanup_expired_sessions(_json_load_sessions())
    if token_norm in sessions:
        del sessions[token_norm]
    _json_save_sessions(sessions)


def _get_query_session_token() -> str:
    try:
        token = st.query_params.get("session")
    except Exception:
        return ""
    if isinstance(token, list):
        return str(token[0]).strip() if token else ""
    return str(token or "").strip()


def _set_query_session_token(token: str) -> None:
    token_norm = str(token or "").strip()
    if not token_norm:
        return
    try:
        st.query_params["session"] = token_norm
    except Exception:
        pass


def _clear_query_session_token() -> None:
    try:
        if "session" in st.query_params:
            del st.query_params["session"]
    except Exception:
        pass


def _json_get_user(username: str) -> dict[str, Any] | None:
    users = _json_load_users()
    username_norm = _normalize_username(username)
    raw = users.get(username_norm)
    if raw is None:
        target = _canonical_username(username_norm)
        for existing_name, existing_raw in users.items():
            if _canonical_username(existing_name) == target:
                username_norm = existing_name
                raw = existing_raw
                break
    if raw is None:
        return None
    # Backward compatibility with old format {"user": "password_hash"}
    if isinstance(raw, str):
        return {
            "username": username_norm,
            "password_hash": raw,
            "cpf": "",
            "nome_completo": "",
            "data_nascimento": "",
            "pergunta_secreta": "",
            "resposta_secreta_hash": "",
        }
    if isinstance(raw, dict):
        raw["username"] = username_norm
        return raw
    return None


def _json_upsert_user(payload: dict[str, Any]) -> None:
    username = _normalize_username(payload["username"])
    users = _json_load_users()
    users[username] = {
        "password_hash": payload["password_hash"],
        "cpf": payload.get("cpf", ""),
        "nome_completo": payload.get("nome_completo", ""),
        "data_nascimento": payload.get("data_nascimento", ""),
        "pergunta_secreta": payload.get("pergunta_secreta", ""),
        "resposta_secreta_hash": payload.get("resposta_secreta_hash", ""),
    }
    _json_save_users(users)


def _sqlite_get_user(username: str) -> dict[str, Any] | None:
    username_norm = _normalize_username(username)
    _ensure_sqlite_users_table()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, password_hash, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
        FROM usuarios WHERE username = ?
        """,
        (username_norm,),
    )
    row = cur.fetchone()
    if not row:
        cur.execute(
            """
            SELECT username, password_hash, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
            FROM usuarios
            WHERE username = ? COLLATE NOCASE
            LIMIT 1
            """,
            (username_norm,),
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
    username = _normalize_username(payload["username"])
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
            username,
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
    username_norm = _normalize_username(username)
    client = get_supabase_client()
    if not client:
        return None
    try:
        data = client.table("usuarios").select("*").eq("username", username_norm).limit(1).execute().data
        if not data:
            data = client.table("usuarios").select("*").ilike("username", username_norm).limit(1).execute().data
    except Exception:
        return None
    if not data:
        return None
    return data[0]


def _supabase_upsert_user(payload: dict[str, Any]) -> bool:
    username = _normalize_username(payload["username"])
    payload_norm = dict(payload)
    payload_norm["username"] = username
    client = get_supabase_client()
    if not client:
        return False
    try:
        existing = client.table("usuarios").select("id").eq("username", username).limit(1).execute().data
        if existing:
            client.table("usuarios").update(payload_norm).eq("username", username).execute()
        else:
            client.table("usuarios").insert(payload_norm).execute()
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


def _authenticate_user(username: str, password: str) -> tuple[bool, dict[str, Any] | None]:
    """Authenticate against all backends to avoid stale-source mismatches."""

    username_norm = _normalize_username(username)
    for getter in (_supabase_get_user, _sqlite_get_user, _json_get_user):
        user = getter(username_norm)
        if user and _verify_password(str(user.get("password_hash", "")), password):
            return True, user
    return False, None


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


def _first_registered_username() -> str:
    """Return the first non-admin username found across backends."""

    client = get_supabase_client()
    if client:
        try:
            rows = (
                client.table("usuarios")
                .select("username")
                .neq("username", "admin")
                .limit(1)
                .execute()
                .data
            )
            if rows and rows[0].get("username"):
                return _normalize_username(rows[0]["username"])
        except Exception:
            pass

    _ensure_sqlite_users_table()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username
        FROM usuarios
        WHERE username <> 'admin'
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        return _normalize_username(row[0])

    users = _json_load_users()
    for username in users.keys():
        username_norm = _normalize_username(username)
        if username_norm and username_norm.casefold() != "admin":
            return username_norm
    return ""


def _registration_locked() -> bool:
    """Lock registration after first non-admin user is created."""

    return _supabase_has_non_admin_user() or _sqlite_has_non_admin_user() or _json_has_non_admin_user()


def _upsert_user(payload: dict[str, Any]) -> bool:
    username = _normalize_username(payload.get("username", ""))
    payload_norm = dict(payload)
    payload_norm["username"] = username

    wrote_any = False
    if _supabase_upsert_user(payload_norm):
        wrote_any = True

    try:
        _sqlite_upsert_user(payload_norm)
        wrote_any = True
    except Exception:
        pass

    try:
        _json_upsert_user(payload_norm)
        wrote_any = True
    except Exception:
        pass

    return wrote_any


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
    try:
        admin_password_hash = _hash_password("admin")
    except RuntimeError:
        admin_password_hash = _hash_text("admin")
    _upsert_user(
        {
            "username": "admin",
            "password_hash": admin_password_hash,
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
    if "current_user" not in st.session_state:
        st.session_state.current_user = ""
    if "session_token" not in st.session_state:
        st.session_state.session_token = ""

    if not st.session_state.authenticated:
        token_from_query = _get_query_session_token()
        user_from_token = _resolve_session_token(token_from_query)
        if user_from_token:
            st.session_state.authenticated = True
            st.session_state.current_user = user_from_token
            st.session_state.session_token = token_from_query

    if st.session_state.authenticated:
        return True

    ensure_default_admin()
    st.title("Login")
    tab_login, tab_register, tab_change, tab_forgot = st.tabs(["Entrar", "Cadastrar-se", "Alterar senha", "Esqueci minha senha"])

    with tab_login:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            authenticated, auth_user = _authenticate_user(username, password)
            if authenticated and auth_user:
                if _needs_password_upgrade(str(auth_user.get("password_hash", ""))):
                    try:
                        payload = dict(auth_user)
                        payload["password_hash"] = _hash_password(password)
                        _upsert_user(payload)
                    except RuntimeError:
                        st.warning("Aviso: bcrypt indisponível para migrar a senha para o padrão seguro.")
                st.session_state.authenticated = True
                st.session_state.current_user = str(auth_user.get("username", _normalize_username(username)))
                session_token = _create_session_token(st.session_state.current_user)
                st.session_state.session_token = session_token
                _set_query_session_token(session_token)
                st.success("Login realizado.")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

    with tab_register:
        locked = _registration_locked()
        if locked:
            existing_username = _first_registered_username()
            if existing_username:
                st.warning(
                    f"Cadastro bloqueado: não é possível cadastrar outra conta, pois já existe uma conta cadastrada. "
                    f"Usuário: {existing_username}."
                )
            else:
                st.warning("Cadastro bloqueado: não é possível cadastrar outra conta, pois já existe uma conta cadastrada.")
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
            username_norm = _normalize_username(new_user)
            if _registration_locked():
                existing_username = _first_registered_username()
                if existing_username:
                    st.error(
                        f"Cadastro bloqueado: não é possível cadastrar outra conta, pois já existe uma conta cadastrada. "
                        f"Usuário: {existing_username}."
                    )
                else:
                    st.error("Cadastro bloqueado: não é possível cadastrar outra conta, pois já existe uma conta cadastrada.")
            elif not username_norm or not new_pass:
                st.error("Preencha usuário e senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            elif not _normalize_cpf(cpf) or not pergunta.strip() or not resposta.strip():
                st.error("CPF, pergunta e resposta secreta são obrigatórios.")
            elif _get_user(username_norm):
                st.error("Usuário já existe.")
            else:
                try:
                    password_hash = _hash_password(new_pass)
                except RuntimeError:
                    st.error("Não foi possível cadastrar: bcrypt não está disponível no ambiente.")
                    st.stop()
                wrote = _upsert_user(
                    {
                        "username": username_norm,
                        "password_hash": password_hash,
                        "cpf": _normalize_cpf(cpf),
                        "nome_completo": nome.strip(),
                        "data_nascimento": _safe_iso_date(nascimento),
                        "pergunta_secreta": pergunta.strip(),
                        "resposta_secreta_hash": _hash_text(resposta),
                    }
                )
                if wrote:
                    st.success("Cadastro realizado. Faça login.")
                else:
                    st.error("Falha ao salvar cadastro. Verifique a conexão/configuração do banco.")

    with tab_change:
        username = st.text_input("Usuário", key="alt_user")
        current = st.text_input("Senha atual", type="password", key="alt_senha_atual")
        new_pass = st.text_input("Nova senha", type="password", key="alt_nova_senha")
        confirm = st.text_input("Confirmar nova senha", type="password", key="alt_confirmar")
        if st.button("Alterar senha"):
            authenticated, auth_user = _authenticate_user(username, current)
            username_norm = _normalize_username(username)
            if not authenticated or not auth_user:
                st.error("Usuário não encontrado.")
            elif not new_pass:
                st.error("Informe a nova senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            else:
                try:
                    password_hash = _hash_password(new_pass)
                except RuntimeError:
                    st.error("Não foi possível alterar a senha: bcrypt não está disponível no ambiente.")
                    st.stop()
                payload = dict(auth_user)
                payload["username"] = auth_user.get("username", username_norm)
                payload["password_hash"] = password_hash
                wrote = _upsert_user(payload)
                if wrote:
                    st.success("Senha alterada. Faça login.")
                else:
                    st.error("Falha ao atualizar senha. Verifique a conexão/configuração do banco.")

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
                    try:
                        password_hash = _hash_password(nova_senha)
                    except RuntimeError:
                        st.error("Não foi possível redefinir a senha: bcrypt não está disponível no ambiente.")
                        st.stop()
                    payload = dict(user)
                    payload["password_hash"] = password_hash
                    wrote = _upsert_user(payload)
                    if wrote:
                        st.success("Senha redefinida com sucesso.")
                    else:
                        st.error("Falha ao redefinir senha. Verifique a conexão/configuração do banco.")

    st.stop()


def render_logout_button() -> None:
    with st.sidebar:
        if st.button("Sair"):
            _revoke_session_token(st.session_state.get("session_token", ""))
            _clear_query_session_token()
            st.session_state.authenticated = False
            st.session_state.current_user = ""
            st.session_state.session_token = ""
            st.rerun()


def get_logged_username() -> str:
    return str(st.session_state.get("current_user", "")).strip()
