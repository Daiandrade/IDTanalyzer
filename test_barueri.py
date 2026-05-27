"""
Teste: Verificar se BARUERI agora e reconhecido
"""
from pathlib import Path
import idt_engine

print("="*70)
print("TESTE: Carregando base de aderencia...")
print("="*70)
print()

# Carregar base
base = idt_engine.load_adherence_base(Path("config/Aderencia.xlsm"))

municipios_dict = base["municipios"]

print(f"Total de municipios na base: {len(municipios_dict)}")
print()

# Testar BARUERI
print("-"*70)
print("TESTE: BARUERI - SP")
print("-"*70)
print()

lookup_key = ("barueri", "SP")
esta_coberto = lookup_key in municipios_dict

print(f"Chave de busca: {lookup_key}")
print(f"Resultado: {'COBERTO' if esta_coberto else 'NAO COBERTO'}")
print()

if esta_coberto:
    print("OK! BARUERI agora e reconhecido como coberto!")
else:
    print("ERRO! BARUERI ainda nao e reconhecido!")

print()
print("="*70)

# Mostrar alguns exemplos de SP
print()
print("Exemplos de municipios de SP cobertos (primeiros 10):")
print()

sp_municipios = [key for key in municipios_dict.keys() if key[1] == "SP"][:10]
for mun, uf in sp_municipios:
    print(f"  - {mun.title()} ({uf})")
