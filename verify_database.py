"""Verificar status do banco de dados"""
import db_manager

print("="*70)
print("STATUS DO BANCO DE DADOS")
print("="*70)
print()

info = db_manager.get_database_info()

print(f"Tipo de Banco: {info['type']}")
print(f"URL: {info['url']}")
print(f"Status Conexao: {'OK' if info['connected'] else 'FALHOU'}")
print(f"Total de Registros: {info['total_records']}")
print()

if info['connected']:
    print("OK! Banco de dados funcionando corretamente!")
else:
    print("ERRO: Problema na conexao com o banco!")
