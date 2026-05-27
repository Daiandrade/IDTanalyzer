"""
Teste FINAL: Verificar se BARUERI e reconhecido com a correcao
"""
import sys
import importlib
from pathlib import Path

# Force reload do modulo para pegar as mudancas
if 'idt_engine' in sys.modules:
    importlib.reload(sys.modules['idt_engine'])

import idt_engine

print("="*70)
print("TESTE FINAL: BARUERI - SP")
print("="*70)
print()

# Carregar base
print("Carregando base de aderencia...")
base = idt_engine.load_adherence_base(Path("config/Aderencia.xlsm"))

municipios_dict = base["municipios"]

print(f"Total de municipios cobertos: {len(municipios_dict)}")
print()

# Testar BARUERI
lookup_key = ("barueri", "SP")
esta_coberto = lookup_key in municipios_dict

print(f"Testando: {lookup_key}")
print(f"Resultado: {'COBERTO' if esta_coberto else 'NAO COBERTO'}")
print()

if esta_coberto:
    print("SUCESSO! BARUERI agora e reconhecido como coberto!")
else:
    print("ERRO! BARUERI ainda nao e reconhecido.")
    print()
    print("Municipios de SP na base (primeiros 20):")
    sp_muns = sorted([k for k in municipios_dict.keys() if k[1] == "SP"])[:20]
    for mun, uf in sp_muns:
        print(f"  - {mun}")
