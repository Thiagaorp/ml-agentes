"""Banco local SQLite: snapshot dos anúncios, métricas e análises dos agentes."""
import json
import sqlite3
from datetime import date

import config


def conectar():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS anuncios (
            id TEXT PRIMARY KEY,
            titulo TEXT, preco REAL, status TEXT, permalink TEXT,
            categoria TEXT, tipo_anuncio TEXT, frete_gratis INTEGER,
            vendas_totais INTEGER, atualizado_em TEXT
        );
        CREATE TABLE IF NOT EXISTS metricas (
            anuncio_id TEXT, data TEXT,
            visitas_30d INTEGER, vendas_30d INTEGER, conversao REAL, saude REAL,
            PRIMARY KEY (anuncio_id, data)
        );
        CREATE TABLE IF NOT EXISTS analises (
            anuncio_id TEXT, data TEXT, agente TEXT, resultado TEXT,
            PRIMARY KEY (anuncio_id, data, agente)
        );
        CREATE TABLE IF NOT EXISTS posvenda (
            pedido_id TEXT PRIMARY KEY, data TEXT
        );
    """)
    return con


def posvenda_ja_enviado(con, pedido_id):
    return con.execute("SELECT 1 FROM posvenda WHERE pedido_id = ?",
                       (str(pedido_id),)).fetchone() is not None


def posvenda_marcar(con, pedido_id):
    con.execute("INSERT OR REPLACE INTO posvenda VALUES (?, date('now'))",
                (str(pedido_id),))
    con.commit()


def salvar_anuncio(con, a):
    frete = a.get("shipping", {}).get("free_shipping", False)
    con.execute(
        """INSERT OR REPLACE INTO anuncios
           VALUES (?,?,?,?,?,?,?,?,?,date('now'))""",
        (a["id"], a["title"], a["price"], a["status"], a.get("permalink", ""),
         a.get("category_id", ""), a.get("listing_type_id", ""),
         1 if frete else 0, a.get("sold_quantity", 0)),
    )


def salvar_metricas(con, anuncio_id, visitas, vendas, saude):
    conversao = round(vendas / visitas * 100, 2) if visitas else 0.0
    con.execute(
        "INSERT OR REPLACE INTO metricas VALUES (?,?,?,?,?,?)",
        (anuncio_id, date.today().isoformat(), visitas, vendas, conversao, saude),
    )


def salvar_analise(con, anuncio_id, agente, resultado):
    con.execute(
        "INSERT OR REPLACE INTO analises VALUES (?,?,?,?)",
        (anuncio_id, date.today().isoformat(), agente, json.dumps(resultado, ensure_ascii=False)),
    )


def painel(con):
    """Anúncios ativos + métricas mais recentes, prontos para análise."""
    rows = con.execute("""
        SELECT a.id, a.titulo, a.preco, a.status, a.permalink, a.frete_gratis,
               a.vendas_totais, m.visitas_30d, m.vendas_30d, m.conversao, m.saude
        FROM anuncios a
        LEFT JOIN metricas m ON m.anuncio_id = a.id
            AND m.data = (SELECT MAX(data) FROM metricas WHERE anuncio_id = a.id)
        ORDER BY m.visitas_30d DESC
    """).fetchall()
    return [dict(r) for r in rows]


def analises_de_hoje(con):
    rows = con.execute(
        "SELECT * FROM analises WHERE data = date('now')"
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["anuncio_id"], {})[r["agente"]] = json.loads(r["resultado"])
    return out
