"""
Migração simplificada: SQLite -> PostgreSQL (Neon)
"""
import sqlite3
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

def migrate():
    sqlite_path = "idt_history.db"
    postgres_url = os.getenv('DATABASE_URL')

    print("="*70)
    print("MIGRACAO: SQLite -> PostgreSQL (Neon)")
    print("="*70)
    print()

    # 1. Conectar SQLite
    print(f"[1/5] Conectando ao SQLite: {sqlite_path}")
    if not Path(sqlite_path).exists():
        print(f"ERRO: Arquivo {sqlite_path} nao encontrado!")
        return False

    sqlite_conn = sqlite3.connect(sqlite_path)
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analyses")
    total_records = cursor.fetchone()[0]
    print(f"OK! Total de registros: {total_records}")
    print()

    if total_records == 0:
        print("Nenhum registro para migrar!")
        sqlite_conn.close()
        return True

    # 2. Ler dados
    print(f"[2/5] Lendo {total_records} registros...")
    query = """
        SELECT
            timestamp, usuario, cliente_nome, cliente_segmento, cliente_estados,
            score_geral, score_ncm_compras, score_ncm_vendas,
            score_municipios, score_cfops,
            total_ncm_compras, total_ncm_vendas, total_municipios, total_cfops,
            gaps_compras, gaps_vendas, municipios_fora_escopo, cfops_nao_standard,
            resultado_json, arquivo_prediag, arquivo_aderencia
        FROM analyses
        ORDER BY timestamp
    """

    df = pd.read_sql_query(query, sqlite_conn)
    sqlite_conn.close()
    print(f"OK! Lidos {len(df)} registros")
    print()

    # 3. Conectar PostgreSQL
    print(f"[3/5] Conectando ao PostgreSQL (Neon)...")
    try:
        pg_engine = create_engine(postgres_url, pool_pre_ping=True)
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"OK! {version.split(',')[0]}")
    except Exception as e:
        print(f"ERRO ao conectar: {e}")
        return False
    print()

    # 4. Criar tabela
    print(f"[4/5] Criando tabela no PostgreSQL...")
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS analyses (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
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
    """

    with pg_engine.connect() as conn:
        conn.execute(text(create_table_sql))
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_usuario ON analyses(usuario)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cliente ON analyses(cliente_nome)"))
        except:
            pass
        conn.commit()

    print(f"OK! Tabela criada")
    print()

    # 5. Inserir dados
    print(f"[5/5] Inserindo {len(df)} registros no PostgreSQL...")
    print(f"(Isso pode demorar alguns minutos...)")
    print()

    try:
        batch_size = 100
        total_batches = (len(df) + batch_size - 1) // batch_size

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            batch.to_sql('analyses', pg_engine, if_exists='append', index=False, method='multi')
            print(f"OK! Lote {batch_num}/{total_batches} inserido ({len(batch)} registros)")

        print()
        print("="*70)
        print(f"MIGRACAO CONCLUIDA COM SUCESSO!")
        print("="*70)
        print(f"Total migrado: {len(df)} registros")
        print()

        # Verificar
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM analyses"))
            pg_count = result.fetchone()[0]
            print(f"Verificacao: {pg_count} registros no PostgreSQL")

        return True

    except Exception as e:
        print()
        print(f"ERRO durante migracao: {e}")
        print()
        return False

if __name__ == "__main__":
    migrate()
