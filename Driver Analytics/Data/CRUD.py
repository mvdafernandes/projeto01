import sqlite3
import pandas as pd

DB_NAME = "driver_analytics.db"


def _supabase_client():
    try:
        from Data.supabase_client import get_supabase
    except Exception:
        return None
    return get_supabase()


def _use_supabase():
    return _supabase_client() is not None


def _to_supabase_record(record):
    record = dict(record)
    if "tempo trabalhado" in record:
        record["tempo_trabalhado"] = record.pop("tempo trabalhado")
    if "total aportado" in record:
        record["total_aportado"] = record.pop("total aportado")
    if "patrimonio total" in record:
        record["patrimonio_total"] = record.pop("patrimonio total")
    return record


def _from_supabase_df(df):
    if df.empty:
        return df
    return df.rename(
        columns={
            "tempo_trabalhado": "tempo trabalhado",
            "total_aportado": "total aportado",
            "patrimonio_total": "patrimonio total",
        }
    )

# ------------------------
# CONEXÃO
# ------------------------

def conectar():
    return sqlite3.connect(DB_NAME)

# ------------------------
# RECEITAS
# ------------------------

def inserir_receita(data, valor, km, tempo_trabalhado, observacao=""):
    client = _supabase_client()
    if client:
        payload = _to_supabase_record(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        client.table("receitas").insert(payload).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO receitas (data, valor, km, "tempo trabalhado", observacao)
        VALUES (?, ?, ?, ?, ?)
    """, (data, valor, km, tempo_trabalhado, observacao))

    conn.commit()
    conn.close()


def listar_receitas():
    client = _supabase_client()
    if client:
        data = client.table("receitas").select("*").execute().data
        return _from_supabase_df(pd.DataFrame(data))

    conn = conectar()
    df = pd.read_sql("SELECT * FROM receitas", conn)
    conn.close()
    return df


def buscar_receita_por_id(id):
    client = _supabase_client()
    if client:
        data = client.table("receitas").select("*").eq("id", id).execute().data
        return _from_supabase_df(pd.DataFrame(data))

    conn = conectar()
    df = pd.read_sql("SELECT * FROM receitas WHERE id = ?", conn, params=(id,))
    conn.close()
    return df


def atualizar_receita(id, data, valor, km, tempo_trabalhado, observacao):
    client = _supabase_client()
    if client:
        payload = _to_supabase_record(
            {
                "data": data,
                "valor": valor,
                "km": km,
                "tempo trabalhado": tempo_trabalhado,
                "observacao": observacao,
            }
        )
        client.table("receitas").update(payload).eq("id", id).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE receitas
        SET data = ?, valor = ?, km = ?, "tempo trabalhado" = ?, observacao = ?
        WHERE id = ?
    """, (data, valor, km, tempo_trabalhado, observacao, id))

    conn.commit()
    conn.close()


def deletar_receita(id):
    client = _supabase_client()
    if client:
        client.table("receitas").delete().eq("id", id).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM receitas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

# ------------------------
# DESPESAS
# ------------------------

def inserir_despesa(data, categoria, valor, observacao=""):
    client = _supabase_client()
    if client:
        payload = {"data": data, "categoria": categoria, "valor": valor, "observacao": observacao}
        client.table("despesas").insert(payload).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO despesas (data, categoria, valor, observacao)
        VALUES (?, ?, ?, ?)
    """, (data, categoria, valor, observacao))

    conn.commit()
    conn.close()


def listar_despesas():
    client = _supabase_client()
    if client:
        data = client.table("despesas").select("*").execute().data
        return pd.DataFrame(data)

    conn = conectar()
    df = pd.read_sql("SELECT * FROM despesas", conn)
    conn.close()
    return df


def buscar_despesa_por_id(id):
    client = _supabase_client()
    if client:
        data = client.table("despesas").select("*").eq("id", id).execute().data
        return pd.DataFrame(data)

    conn = conectar()
    df = pd.read_sql("SELECT * FROM despesas WHERE id = ?", conn, params=(id,))
    conn.close()
    return df


def atualizar_despesa(id, data, categoria, valor, observacao):
    client = _supabase_client()
    if client:
        payload = {"data": data, "categoria": categoria, "valor": valor, "observacao": observacao}
        client.table("despesas").update(payload).eq("id", id).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE despesas
        SET data = ?, categoria = ?, valor = ?, observacao = ?
        WHERE id = ?
    """, (data, categoria, valor, observacao, id))

    conn.commit()
    conn.close()


