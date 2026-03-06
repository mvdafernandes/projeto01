"""Authentication and session management for Streamlit app."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import streamlit as st

from core.config import get_settings
from core.database import get_supabase_client
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


_AUTH_LAST_ERROR_KEY = "auth_last_error"


def _clear_auth_error() -> None:
    st.session_state.pop(_AUTH_LAST_ERROR_KEY, None)


def _format_supabase_error(exc: Exception) -> str:
    parts: list[str] = []
    for attr in ("message", "details", "hint", "code"):
        value = getattr(exc, attr, None)
        if value:
            parts.append(f"{attr}: {value}")
    if not parts:
        parts.append(str(exc))
    return " | ".join(parts)


def _set_auth_error(context: str, exc: Exception | None = None) -> None:
    detail = context
    if exc is not None:
        detail = f"{context} ({_format_supabase_error(exc)})"
    st.session_state[_AUTH_LAST_ERROR_KEY] = detail


def _get_auth_error() -> str:
    return str(st.session_state.get(_AUTH_LAST_ERROR_KEY, "")).strip()


def _check_remote_auth_schema() -> tuple[bool, str]:
    client = get_supabase_client()
    if not client:
        return False, "Autenticação exige Supabase remoto. Configure SUPABASE_URL/SUPABASE_KEY e APP_DB_MODE=remote."
    try:
        client.table("usuarios").select("id").limit(1).execute()
    except Exception as exc:
        return (
            False,
            "Tabela remota `public.usuarios` indisponível para autenticação. "
            f"Aplique as migrations SQL no Supabase. Detalhe: {_format_supabase_error(exc)}",
        )
    try:
        client.table("auth_sessions").select("session_id").limit(1).execute()
    except Exception as exc:
        return (
            False,
            "Tabela remota `public.auth_sessions` indisponível para sessões. "
            f"Aplique as migrations SQL no Supabase. Detalhe: {_format_supabase_error(exc)}",
        )
    return True, ""


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _supabase_get_user(username: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    if not client:
        _set_auth_error("Cliente Supabase indisponível para buscar usuário.")
        return None
    username_n = _normalize_username(username)
    try:
        data = client.table("usuarios").select("*").eq("username", username_n).limit(1).execute().data
    except Exception as exc:
        _set_auth_error("Falha ao consultar usuário no Supabase.", exc)
        return None
    if not data:
        return None
    _clear_auth_error()
    return dict(data[0])


def _get_user(username: str) -> dict[str, Any] | None:
    return _supabase_get_user(username)


def _upsert_user(payload: dict[str, Any]) -> bool:
    payload_n = dict(payload)
    payload_n["username"] = _normalize_username(payload_n.get("username", ""))
    payload_n["must_change_password"] = int(payload_n.get("must_change_password", 0) or 0)
    client = get_supabase_client()
    if not client:
        _set_auth_error("Cliente Supabase indisponível para salvar usuário.")
        return False
    try:
        client.table("usuarios").upsert(payload_n, on_conflict="username").execute()
        _clear_auth_error()
        return True
    except Exception as exc:
        _set_auth_error("Falha ao gravar usuário no Supabase.", exc)
        return False


def _get_logged_user() -> dict[str, Any] | None:
    username = _normalize_username(st.session_state.get("current_user", ""))
    if not username:
        return None
    return _get_user(username)


def _get_rate_limit(action: str, key: str) -> tuple[int, datetime | None]:
    store = st.session_state.get("auth_rate_limits_store", {})
    if not isinstance(store, dict):
        return 0, None
    row = store.get(f"{action}:{key}")
    if not isinstance(row, dict):
        return 0, None
    blocked_until = None
    if row.get("blocked_until"):
        try:
            blocked_until = datetime.fromisoformat(str(row.get("blocked_until")))
        except Exception:
            blocked_until = None
    return int(row.get("failures", 0) or 0), blocked_until


def _set_rate_limit(action: str, key: str, failures: int, blocked_until: datetime | None) -> None:
    store = st.session_state.get("auth_rate_limits_store", {})
    if not isinstance(store, dict):
        store = {}
    store[f"{action}:{key}"] = {
        "failures": int(failures),
        "blocked_until": blocked_until.isoformat() if blocked_until else None,
        "last_failure_at": _utc_now().isoformat(),
    }
    st.session_state["auth_rate_limits_store"] = store


def _rate_limited(action: str, key: str) -> bool:
    _, blocked_until = _get_rate_limit(action, key)
    return bool(blocked_until and blocked_until > _utc_now())


def _rate_limit_success(action: str, key: str) -> None:
    _set_rate_limit(action, key, 0, None)


def _rate_limit_failure(action: str, key: str, max_failures: int = 10, cooldown_minutes: int = 15) -> None:
    failures, _ = _get_rate_limit(action, key)
    failures += 1
    blocked_until = None
    if failures >= int(max_failures):
        blocked_until = _utc_now() + timedelta(minutes=int(cooldown_minutes))
    _set_rate_limit(action, key, failures, blocked_until)


def _authenticate_user(username: str, password: str) -> tuple[bool, dict[str, Any] | None]:
    username_n = _normalize_username(username)
    user = _supabase_get_user(username_n)
    if user and verify_password(password, str(user.get("password_hash", ""))):
        return True, user
    return False, None


def _get_user_id(user: dict[str, Any]) -> int | None:
    value = user.get("id")
    try:
        return int(value) if value is not None else None
    except Exception:
        return None


def _supabase_create_session(user_id: int, raw_token: str) -> tuple[str, str] | None:
    client = get_supabase_client()
    if not client:
        _set_auth_error("Cliente Supabase indisponível para criar sessão.")
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
        _clear_auth_error()
        return session_id, raw_token
    except Exception as exc:
        _set_auth_error("Falha ao criar sessão no Supabase.", exc)
        return None


def _create_session(user: dict[str, Any]) -> tuple[str, str] | None:
    user_id = _get_user_id(user)
    if user_id is None:
        return None
    raw_token = secrets.token_urlsafe(48)
    return _supabase_create_session(user_id, raw_token)


def _supabase_resolve_session(session_id: str, raw_token: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    if not client:
        _set_auth_error("Cliente Supabase indisponível para validar sessão.")
        return None
    try:
        rows = client.table("auth_sessions").select("*").eq("session_id", str(session_id)).limit(1).execute().data
    except Exception as exc:
        _set_auth_error("Falha ao consultar sessão no Supabase.", exc)
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
    except Exception as exc:
        _set_auth_error("Falha ao consultar usuário da sessão no Supabase.", exc)
        return None
    if not user_rows:
        return None
    _clear_auth_error()
    return {
        "user_id": user_id,
        "username": str(user_rows[0].get("username", "")),
        "last_seen_at": str(session.get("last_seen_at", "")),
    }


def _resolve_session(session_id: str, raw_token: str) -> dict[str, Any] | None:
    if not session_id or not raw_token:
        return None
    return _supabase_resolve_session(session_id, raw_token)


def _revoke_session(session_id: str) -> None:
    if not session_id:
        return
    client = get_supabase_client()
    if not client:
        return
    try:
        client.table("auth_sessions").update({"revoked_at": _utc_now().isoformat()}).eq("session_id", str(session_id)).execute()
    except Exception:
        pass


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
    if not client:
        return False
    try:
        rows = client.table("usuarios").select("id").neq("username", "admin").limit(1).execute().data
        return bool(rows)
    except Exception:
        return False


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
    if not client:
        _set_auth_error("Cliente Supabase indisponível para recuperação de senha.")
        return None
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
    except Exception as exc:
        _set_auth_error("Falha ao buscar usuário para recuperação de senha.", exc)
        return None
    _clear_auth_error()
    return None


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

    schema_ok, schema_msg = _check_remote_auth_schema()
    if not schema_ok:
        st.error(schema_msg)
        st.caption(
            "Execute as migrations em `sql/supabase_migration_2026_02_14.sql` e "
            "`sql/migrations/20260218_0900__security_sessions_user_ownership.sql`."
        )
        st.stop()

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
            _clear_auth_error()
            username_n = _normalize_username(username)
            if _rate_limited("login", username_n):
                st.error("Muitas tentativas. Tente novamente mais tarde.")
                st.stop()
            authenticated, auth_user = _authenticate_user(username_n, password)
            if not authenticated or not auth_user:
                _rate_limit_failure("login", username_n)
                st.error(_get_auth_error() or "Usuário ou senha inválidos.")
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
            _clear_auth_error()
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
                    st.error(_get_auth_error() or "Falha ao salvar cadastro.")

    with tab_change:
        username = st.text_input("Usuário", key="alt_user")
        current = st.text_input("Senha atual", type="password", key="alt_senha_atual")
        new_pass = st.text_input("Nova senha", type="password", key="alt_nova_senha")
        confirm = st.text_input("Confirmar nova senha", type="password", key="alt_confirmar")
        if st.button("Alterar senha"):
            _clear_auth_error()
            authenticated, auth_user = _authenticate_user(username, current)
            if not authenticated or not auth_user:
                st.error(_get_auth_error() or "Usuário ou senha inválidos.")
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
                    st.error(_get_auth_error() or "Falha ao atualizar senha.")

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
            _clear_auth_error()
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
