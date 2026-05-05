"""
Script de migração: SQLite local → PostgreSQL produção
Migra todo o histórico de análises do banco local para produção
"""
import sqlite3
import os
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text


def migrate_sqlite_to_postgres(sqlite_path: str, postgres_url: str):
    """
    Migra dados do SQLite para PostgreSQL

    Args:
        sqlite_path: Caminho do arquivo SQLite local
        postgres_url: URL de conexão PostgreSQL
    """

    print("=" * 70)
    print("🔄 MIGRAÇÃO: SQLite → PostgreSQL")
    print("=" * 70)
    print()

    # 1. Conectar ao SQLite
    print(f"📂 [1/5] Conectando ao SQLite: {sqlite_path}")

    if not Path(sqlite_path).exists():
        print(f"❌ Erro: Arquivo {sqlite_path} não encontrado!")
        return False

    sqlite_conn = sqlite3.connect(sqlite_path)

    # Contar registros
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM analyses")
    total_records = cursor.fetchone()[0]

    print(f"   ✅ Conectado! Total de registros: {total_records}")
    print()

    if total_records == 0:
        print("⚠️  Nenhum registro para migrar!")
        sqlite_conn.close()
        return True

    # 2. Ler todos os dados
    print(f"📊 [2/5] Lendo {total_records} registros do SQLite...")

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

    print(f"   ✅ Lidos {len(df)} registros")
    print(f"   📅 Período: {df['timestamp'].min()} até {df['timestamp'].max()}")
    print()

    # 3. Conectar ao PostgreSQL
    print(f"🐘 [3/5] Conectando ao PostgreSQL...")

    try:
        pg_engine = create_engine(postgres_url, pool_pre_ping=True)
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✅ Conectado! {version.split(',')[0]}")
    except Exception as e:
        print(f"   ❌ Erro ao conectar: {e}")
        return False

    print()

    # 4. Criar tabela no PostgreSQL (se não existir)
    print(f"🏗️  [4/5] Criando tabela no PostgreSQL...")

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

        # Criar índices
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_usuario ON analyses(usuario)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_timestamp ON analyses(timestamp DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cliente ON analyses(cliente_nome)"))
        except:
            pass

        conn.commit()

    print(f"   ✅ Tabela criada/verificada")
    print()

    # 5. Inserir dados
    print(f"💾 [5/5] Inserindo {len(df)} registros no PostgreSQL...")
    print(f"   (Isso pode demorar alguns minutos...)")
    print()

    try:
        # Inserir em lotes de 100 registros
        batch_size = 100
        total_batches = (len(df) + batch_size - 1) // batch_size

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            batch_num = (i // batch_size) + 1

            # Usar to_sql do pandas (mais eficiente)
            batch.to_sql('analyses', pg_engine, if_exists='append', index=False, method='multi')

            print(f"   ✅ Lote {batch_num}/{total_batches} inserido ({len(batch)} registros)")

        print()
        print("=" * 70)
        print(f"✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        print(f"📊 Total migrado: {len(df)} registros")
        print()

        # Verificar resultado
        with pg_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM analyses"))
            pg_count = result.fetchone()[0]
            print(f"🔍 Verificação: {pg_count} registros no PostgreSQL")

        return True

    except Exception as e:
        print()
        print(f"❌ ERRO durante migração: {e}")
        print()
        return False


def main():
    """Executa a migração"""

    print()
    print("🔄 Script de Migração - IDT Analyzer")
    print()

    # Caminho do SQLite local
    sqlite_path = "idt_history.db"

    # URL PostgreSQL
    # Você pode passar via variável de ambiente ou editar aqui
    postgres_url = os.getenv('DATABASE_URL')

    if not postgres_url:
        print("⚠️  Variável DATABASE_URL não encontrada!")
        print()
        print("Como usar:")
        print()
        print("Opção 1 - Variável de ambiente:")
        print('  set DATABASE_URL=postgresql://user:password@host:5432/database')
        print('  python migrate_to_postgres.py')
        print()
        print("Opção 2 - Direto no código:")
        print('  Edite este arquivo e coloque sua URL PostgreSQL na linha 180')
        print()

        # Descomente e edite a linha abaixo com sua URL PostgreSQL:
        # postgres_url = "postgresql://user:password@host:5432/database"

        if not postgres_url:
            sys.exit(1)

    # Confirmação
    print(f"📂 Origem:  {sqlite_path}")
    print(f"🐘 Destino: PostgreSQL (conexão configurada)")
    print()

    resposta = input("⚠️  Deseja continuar com a migração? (s/N): ")

    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("❌ Migração cancelada pelo usuário")
        sys.exit(0)

    print()

    # Executar migração
    success = migrate_sqlite_to_postgres(sqlite_path, postgres_url)

    if success:
        print()
        print("🎉 Tudo pronto! Agora você pode:")
        print("   1. Configurar DATABASE_URL nos secrets do Streamlit Cloud")
        print("   2. Substituir db_manager.py por db_manager_new.py")
        print("   3. Fazer deploy no Streamlit Cloud")
        print("   4. O histórico estará disponível em produção!")
        print()
        sys.exit(0)
    else:
        print()
        print("❌ Migração falhou. Verifique os erros acima.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
