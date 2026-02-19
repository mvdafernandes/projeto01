"""Authentication and session management for Streamlit app."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import streamlit as st

from core.config import get_settings
from core.database import get_sqlite_connection, get_supabase_client
from core.security.passwords import hash_password, legacy_hash_password, needs_password_upgrade, verify_password


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_username(value: str) -> str:
    return str(value or "").strip()


def _normalize_cpf(value: str) -> str:
    return "".join([c for c in str(value) if c.isdigit()])


def _safe_iso_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _users_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    rel_path = get_settings().users_file
    return os.path.join(base_dir, rel_path)


def _json_load_users() -> dict[str, Any]:
    path = _users_path()
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as file:
        raw = json.load(file)
    return raw if isinstance(raw, dict) else {}


def _json_save_users(users: dict[str, Any]) -> None:
    path = _users_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=2)


def _ensure_sqlite_auth_tables() -> None:
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            cpf TEXT UNIQUE,
            nome_completo TEXT,
            data_nascimento TEXT,
            pergunta_secreta TEXT,
            resposta_secreta_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            last_seen_at TEXT,
            user_agent TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_rate_limits (
            key TEXT NOT NULL,
            action TEXT NOT NULL,
            failures INTEGER NOT NULL DEFAULT 0,
            blocked_until TEXT,
            last_failure_at TEXT,
            PRIMARY KEY (key, action)
        )
        """
    )
    conn.commit()
    conn.close()


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _supabase_get_user(username: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    if not client:
        return None
    username_n = _normalize_username(username)
    try:
        data = client.table("usuarios").select("*").eq("username", username_n).limit(1).execute().data
    except Exception:
        return None
    if not data:
        return None
    return dict(data[0])


def _sqlite_get_user(username: str) -> dict[str, Any] | None:
    _ensure_sqlite_auth_tables()
    username_n = _normalize_username(username)
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, password_hash, must_change_password, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
        FROM usuarios
        WHERE username = ? COLLATE NOCASE
        LIMIT 1
        """,
        (username_n,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "username": row[1],
        "password_hash": row[2],
        "must_change_password": int(row[3] or 0),
        "cpf": row[4] or "",
        "nome_completo": row[5] or "",
        "data_nascimento": row[6] or "",
        "pergunta_secreta": row[7] or "",
        "resposta_secreta_hash": row[8] or "",
    }


def _json_get_user(username: str) -> dict[str, Any] | None:
    users = _json_load_users()
    username_n = _normalize_username(username)
    for existing_name, payload in users.items():
        if _normalize_username(existing_name).casefold() != username_n.casefold():
            continue
        if isinstance(payload, str):
            return {
                "id": None,
                "username": existing_name,
                "password_hash": payload,
                "must_change_password": 0,
                "cpf": "",
                "nome_completo": "",
                "data_nascimento": "",
                "pergunta_secreta": "",
                "resposta_secreta_hash": "",
            }
        if isinstance(payload, dict):
            out = dict(payload)
            out["username"] = existing_name
            out.setdefault("id", None)
            out.setdefault("must_change_password", 0)
            return out
    return None


def _get_user(username: str) -> dict[str, Any] | None:
    user = _supabase_get_user(username)
    if user is not None:
        return user
    user = _sqlite_get_user(username)
    if user is not None:
        return user
    return _json_get_user(username)


def _upsert_user(payload: dict[str, Any]) -> bool:
    payload_n = dict(payload)
    payload_n["username"] = _normalize_username(payload_n.get("username", ""))
    payload_n["must_change_password"] = int(payload_n.get("must_change_password", 0) or 0)

    wrote = False
    client = get_supabase_client()
    if client:
        try:
            existing = client.table("usuarios").select("id").eq("username", payload_n["username"]).limit(1).execute().data
            if existing:
                client.table("usuarios").update(payload_n).eq("username", payload_n["username"]).execute()
            else:
                client.table("usuarios").insert(payload_n).execute()
            wrote = True
        except Exception:
            pass

    try:
        _ensure_sqlite_auth_tables()
        conn = get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO usuarios (
                username, password_hash, must_change_password, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash=excluded.password_hash,
                must_change_password=excluded.must_change_password,
                cpf=excluded.cpf,
                nome_completo=excluded.nome_completo,
                data_nascimento=excluded.data_nascimento,
                pergunta_secreta=excluded.pergunta_secreta,
                resposta_secreta_hash=excluded.resposta_secreta_hash
            """,
            (
                payload_n["username"],
                payload_n["password_hash"],
                int(payload_n.get("must_change_password", 0)),
                payload_n.get("cpf", ""),
                payload_n.get("nome_completo", ""),
                payload_n.get("data_nascimento", ""),
                payload_n.get("pergunta_secreta", ""),
                payload_n.get("resposta_secreta_hash", ""),
            ),
        )
        conn.commit()
        conn.close()
        wrote = True
    except Exception:
        pass

    # Keep JSON fallback only for backward compatibility.
    try:
        users = _json_load_users()
        users[payload_n["username"]] = {
            "password_hash": payload_n["password_hash"],
            "must_change_password": int(payload_n.get("must_change_password", 0)),
            "cpf": payload_n.get("cpf", ""),
            "nome_completo": payload_n.get("nome_completo", ""),
            "data_nascimento": payload_n.get("data_nascimento", ""),
            "pergunta_secreta": payload_n.get("pergunta_secreta", ""),
            "resposta_secreta_hash": payload_n.get("resposta_secreta_hash", ""),
        }
        _json_save_users(users)
        wrote = True
    except Exception:
        pass

    return wrote


