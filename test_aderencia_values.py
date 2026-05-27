"""
Debug: Testar logica de aderencia diretamente
"""
import pandas as pd
import unicodedata

def normalize(s: str) -> str:
    s = str(s).lower().strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

# Carregar base
df_mun = pd.read_excel("config/Aderencia.xlsm", sheet_name="Cfg_Municipios_Cobertos", engine="openpyxl", header=0)

print("="*70)
print("TESTE DA LOGICA DE ADERENCIA")
print("="*70)
print()

# Testar com os valores reais
test_values = ["Atentido", "Nao Atendido", 1, 0, "Atendido"]

print("Testando logica para cada valor:")
print()

for val in test_values:
    aderencia_str = normalize(str(val))
    is_covered = (
        val == 1 or
        "atend" in aderencia_str
    )
    print(f"  Valor: '{val}' (tipo: {type(val).__name__})")
    print(f"  Normalizado: '{aderencia_str}'")
    print(f"  Resultado: {'COBERTO' if is_covered else 'NAO COBERTO'}")
    print()

print("-"*70)
print("BARUERI na base:")
print()

# Pegar linha do BARUERI
barueri_row = df_mun[df_mun.iloc[:, 2].astype(str).str.lower().str.contains("barueri", na=False)].iloc[0]

uf = str(barueri_row.iloc[1]).strip().upper()
mun_c = str(barueri_row.iloc[2]).strip()
aderencia_raw = barueri_row.iloc[4]

print(f"Municipio: {mun_c}")
print(f"UF: {uf}")
print(f"Aderencia (raw): '{aderencia_raw}' (tipo: {type(aderencia_raw).__name__})")
print()

# Aplicar a logica
aderencia_str = normalize(str(aderencia_raw))
is_covered = (
    aderencia_raw == 1 or
    "atend" in aderencia_str
)

print(f"Aderencia (normalizado): '{aderencia_str}'")
print(f"'atend' in aderencia_str: {'atend' in aderencia_str}")
print(f"aderencia_raw == 1: {aderencia_raw == 1}")
print(f"RESULTADO: {'COBERTO' if is_covered else 'NAO COBERTO'}")
print()

if is_covered:
    mun_normalized = normalize(mun_c)
    print(f"OK! Deveria ser adicionado com chave: ('{mun_normalized}', '{uf}')")
else:
    print("ERRO! Nao seria adicionado ao lookup!")
