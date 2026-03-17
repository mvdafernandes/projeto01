"""Repository for backend-only usuarios settings."""

from __future__ import annotations

from repositories.base_repository import BaseRepository


class UsuariosRepository(BaseRepository):
    """Backend-only access to the current authenticated user row."""

    table_name = "usuarios"

    def buscar_usuario_atual(self) -> dict | None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        rows = (
            client.table(self.table_name)
            .select("*")
            .eq("id", int(user_id))
            .limit(1)
            .execute()
            .data
        )
        return dict(rows[0]) if rows else None

    def obter_daily_goal(self) -> float:
        user = self.buscar_usuario_atual() or {}
        try:
            return float(user.get("daily_goal", 300.0) or 300.0)
        except Exception:
            return 300.0

    def atualizar_daily_goal(self, daily_goal: float) -> None:
        client = self._supabase()
        user_id = self._require_user_id()
        if not client:
            raise RuntimeError("Supabase remoto indisponivel.")
        client.table(self.table_name).update({"daily_goal": float(daily_goal)}).eq("id", int(user_id)).execute()