def _get_logged_user() -> dict[str, Any] | None:
    username = _normalize_username(st.session_state.get("current_user", ""))
    if not username:
        return None
    return _get_user(username)


def _get_rate_limit(action: str, key: str) -> tuple[int, datetime | None]:
    _ensure_sqlite_auth_tables()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT failures, blocked_until FROM auth_rate_limits WHERE action = ? AND key = ?",
        (str(action), str(key)),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return 0, None
    blocked_until = None
    if row[1]:
        try:
            blocked_until = datetime.fromisoformat(str(row[1]))
        except Exception:
            blocked_until = None
    return int(row[0] or 0), blocked_until


def _set_rate_limit(action: str, key: str, failures: int, blocked_until: datetime | None) -> None:
    _ensure_sqlite_auth_tables()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO auth_rate_limits (action, key, failures, blocked_until, last_failure_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(action, key) DO UPDATE SET
            failures = excluded.failures,
            blocked_until = excluded.blocked_until,
            last_failure_at = excluded.last_failure_at
        """,
        (
            str(action),
            str(key),
            int(failures),
            blocked_until.isoformat() if blocked_until else None,
            _utc_now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def _rate_limited(action: str, key: str) -> bool:
    _, blocked_until = _get_rate_limit(action, key)
    return bool(blocked_until and blocked_until > _utc_now())


def _rate_limit_success(action: str, key: str) -> None:
    _set_rate_limit(action, key, 0, None)


def _rate_limit_failure(action: str, key: str, max_failures: int = 5, cooldown_minutes: int = 15) -> None:
    failures, _ = _get_rate_limit(action, key)
    failures += 1
    blocked_until = None
    if failures >= int(max_failures):
        blocked_until = _utc_now() + timedelta(minutes=int(cooldown_minutes))
    _set_rate_limit(action, key, failures, blocked_until)


def _authenticate_user(username: str, password: str) -> tuple[bool, dict[str, Any] | None]:
    username_n = _normalize_username(username)
    for getter in (_supabase_get_user, _sqlite_get_user, _json_get_user):
        user = getter(username_n)
        if not user:
            continue
        if verify_password(password, str(user.get("password_hash", ""))):
            return True, user
    return False, None


def _get_user_id(user: dict[str, Any]) -> int | None:
    value = user.get("id")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _sqlite_create_session(user_id: int, raw_token: str) -> tuple[str, str]:
    _ensure_sqlite_auth_tables()
    settings = get_settings()
    session_id = str(uuid.uuid4())
    now = _utc_now()
    expires = now + timedelta(days=int(settings.session_ttl_days))
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO auth_sessions (session_id, user_id, token_hash, created_at, expires_at, revoked_at, last_seen_at, user_agent)
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
        """,
        (session_id, int(user_id), _token_hash(raw_token), now.isoformat(), expires.isoformat(), now.isoformat(), ""),
    )
    conn.commit()
    conn.close()
    return session_id, raw_token


def _supabase_create_session(user_id: int, raw_token: str) -> tuple[str, str] | None:
    client = get_supabase_client()
    if not client:
        return None
    settings = get_settings()
    session_id = str(uuid.uuid4())
    now = _utc_now()
    expires = now + timedelta(days=int(settings.session_ttl_days))
    payload = {
        "session_id": session_id,
        "user_id": int(user_id),
        "token_hash": _token_hash(raw_token),
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "revoked_at": None,
        "last_seen_at": now.isoformat(),
        "user_agent": "",
    }
    try:
        client.table("auth_sessions").insert(payload).execute()
        return session_id, raw_token
    except Exception:
        return None


