"""
Debug detalhado: Simular exatamente o que o idt_engine faz
"""
import pandas as pd
import unicodedata
import sys

def normalize(s: str) -> str:
    s = str(s).lower().strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

# Solicitar caminho do arquivo
if len(sys.argv) > 1:
    arquivo = sys.argv[1]
else:
    print("Informe o caminho do arquivo Pre-Diagnostico:")
    arquivo = input("> ").strip().strip('"')

print("="*70)
print("DEBUG DETALHADO: PROCESSAMENTO DE MUNICIPIOS")
print("="*70)
print()

# Abrir arquivo
xl = pd.ExcelFile(arquivo, engine="openpyxl")
all_sheets = xl.sheet_names

# Encontrar sheet
municipios_sheet = None
for sheet in all_sheets:
    if 'municipio' in sheet.lower() or 'cidade' in sheet.lower():
        municipios_sheet = sheet
        break

if not municipios_sheet:
    print("ERRO: Sheet de municipios nao encontrada!")
    sys.exit(1)

print(f"Sheet: '{municipios_sheet}'")
print()

# Ler sem header
df_mun_raw = pd.read_excel(arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=None)

print(f"[PASSO 1] Total de linhas na sheet: {len(df_mun_raw)}")
print()

# Procurar header (logica do idt_engine)
header_row_mun = None
for i in range(min(10, len(df_mun_raw))):
    if len(df_mun_raw.columns) < 2:
        continue

    col_a = normalize(str(df_mun_raw.iloc[i, 0])) if pd.notna(df_mun_raw.iloc[i, 0]) else ""
    col_b = normalize(str(df_mun_raw.iloc[i, 1])) if pd.notna(df_mun_raw.iloc[i, 1]) else ""

    has_uf = ('uf' in col_a or 'estado' in col_a)
    has_mun = ('municipio' in col_b or 'cidade' in col_b)

    if has_uf and has_mun:
        header_row_mun = i
        print(f"[PASSO 2] Header encontrado na linha {i}")
        print(f"  Col A: '{col_a}'")
        print(f"  Col B: '{col_b}'")
        break

if header_row_mun is None:
    print("[PASSO 2] Header NAO encontrado! Usando linha 0 como fallback")
    header_row_mun = 0

print()

# Reler com header
df_mun = pd.read_excel(arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=header_row_mun)

print(f"[PASSO 3] Apos reler com header={header_row_mun}:")
print(f"  Total de linhas: {len(df_mun)}")
print(f"  Colunas: {len(df_mun.columns)}")
print()

# Criar DataFrame (logica do idt_engine)
mun_rows = pd.DataFrame({
    'UF': df_mun.iloc[:, 0],
    'Cidade': df_mun.iloc[:, 1]
})

print(f"[PASSO 4] Apos criar DataFrame com Col A e Col B:")
print(f"  Total de linhas: {len(mun_rows)}")
print()

# Remover linhas vazias
antes = len(mun_rows)
mun_rows = mun_rows.dropna(subset=['Cidade', 'UF'])
print(f"[PASSO 5] Apos remover linhas vazias (dropna):")
print(f"  Linhas antes: {antes}")
print(f"  Linhas depois: {len(mun_rows)}")
print(f"  Removidas: {antes - len(mun_rows)}")
print()

# Filtrar placeholders
antes = len(mun_rows)
mun_rows = mun_rows[~mun_rows["Cidade"].astype(str).str.lower().str.contains(
    "fora do escopo|placeholder|exemplo|municipio|cidade", na=False
)]
print(f"[PASSO 6] Apos filtrar placeholders:")
print(f"  Linhas antes: {antes}")
print(f"  Linhas depois: {len(mun_rows)}")
print(f"  Removidas: {antes - len(mun_rows)}")
print()

# Validar UFs
VALID_UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
            "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
            "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

antes = len(mun_rows)
mun_rows = mun_rows[mun_rows['UF'].astype(str).str.upper().isin(VALID_UFS)]
print(f"[PASSO 7] Apos validar UFs:")
print(f"  Linhas antes: {antes}")
print(f"  Linhas depois: {len(mun_rows)}")
print(f"  Removidas: {antes - len(mun_rows)}")
print()

print("="*70)
print(f"RESULTADO FINAL: {len(mun_rows)} municipios validos")
print("="*70)
print()

# Mostrar alguns exemplos
if len(mun_rows) > 0:
    print("Primeiros 20 municipios:")
    for idx, row in mun_rows.head(20).iterrows():
        print(f"  - {row['Cidade']} ({row['UF']})")
    print()

    print("Ultimos 20 municipios:")
    for idx, row in mun_rows.tail(20).iterrows():
        print(f"  - {row['Cidade']} ({row['UF']})")
    print()

    # Contar por UF
    print("Distribuicao por UF:")
    uf_counts = mun_rows['UF'].value_counts()
    for uf, count in uf_counts.head(10).items():
        print(f"  {uf}: {count} municipios")
