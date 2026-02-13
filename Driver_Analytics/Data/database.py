import sqlite3

def criar_banco():
    conn = sqlite3.connect("driver_analytics.db")
    cursor = conn.cursor()

    # Tabela receitas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receitas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        valor REAL NOT NULL,
        km REAL NOT NULL,
        "tempo trabalhado" INTEGER NOT NULL,
        observacao TEXT
    )
    """)

    # Tabela despesas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS despesas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        observacao TEXT
    )
    """)

    # Tabela investimentos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        aporte REAL NOT NULL,
        "total aportado" REAL NOT NULL,
        rendimento REAL NOT NULL,
        "patrimonio total" REAL NOT NULL

    )
    """)

    conn.commit()
    conn.close()