def _create_session(user: dict[str, Any]) -> tuple[str, str] | None:
    user_id = _get_user_id(user)
    if user_id is None:
        return None
    raw_token = secrets.token_urlsafe(48)
    remote = _supabase_create_session(user_id, raw_token)
    if remote is not None:
        return remote
    return _sqlite_create_session(user_id, raw_token)


def _sqlite_resolve_session(session_id: str, raw_token: str) -> dict[str, Any] | None:
    _ensure_sqlite_auth_tables()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.user_id, s.token_hash, s.expires_at, s.revoked_at, s.last_seen_at, u.username
        FROM auth_sessions s
        JOIN usuarios u ON u.id = s.user_id
        WHERE s.session_id = ?
        LIMIT 1
        """,
        (str(session_id),),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    user_id, token_hash, expires_at, revoked_at, last_seen_at, username = row
    if revoked_at:
        conn.close()
        return None
    if str(token_hash or "") != _token_hash(raw_token):
        conn.close()
        return None
    try:
        exp = datetime.fromisoformat(str(expires_at))
        if exp <= _utc_now():
            conn.close()
            return None
    except Exception:
        conn.close()
        return None

    now = _utc_now()
    cur.execute("UPDATE auth_sessions SET last_seen_at = ? WHERE session_id = ?", (now.isoformat(), str(session_id)))
    conn.commit()
    conn.close()
    return {
        "user_id": int(user_id),
        "username": str(username),
        "last_seen_at": str(last_seen_at or ""),
    }


def _supabase_resolve_session(session_id: str, raw_token: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    if not client:
        return None
    try:
        rows = client.table("auth_sessions").select("*").eq("session_id", str(session_id)).limit(1).execute().data
    except Exception:
        return None
    if not rows:
        return None
    session = dict(rows[0])
    if session.get("revoked_at"):
        return None
    if str(session.get("token_hash", "")) != _token_hash(raw_token):
        return None
    try:
        if datetime.fromisoformat(str(session.get("expires_at", ""))) <= _utc_now():
            return None
    except Exception:
        return None
    user_id = int(session.get("user_id", 0))
    try:
        client.table("auth_sessions").update({"last_seen_at": _utc_now().isoformat()}).eq("session_id", str(session_id)).execute()
    except Exception:
        pass
    try:
        user_rows = client.table("usuarios").select("username").eq("id", user_id).limit(1).execute().data
    except Exception:
        return None
    if not user_rows:
        return None
    return {
        "user_id": user_id,
        "username": str(user_rows[0].get("username", "")),
        "last_seen_at": str(session.get("last_seen_at", "")),
    }


def _resolve_session(session_id: str, raw_token: str) -> dict[str, Any] | None:
    if not session_id or not raw_token:
        return None
    remote = _supabase_resolve_session(session_id, raw_token)
    if remote is not None:
        return remote
    return _sqlite_resolve_session(session_id, raw_token)


def _revoke_session(session_id: str) -> None:
    if not session_id:
        return
    client = get_supabase_client()
    if client:
        try:
            client.table("auth_sessions").update({"revoked_at": _utc_now().isoformat()}).eq("session_id", str(session_id)).execute()
        except Exception:
            pass
    _ensure_sqlite_auth_tables()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute("UPDATE auth_sessions SET revoked_at = ? WHERE session_id = ?", (_utc_now().isoformat(), str(session_id)))
    conn.commit()
    conn.close()


def _maybe_rotate_session(session: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        last_seen = datetime.fromisoformat(str(session.get("last_seen_at", "")))
    except Exception:
        last_seen = _utc_now() - timedelta(hours=settings.session_rotation_hours + 1)
    if (_utc_now() - last_seen) < timedelta(hours=int(settings.session_rotation_hours)):
        return

    user = _get_user(str(session.get("username", "")))
    if not user:
        return
    new_session = _create_session(user)
    if not new_session:
        return
    old_session_id = str(st.session_state.get("session_id", ""))
    st.session_state.session_id = new_session[0]
    st.session_state.session_token = new_session[1]
    if old_session_id:
        _revoke_session(old_session_id)


def _has_non_admin_user() -> bool:
    client = get_supabase_client()
    if client:
        try:
            rows = client.table("usuarios").select("id").neq("username", "admin").limit(1).execute().data
            if rows:
                return True
        except Exception:
            pass

    _ensure_sqlite_auth_tables()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM usuarios WHERE username <> 'admin' LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return bool(row)


def ensure_default_admin() -> None:
    settings = get_settings()
    if settings.app_env != "dev":
        return
    if _get_user("admin"):
        return
    _upsert_user(
        {
            "username": "admin",
            "password_hash": hash_password("admin"),
            "must_change_password": 1,
            "cpf": "",
            "nome_completo": "Administrador",
            "data_nascimento": "",
            "pergunta_secreta": "",
            "resposta_secreta_hash": "",
        }
    )


def _upgrade_password_if_needed(user: dict[str, Any], plain_password: str) -> None:
    current_hash = str(user.get("password_hash", ""))
    if not needs_password_upgrade(current_hash):
        return
    payload = dict(user)
    payload["password_hash"] = hash_password(plain_password)
    _upsert_user(payload)


def _find_user_for_recovery(cpf: str, data_nascimento: str, pergunta: str, resposta_hash: str) -> dict[str, Any] | None:
    cpf_norm = _normalize_cpf(cpf)
    data_iso = _safe_iso_date(data_nascimento)
    pergunta_n = str(pergunta).strip()
    client = get_supabase_client()
    if client:
        try:
            rows = (
                client.table("usuarios")
                .select("*")
                .eq("cpf", cpf_norm)
                .eq("data_nascimento", data_iso)
                .eq("pergunta_secreta", pergunta_n)
                .eq("resposta_secreta_hash", resposta_hash)
                .limit(1)
                .execute()
                .data
            )
            if rows:
                return dict(rows[0])
        except Exception:
            pass
    _ensure_sqlite_auth_tables()
    conn = get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, username, password_hash, must_change_password, cpf, nome_completo, data_nascimento, pergunta_secreta, resposta_secreta_hash
        FROM usuarios
        WHERE cpf = ? AND data_nascimento = ? AND pergunta_secreta = ? AND resposta_secreta_hash = ?
        LIMIT 1
        """,
        (cpf_norm, data_iso, pergunta_n, resposta_hash),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": int(row[0]),
        "username": row[1],
        "password_hash": row[2],
        "must_change_password": int(row[3] or 0),
        "cpf": row[4] or "",
        "nome_completo": row[5] or "",
        "data_nascimento": row[6] or "",
        "pergunta_secreta": row[7] or "",
        "resposta_secreta_hash": row[8] or "",
    }


