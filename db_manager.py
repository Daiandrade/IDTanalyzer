"""
Database manager for IDT Analyzer - stores analysis history
Supports both SQLite (local dev) and PostgreSQL (production)
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd
from sqlalchemy import create_engine, text, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import streamlit as st


# Detecta ambiente: PostgreSQL (produção) ou SQLite (local)
def get_database_url():
    """Get database URL from environment or Streamlit secrets"""
    # Tenta pegar do Streamlit secrets (produção)
    try:
        if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
            return st.secrets['DATABASE_URL']
    except:
        pass

    # Tenta pegar de variável de ambiente
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url

    # Fallback: SQLite local
    db_path = Path("idt_history.db")
    return f"sqlite:///{db_path}"


# Database engine
def get_engine():
    """Get SQLAlchemy engine"""
    url = get_database_url()

    # PostgreSQL precisa de configurações extras
    if url.startswith('postgresql'):
        return create_engine(
            url,
            pool_pre_ping=True,  # Verifica conexão antes de usar
            pool_recycle=3600,   # Recicla conexões a cada hora
            echo=False
        )
    else:
        # SQLite
        return create_engine(url, echo=False)


# Global engine instance
engine = get_engine()
Base = declarative_base()
Session = sessionmaker(bind=engine)


def init_db():
    """Create database tables if they don't exist"""
    # SQL compatível com PostgreSQL e SQLite
    try:
        with engine.connect() as conn:
            # Main analyses table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario VARCHAR(100) NOT NULL,
                    cliente_nome TEXT,
                    cliente_segmento TEXT,
                    cliente_estados TEXT,

                    score_geral FLOAT,
                    score_ncm_compras FLOAT,
                    score_ncm_vendas FLOAT,
                    score_municipios FLOAT,
                    score_cfops FLOAT,

                    total_ncm_compras INTEGER,
                    total_ncm_vendas INTEGER,
                    total_municipios INTEGER,
                    total_cfops INTEGER,

                    gaps_compras INTEGER,
                    gaps_vendas INTEGER,
                    municipios_fora_escopo INTEGER,
                    cfops_nao_standard INTEGER,

                    resultado_json TEXT,

                    arquivo_prediag TEXT,
                    arquivo_aderencia TEXT
                )
            """))

            # Índices para PostgreSQL
            if get_database_url().startswith('postgresql'):
                try:
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_usuario ON analyses(usuario)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp DESC)
                    """))
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_cliente ON analyses(cliente_nome)
                    """))
                except:
                    pass  # Índices podem já existir

            conn.commit()
    except Exception as e:
        db_url = get_database_url()
        error_msg = f"""
        ❌ ERRO DE CONEXÃO COM BANCO DE DADOS

        Tipo de banco: {'PostgreSQL' if db_url.startswith('postgresql') else 'SQLite'}
        URL: {db_url[:50]}...

        Erro: {str(e)}

        Se estiver usando PostgreSQL, verifique:
        1. DATABASE_URL está configurado nos Secrets do Streamlit Cloud
        2. Senha está correta (case-sensitive!)
        3. Banco Supabase está ativo (não pausado)
        4. URL tem ?sslmode=require no final
        """
        import streamlit as st
        st.error(error_msg)
        raise


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

    general = result.get("general", {})
    ncm_c = result.get("ncm_compras", {})
    ncm_v = result.get("ncm_vendas", {})
    mun = result.get("municipios", {})
    cfops = result.get("cfops", {})

    cliente_nome = cliente_nome_custom if cliente_nome_custom else general.get("segmento", "")

    with engine.connect() as conn:
        # INSERT compatível com PostgreSQL e SQLite
        query = text("""
            INSERT INTO analyses (
                usuario, cliente_nome, cliente_segmento, cliente_estados,
                score_geral, score_ncm_compras, score_ncm_vendas,
                score_municipios, score_cfops,
                total_ncm_compras, total_ncm_vendas, total_municipios, total_cfops,
                gaps_compras, gaps_vendas, municipios_fora_escopo, cfops_nao_standard,
                resultado_json, arquivo_prediag, arquivo_aderencia
            ) VALUES (
                :usuario, :cliente_nome, :cliente_segmento, :cliente_estados,
                :score_geral, :score_ncm_compras, :score_ncm_vendas,
                :score_municipios, :score_cfops,
                :total_ncm_compras, :total_ncm_vendas, :total_municipios, :total_cfops,
                :gaps_compras, :gaps_vendas, :municipios_fora_escopo, :cfops_nao_standard,
                :resultado_json, :arquivo_prediag, :arquivo_aderencia
            )
        """)

        result_proxy = conn.execute(query, {
            "usuario": usuario,
            "cliente_nome": cliente_nome,
            "cliente_segmento": general.get("segmento", ""),
            "cliente_estados": general.get("estados", ""),
            "score_geral": result.get("overall_score"),
            "score_ncm_compras": ncm_c.get("score"),
            "score_ncm_vendas": ncm_v.get("score"),
            "score_municipios": mun.get("score"),
            "score_cfops": cfops.get("score"),
            "total_ncm_compras": ncm_c.get("total_pairs", 0),
            "total_ncm_vendas": ncm_v.get("total_pairs", 0),
            "total_municipios": mun.get("total", 0),
            "total_cfops": cfops.get("total_cfops", 0),
            "gaps_compras": len(ncm_c.get("gaps", [])),
            "gaps_vendas": len(ncm_v.get("gaps", [])),
            "municipios_fora_escopo": len(mun.get("out_of_scope", [])),
            "cfops_nao_standard": len(cfops.get("alertas", [])),
            "resultado_json": json.dumps(result, default=str, ensure_ascii=False),
            "arquivo_prediag": arquivo_prediag,
            "arquivo_aderencia": arquivo_aderencia
        })

        conn.commit()

        # Pegar último ID inserido
        last_id_query = text("SELECT MAX(id) FROM analyses")
        analysis_id = conn.execute(last_id_query).scalar()

        return analysis_id


def get_user_history(usuario: str, limit: int = 50) -> pd.DataFrame:
    """Get analysis history for a user"""
    init_db()

    # Use text() with proper parameter binding for SQLAlchemy
    from sqlalchemy import text

    query = text("""
        SELECT
            id, timestamp, cliente_nome, cliente_segmento,
            score_geral, score_ncm_compras, score_ncm_vendas,
            score_municipios, score_cfops,
            gaps_compras, gaps_vendas, cfops_nao_standard
        FROM analyses
        WHERE usuario = :usuario
        ORDER BY timestamp DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {"usuario": usuario, "limit": limit})
        rows = result.fetchall()
        columns = result.keys()

    df = pd.DataFrame(rows, columns=columns)

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


