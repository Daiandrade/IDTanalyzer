"""
Debug: Verificar como BARUERI está sendo processado
"""
import pandas as pd
from pathlib import Path
import unicodedata

def normalize(s: str) -> str:
    """Mesma função usada no idt_engine.py"""
    s = str(s).lower().strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

# Carregar base de aderência
aderencia_path = Path("config/Aderencia.xlsm")

print("="*70)
print("DEBUG: Análise de Municípios - BARUERI - SP")
print("="*70)
print()

# Ler sheet de municípios
df_mun = pd.read_excel(aderencia_path, sheet_name="Cfg_Municipios_Cobertos", engine="openpyxl", header=0)

print(f"Total de linhas na base: {len(df_mun)}")
print(f"Colunas: {list(df_mun.columns)}")
print()

# Procurar por BARUERI
print("Procurando por BARUERI...")
print()

# Filtrar linhas que contenham "barueri"
barueri_rows = df_mun[df_mun.iloc[:, 2].astype(str).str.lower().str.contains("barueri", na=False)]

if len(barueri_rows) > 0:
    print(f"Encontrado {len(barueri_rows)} registro(s) de BARUERI:")
    print()

    for idx, row in barueri_rows.iterrows():
        uf = str(row.iloc[1]).strip().upper()
        mun_c = str(row.iloc[2]).strip()  # Nome com acentos
        mun_d = str(row.iloc[3]).strip() if len(row) > 3 else ""  # Nome normalizado
        aderencia = row.iloc[4] if len(row) > 4 else None

        mun_normalized = normalize(mun_c)

        print(f"  Linha {idx}:")
        print(f"    UF: {uf}")
        print(f"    Nome original (Coluna C): '{mun_c}'")
        print(f"    Nome normalizado (Coluna D): '{mun_d}'")
        print(f"    Aderencia (Coluna E): {aderencia}")
        print(f"    Normalizado pela função: '{mun_normalized}'")
        print(f"    Chave de lookup: ('{mun_normalized}', '{uf}')")
        print(f"    Status: {'✅ COBERTO' if aderencia == 1 else '❌ NÃO COBERTO'}")
        print()
else:
    print("❌ BARUERI NÃO encontrado na base!")
    print()

# Mostrar alguns exemplos de SP para comparação
print("-"*70)
print("Exemplos de municípios de SP na base (primeiros 10):")
print()

sp_rows = df_mun[df_mun.iloc[:, 1].astype(str).str.upper() == "SP"].head(10)
for idx, row in sp_rows.iterrows():
    mun_c = str(row.iloc[2]).strip()
    aderencia = row.iloc[4] if len(row) > 4 else None
    mun_normalized = normalize(mun_c)
    print(f"  '{mun_c}' -> '{mun_normalized}' (Aderencia={aderencia})")

print()
print("="*70)

# Simular o que acontece quando o cliente envia "BARUERI - SP"
print()
print("SIMULAÇÃO: Cliente enviou 'BARUERI' com UF 'SP'")
print()

cliente_cidade = "BARUERI"
cliente_uf = "SP"
cliente_normalized = normalize(cliente_cidade)

print(f"Nome do cliente: '{cliente_cidade}'")
print(f"Normalizado: '{cliente_normalized}'")
print(f"UF: '{cliente_uf}'")
print(f"Chave de busca: ('{cliente_normalized}', '{cliente_uf}')")
print()

# Verificar se encontra na base
barueri_na_base = df_mun[
    (df_mun.iloc[:, 1].astype(str).str.upper() == cliente_uf) &
    (df_mun.iloc[:, 2].astype(str).apply(normalize) == cliente_normalized)
]

if len(barueri_na_base) > 0:
    row = barueri_na_base.iloc[0]
    aderencia = row.iloc[4] if len(row) > 4 else None
    if aderencia == 1:
        print("✅ RESULTADO: Deveria ser encontrado como COBERTO")
    else:
        print("⚠️  RESULTADO: Encontrado mas com Aderencia != 1")
else:
    print("❌ RESULTADO: NÃO seria encontrado na base")
    print()
    print("Possíveis causas:")
    print("1. Nome está escrito diferente na base")
    print("2. Problema de normalização")
    print("3. Município não está cadastrado")
