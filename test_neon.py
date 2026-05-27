import os
os.environ['DATABASE_URL'] = "postgresql://neondb_owner:npg_8MnjVKiGAyY7@ep-shiny-hill-ajbaiza1-pooler.c-3.us-east-2.aws.neon.tech/neondb?sslmode=require"

import db_manager

print("Testando conexao com Neon...")
db_manager.init_db()

info = db_manager.get_database_info()
print(f"Tipo: {info['type']}")
print(f"Conectado: {info['connected']}")
print(f"Registros atuais: {info['total_records']}")