def login_required() -> bool:
    """Render login screen and stop app flow when unauthenticated."""

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = ""
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = ""
    if "session_token" not in st.session_state:
        st.session_state.session_token = ""
    if "must_change_password" not in st.session_state:
        st.session_state.must_change_password = False

    if not st.session_state.authenticated and st.session_state.session_id and st.session_state.session_token:
        session = _resolve_session(st.session_state.session_id, st.session_state.session_token)
        if session:
            st.session_state.authenticated = True
            st.session_state.current_user = str(session.get("username", ""))
            st.session_state.current_user_id = int(session.get("user_id", 0))
            _maybe_rotate_session(session)

    if st.session_state.authenticated:
        if bool(st.session_state.get("must_change_password", False)):
            st.warning("É obrigatório alterar a senha antes de continuar.")
            with st.form("force_change_password_form"):
                current = st.text_input("Senha atual", type="password")
                new_pass = st.text_input("Nova senha", type="password")
                confirm = st.text_input("Confirmar nova senha", type="password")
                submit = st.form_submit_button("Atualizar senha")
            if submit:
                user = _get_logged_user()
                if not user or not verify_password(current, str(user.get("password_hash", ""))):
                    st.error("Senha atual inválida.")
                    st.stop()
                if not new_pass or new_pass != confirm:
                    st.error("As senhas não conferem.")
                    st.stop()
                payload = dict(user)
                payload["password_hash"] = hash_password(new_pass)
                payload["must_change_password"] = 0
                if _upsert_user(payload):
                    st.session_state.must_change_password = False
                    st.success("Senha alterada.")
                    st.rerun()
                st.error("Falha ao atualizar senha.")
            st.stop()
        return True

    ensure_default_admin()
    st.title("Login")
    tab_login, tab_register, tab_change, tab_forgot = st.tabs(["Entrar", "Cadastrar-se", "Alterar senha", "Esqueci minha senha"])

    with tab_login:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            username_n = _normalize_username(username)
            if _rate_limited("login", username_n):
                st.error("Muitas tentativas. Tente novamente mais tarde.")
                st.stop()
            authenticated, auth_user = _authenticate_user(username_n, password)
            if not authenticated or not auth_user:
                _rate_limit_failure("login", username_n)
                st.error("Usuário ou senha inválidos.")
                st.stop()
            _rate_limit_success("login", username_n)
            try:
                _upgrade_password_if_needed(auth_user, password)
            except Exception:
                pass

            session = _create_session(auth_user)
            if not session:
                st.error("Não foi possível iniciar sessão.")
                st.stop()
            st.session_state.authenticated = True
            st.session_state.current_user = str(auth_user.get("username", username_n))
            st.session_state.current_user_id = _get_user_id(_get_user(st.session_state.current_user) or auth_user)
            st.session_state.session_id = session[0]
            st.session_state.session_token = session[1]
            st.session_state.must_change_password = bool(int(auth_user.get("must_change_password", 0) or 0))
            if st.session_state.must_change_password:
                st.warning("Troca de senha obrigatória no primeiro login.")
            st.success("Login realizado.")
            st.rerun()

    with tab_register:
        locked = _has_non_admin_user()
        if locked:
            st.warning("Cadastro bloqueado: já existe uma conta cadastrada.")
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
            username_n = _normalize_username(new_user)
            if not username_n or not new_pass:
                st.error("Preencha usuário e senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            elif not _normalize_cpf(cpf) or not pergunta.strip() or not resposta.strip():
                st.error("CPF, pergunta e resposta secreta são obrigatórios.")
            elif _get_user(username_n):
                st.error("Usuário já existe.")
            else:
                wrote = _upsert_user(
                    {
                        "username": username_n,
                        "password_hash": hash_password(new_pass),
                        "must_change_password": 0,
                        "cpf": _normalize_cpf(cpf),
                        "nome_completo": nome.strip(),
                        "data_nascimento": _safe_iso_date(nascimento),
                        "pergunta_secreta": pergunta.strip(),
                        "resposta_secreta_hash": legacy_hash_password(resposta),
                    }
                )
                if wrote:
                    st.success("Cadastro realizado. Faça login.")
                else:
                    st.error("Falha ao salvar cadastro.")

    with tab_change:
        username = st.text_input("Usuário", key="alt_user")
        current = st.text_input("Senha atual", type="password", key="alt_senha_atual")
        new_pass = st.text_input("Nova senha", type="password", key="alt_nova_senha")
        confirm = st.text_input("Confirmar nova senha", type="password", key="alt_confirmar")
        if st.button("Alterar senha"):
            authenticated, auth_user = _authenticate_user(username, current)
            if not authenticated or not auth_user:
                st.error("Usuário ou senha inválidos.")
            elif not new_pass:
                st.error("Informe a nova senha.")
            elif new_pass != confirm:
                st.error("As senhas não conferem.")
            else:
                payload = dict(auth_user)
                payload["password_hash"] = hash_password(new_pass)
                payload["must_change_password"] = 0
                wrote = _upsert_user(payload)
                if wrote:
                    st.session_state.must_change_password = False
                    st.success("Senha alterada.")
                else:
                    st.error("Falha ao atualizar senha.")

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
            key = f"{_normalize_cpf(cpf)}:{_normalize_username(pergunta)}"
            if _rate_limited("recovery", key):
                st.info("Se os dados estiverem corretos, a solicitação será processada em alguns minutos.")
                st.stop()
            # Always return neutral response.
            neutral = "Se os dados estiverem corretos, a senha foi redefinida."
            if not cpf.strip() or not pergunta.strip() or not resposta.strip() or not nova_senha or nova_senha != confirma:
                _rate_limit_failure("recovery", key)
                st.info(neutral)
                st.stop()
            user = _find_user_for_recovery(cpf, nascimento, pergunta, legacy_hash_password(resposta))
            if not user:
                _rate_limit_failure("recovery", key)
                st.info(neutral)
                st.stop()
            payload = dict(user)
            payload["password_hash"] = hash_password(nova_senha)
            payload["must_change_password"] = 0
            _upsert_user(payload)
            _rate_limit_success("recovery", key)
            st.info(neutral)

    st.stop()


def render_logout_button() -> None:
    with st.sidebar:
        if st.button("Sair"):
            _revoke_session(str(st.session_state.get("session_id", "")))
            st.session_state.authenticated = False
            st.session_state.current_user = ""
            st.session_state.current_user_id = None
            st.session_state.session_id = ""
            st.session_state.session_token = ""
            st.session_state.must_change_password = False
            st.rerun()


def get_logged_username() -> str:
    return str(st.session_state.get("current_user", "")).strip()


def get_logged_user_id() -> int | None:
    value = st.session_state.get("current_user_id")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None