def deletar_despesa(id):
    client = _supabase_client()
    if client:
        client.table("despesas").delete().eq("id", id).execute()
        return

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM despesas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

# ------------------------
# INVESTIMENTOS
# ------------------------

def inserir_investimento(data, aporte, total_aportado, rendimento, patrimonio_total):
    client = _supabase_client()
    if client:
        payload = _to_supabase_record(
            {
                "data": data,
                "aporte": aporte,
                "total aportado": total_aportado,
                "rendimento": rendimento,
                "patrimonio total": patrimonio_total,
            }
        )
        client.table("investimentos").insert(payload).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO investimentos (data, aporte, "total aportado", rendimento, "patrimonio total")
        VALUES (?, ?, ?, ?, ?)
    """, (data, aporte, total_aportado, rendimento, patrimonio_total))

    conn.commit()
    conn.close()


def listar_investimentos():
    client = _supabase_client()
    if client:
        data = client.table("investimentos").select("*").execute().data
        return _from_supabase_df(pd.DataFrame(data))

    conn = conectar()
    df = pd.read_sql("SELECT * FROM investimentos", conn)
    conn.close()
    return df


def buscar_investimento_por_id(id):
    client = _supabase_client()
    if client:
        data = client.table("investimentos").select("*").eq("id", id).execute().data
        return _from_supabase_df(pd.DataFrame(data))

    conn = conectar()
    df = pd.read_sql("SELECT * FROM investimentos WHERE id = ?", conn, params=(id,))
    conn.close()
    return df


def atualizar_investimento(id, data, aporte, total_aportado, rendimento, patrimonio_total):
    client = _supabase_client()
    if client:
        payload = _to_supabase_record(
            {
                "data": data,
                "aporte": aporte,
                "total aportado": total_aportado,
                "rendimento": rendimento,
                "patrimonio total": patrimonio_total,
            }
        )
        client.table("investimentos").update(payload).eq("id", id).execute()
        return

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE investimentos
        SET data = ?, aporte = ?, "total aportado" = ?, rendimento = ?, "patrimonio total" = ?
        WHERE id = ?
    """, (data, aporte, total_aportado, rendimento, patrimonio_total, id))

    conn.commit()
    conn.close()


def deletar_investimento(id):
    client = _supabase_client()
    if client:
        client.table("investimentos").delete().eq("id", id).execute()
        return

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM investimentos WHERE id = ?", (id,))
    conn.commit()
    conn.close()


def recalcular_total_aportado():
    client = _supabase_client()
    if client:
        data = (
            client.table("investimentos")
            .select("id,data,aporte")
            .order("data", desc=False)
            .order("id", desc=False)
            .execute()
            .data
        )
        df = pd.DataFrame(data)
        if df.empty:
            return
        df["aporte"] = pd.to_numeric(df["aporte"], errors="coerce").fillna(0.0)
        df["total_aportado"] = df["aporte"].cumsum()
        for _, row in df.iterrows():
            client.table("investimentos").update(
                {"total_aportado": float(row["total_aportado"])}
            ).eq("id", int(row["id"])).execute()
        return

    conn = conectar()
    df = pd.read_sql("SELECT id, data, aporte FROM investimentos ORDER BY data, id", conn)
    if df.empty:
        conn.close()
        return

    df["aporte"] = pd.to_numeric(df["aporte"], errors="coerce").fillna(0.0)
    df["total_aportado"] = df["aporte"].cumsum()

    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute(
            'UPDATE investimentos SET "total aportado" = ? WHERE id = ?',
            (float(row["total_aportado"]), int(row["id"])),
        )

    conn.commit()
    conn.close()