def get_all_history(limit: int = 100) -> pd.DataFrame:
    """Get all analysis history (admin view)"""
    init_db()

    # Use f-string for limit (safe, it's an integer)
    query = f"""
        SELECT
            id, timestamp, usuario, cliente_nome, cliente_segmento,
            score_geral, gaps_compras, gaps_vendas, cfops_nao_standard
        FROM analyses
        ORDER BY timestamp DESC
        LIMIT {limit}
    """

    df = pd.read_sql_query(query, engine)

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


def get_analysis_by_id(analysis_id: int) -> Optional[dict]:
    """Load full analysis result by ID with client name"""
    init_db()

    with engine.connect() as conn:
        query = text("""
            SELECT resultado_json, cliente_nome
            FROM analyses
            WHERE id = :id
        """)

        result = conn.execute(query, {"id": analysis_id}).fetchone()

        if result and result[0]:
            analysis_result = json.loads(result[0])
            analysis_result['_cliente_nome'] = result[1] if result[1] else None
            return analysis_result

    return None


def get_stats_by_user(usuario: str = None) -> dict:
    """Get statistics for a user, or all users if usuario is None"""
    init_db()

    with engine.connect() as conn:
        if usuario:
            query = text("""
                SELECT
                    COUNT(*) as total_analyses,
                    AVG(score_geral) as avg_score,
                    MIN(score_geral) as min_score,
                    MAX(score_geral) as max_score,
                    SUM(gaps_compras + gaps_vendas) as total_gaps,
                    SUM(cfops_nao_standard) as total_cfop_alerts
                FROM analyses
                WHERE usuario = :usuario
            """)
            result = conn.execute(query, {"usuario": usuario}).fetchone()
        else:
            query = text("""
                SELECT
                    COUNT(*) as total_analyses,
                    AVG(score_geral) as avg_score,
                    MIN(score_geral) as min_score,
                    MAX(score_geral) as max_score,
                    SUM(gaps_compras + gaps_vendas) as total_gaps,
                    SUM(cfops_nao_standard) as total_cfop_alerts
                FROM analyses
            """)
            result = conn.execute(query).fetchone()

        if result:
            return {
                "total_analyses": result[0] or 0,
                "avg_score": round(result[1], 1) if result[1] else None,
                "min_score": round(result[2], 1) if result[2] else None,
                "max_score": round(result[3], 1) if result[3] else None,
                "total_gaps": result[4] or 0,
                "total_cfop_alerts": result[5] or 0,
            }

    return {}


def delete_analysis(analysis_id: int, usuario: str) -> bool:
    """Delete an analysis (only if it belongs to the user)"""
    init_db()

    with engine.connect() as conn:
        query = text("""
            DELETE FROM analyses
            WHERE id = :id AND usuario = :usuario
        """)

        result = conn.execute(query, {"id": analysis_id, "usuario": usuario})
        conn.commit()

        return result.rowcount > 0


def delete_analysis_by_id(analysis_id: int) -> bool:
    """Delete a specific analysis by ID (admin only)"""
    init_db()

    with engine.connect() as conn:
        query = text("DELETE FROM analyses WHERE id = :id")
        result = conn.execute(query, {"id": analysis_id})
        conn.commit()

        return result.rowcount > 0


def delete_all_analyses(usuario: str = None) -> int:
    """
    Delete all analyses, optionally filtered by user
    Returns the number of deleted records
    """
    init_db()

    with engine.connect() as conn:
        if usuario:
            query = text("DELETE FROM analyses WHERE usuario = :usuario")
            result = conn.execute(query, {"usuario": usuario})
        else:
            query = text("DELETE FROM analyses")
            result = conn.execute(query)

        conn.commit()
        return result.rowcount


def get_database_info() -> dict:
    """Get information about current database connection"""
    url = get_database_url()

    if url.startswith('postgresql'):
        db_type = "PostgreSQL (Production)"
    elif url.startswith('sqlite'):
        db_type = "SQLite (Local Development)"
    else:
        db_type = "Unknown"

    # Teste de conexão
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM analyses"))
            total_records = result.scalar()
            connection_ok = True
    except Exception as e:
        total_records = 0
        connection_ok = False

    return {
        "type": db_type,
        "url": url.split('@')[-1] if '@' in url else url,  # Esconde senha
        "connected": connection_ok,
        "total_records": total_records
    }


if __name__ == "__main__":
    # Test the database
    print("Initializing database...")
    init_db()

    info = get_database_info()
    print(f"✅ Database initialized successfully")
    print(f"📁 Database type: {info['type']}")
    print(f"🔗 Connection: {'✅ OK' if info['connected'] else '❌ Failed'}")
    print(f"📊 Total records: {info['total_records']}")
