"""
Teste completo: Verificar leitura de municipios e comparacao com base
"""
import sys
import importlib
from pathlib import Path
import pandas as pd

# Force reload
if 'idt_engine' in sys.modules:
    importlib.reload(sys.modules['idt_engine'])

import idt_engine

print("="*70)
print("TESTE COMPLETO: ANALISE DE MUNICIPIOS")
print("="*70)
print()

# 1. Testar leitura da base de aderencia
print("[1/3] Carregando base de aderencia...")
base = idt_engine.load_adherence_base(Path("config/Aderencia.xlsm"))
municipios_dict = base["municipios"]

print(f"Total de municipios cobertos na base: {len(municipios_dict)}")
print()

# Mostrar alguns exemplos de SP
sp_municipios = sorted([key for key in municipios_dict.keys() if key[1] == "SP"])
print(f"Municipios de SP na base (primeiros 10):")
for mun, uf in sp_municipios[:10]:
    print(f"  - {mun.title()} ({uf})")
print()

# 2. Testar com dados de exemplo do cliente
print("[2/3] Simulando dados do cliente...")
print()

# Simular um DataFrame como viria do cliente
client_data = pd.DataFrame({
    'UF': ['SP', 'SP', 'RJ', 'MG', 'SP'],
    'Cidade': ['BARUERI', 'São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Campinas']
})

print("Municipios do cliente (exemplo):")
print(client_data.to_string(index=False))
print()

# 3. Testar analise
print("[3/3] Analisando municipios...")
print()

result = idt_engine.analyse_municipios(client_data, municipios_dict)

print(f"Total de municipios analisados: {result['total']}")
print(f"Municipios cobertos: {result.get('covered', 0)}")
print(f"Municipios nao cobertos: {result.get('not_covered', 0)}")
print(f"Score: {result.get('score', 0)}%")
print()

if result.get('in_scope'):
    print("Municipios COBERTOS:")
    for mun in result['in_scope']:
        print(f"  - {mun}")
    print()

if result.get('out_of_scope'):
    print("Municipios NAO COBERTOS:")
    for mun in result['out_of_scope']:
        print(f"  - {mun}")
    print()

print("="*70)
print()

# Verificacoes especificas
print("VERIFICACOES ESPECIFICAS:")
print()

test_cases = [
    ('barueri', 'SP'),
    ('sao paulo', 'SP'),
    ('rio de janeiro', 'RJ'),
    ('belo horizonte', 'MG'),
    ('campinas', 'SP')
]

for mun, uf in test_cases:
    esta_na_base = (mun, uf) in municipios_dict
    print(f"  {mun.title()} ({uf}): {'COBERTO' if esta_na_base else 'NAO COBERTO'}")
