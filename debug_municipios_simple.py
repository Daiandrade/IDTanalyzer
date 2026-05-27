"""
Debug simples: Verificar valores da coluna Aderencia
"""
import pandas as pd
from pathlib import Path

# Carregar base
df_mun = pd.read_excel("config/Aderencia.xlsm", sheet_name="Cfg_Municipios_Cobertos", engine="openpyxl", header=0)

print("="*70)
print("ANALISE DA COLUNA ADERENCIA")
print("="*70)
print()

# Verificar tipos de valores na coluna Aderencia
print("Coluna E (Aderencia) - Valores unicos:")
print()

valores_unicos = df_mun.iloc[:, 4].unique()
print(f"Total de valores unicos: {len(valores_unicos)}")
print()

for val in valores_unicos:
    count = (df_mun.iloc[:, 4] == val).sum()
    tipo = type(val).__name__
    print(f"  Valor: '{val}' (tipo: {tipo}) - Aparece {count} vezes")

print()
print("-"*70)
print("BARUERI:")
print()

# Verificar BARUERI especificamente
barueri = df_mun[df_mun.iloc[:, 2].astype(str).str.lower().str.contains("barueri", na=False)]
for _, row in barueri.iterrows():
    print(f"  Municipio: {row.iloc[2]}")
    print(f"  UF: {row.iloc[1]}")
    print(f"  Aderencia (valor): '{row.iloc[4]}'")
    print(f"  Aderencia (tipo): {type(row.iloc[4]).__name__}")
    print()

print("="*70)
print("PROBLEMA IDENTIFICADO:")
print()
print("A coluna Aderencia contem TEXTO, nao numeros!")
print("Valores: 'Atentido' (com typo), 'Nao Atendido', etc")
print()
print("O codigo atual verifica: if aderencia == 1")
print("Isso NUNCA sera True porque 'Atentido' != 1")
print()
print("SOLUCAO: Verificar se o texto contem 'atend' (normalizado)")
