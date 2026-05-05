"""
Database manager for IDT Analyzer - stores analysis history
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd


DB_PATH = Path("idt_history.db")


def init_db():
    """Create database tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Main analyses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            usuario TEXT NOT NULL,
            cliente_nome TEXT,
            cliente_segmento TEXT,
            cliente_estados TEXT,

            -- Scores
            score_geral REAL,
            score_ncm_compras REAL,
            score_ncm_vendas REAL,
            score_municipios REAL,
            score_cfops REAL,

            -- Counts
            total_ncm_compras INTEGER,
            total_ncm_vendas INTEGER,
            total_municipios INTEGER,
            total_cfops INTEGER,

            -- Gaps/Alerts
            gaps_compras INTEGER,
            gaps_vendas INTEGER,
            municipios_fora_escopo INTEGER,
            cfops_nao_standard INTEGER,

            -- Full result JSON
            resultado_json TEXT,

            -- Files metadata
            arquivo_prediag TEXT,
            arquivo_aderencia TEXT
        )
    """)

    # Index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_usuario ON analyses(usuario)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cliente ON analyses(cliente_nome)
    """)

    conn.commit()
    conn.close()


def save_analysis(
    usuario: str,
    result: dict,
    arquivo_prediag: str,
    arquivo_aderencia: str,
    cliente_nome_custom: str = None
) -> int:
    """
    Save analysis result to database
    Returns: analysis ID
    """
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    general = result.get("general", {})
    ncm_c = result.get("ncm_compras", {})
    ncm_v = result.get("ncm_vendas", {})
    mun = result.get("municipios", {})
    cfops = result.get("cfops", {})

    # Usa nome customizado se fornecido, senão usa segmento do arquivo
    cliente_nome = cliente_nome_custom if cliente_nome_custom else general.get("segmento", "")

    cursor.execute("""
        INSERT INTO analyses (
            usuario, cliente_nome, cliente_segmento, cliente_estados,
            score_geral, score_ncm_compras, score_ncm_vendas,
            score_municipios, score_cfops,
            total_ncm_compras, total_ncm_vendas, total_municipios, total_cfops,
            gaps_compras, gaps_vendas, municipios_fora_escopo, cfops_nao_standard,
            resultado_json, arquivo_prediag, arquivo_aderencia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        usuario,
        cliente_nome,
        general.get("segmento", ""),
        general.get("estados", ""),
        result.get("overall_score"),
        ncm_c.get("score"),
        ncm_v.get("score"),
        mun.get("score"),
        cfops.get("score"),
        ncm_c.get("total_pairs", 0),
        ncm_v.get("total_pairs", 0),
        mun.get("total", 0),
        cfops.get("total_cfops", 0),
        len(ncm_c.get("gaps", [])),
        len(ncm_v.get("gaps", [])),
        len(mun.get("out_of_scope", [])),
        len(cfops.get("alertas", [])),
        json.dumps(result, default=str, ensure_ascii=False),
        arquivo_prediag,
        arquivo_aderencia
    ))

    analysis_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return analysis_id


def get_user_history(usuario: str, limit: int = 50) -> pd.DataFrame:
    """Get analysis history for a user"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            id, timestamp, cliente_nome, cliente_segmento,
            score_geral, score_ncm_compras, score_ncm_vendas,
            score_municipios, score_cfops,
            gaps_compras, gaps_vendas, cfops_nao_standard
        FROM analyses
        WHERE usuario = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(usuario, limit))
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


def get_all_history(limit: int = 100) -> pd.DataFrame:
    """Get all analysis history (admin view)"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            id, timestamp, usuario, cliente_nome, cliente_segmento,
            score_geral, gaps_compras, gaps_vendas, cfops_nao_standard
        FROM analyses
        ORDER BY timestamp DESC
        LIMIT ?
    """
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


def get_analysis_by_id(analysis_id: int) -> Optional[dict]:
    """Load full analysis result by ID with client name"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT resultado_json, cliente_nome
        FROM analyses
        WHERE id = ?
    """, (analysis_id,))

    row = cursor.fetchone()
    conn.close()

    if row and row[0]:
        result = json.loads(row[0])
        # Adiciona o nome do cliente ao result para uso no PDF
        result['_cliente_nome'] = row[1] if row[1] else None
        return result
    return None


def get_stats_by_user(usuario: str = None) -> dict:
    """Get statistics for a user, or all users if usuario is None"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if usuario:
        # Stats de um usuário específico
        cursor.execute("""
            SELECT
                COUNT(*) as total_analyses,
                AVG(score_geral) as avg_score,
                MIN(score_geral) as min_score,
                MAX(score_geral) as max_score,
                SUM(gaps_compras + gaps_vendas) as total_gaps,
                SUM(cfops_nao_standard) as total_cfop_alerts
            FROM analyses
            WHERE usuario = ?
        """, (usuario,))
    else:
        # Stats de todos os usuários (admin)
        cursor.execute("""
            SELECT
                COUNT(*) as total_analyses,
                AVG(score_geral) as avg_score,
                MIN(score_geral) as min_score,
                MAX(score_geral) as max_score,
                SUM(gaps_compras + gaps_vendas) as total_gaps,
                SUM(cfops_nao_standard) as total_cfop_alerts
            FROM analyses
        """)

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_analyses": row[0] or 0,
            "avg_score": round(row[1], 1) if row[1] else None,
            "min_score": round(row[2], 1) if row[2] else None,
            "max_score": round(row[3], 1) if row[3] else None,
            "total_gaps": row[4] or 0,
            "total_cfop_alerts": row[5] or 0,
        }
    return {}


def delete_analysis(analysis_id: int, usuario: str) -> bool:
    """Delete an analysis (only if it belongs to the user)"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM analyses
        WHERE id = ? AND usuario = ?
    """, (analysis_id, usuario))

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


def delete_analysis_by_id(analysis_id: int) -> bool:
    """Delete a specific analysis by ID (admin only)"""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))

    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


def delete_all_analyses(usuario: str = None) -> int:
    """
    Delete all analyses, optionally filtered by user
    Returns the number of deleted records
    """
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if usuario:
        cursor.execute("DELETE FROM analyses WHERE usuario = ?", (usuario,))
    else:
        cursor.execute("DELETE FROM analyses")

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted_count


if __name__ == "__main__":
    # Test the database
    print("Initializing database...")
    init_db()
    print("✅ Database initialized successfully")
    print(f"📁 Database location: {DB_PATH.absolute()}")
