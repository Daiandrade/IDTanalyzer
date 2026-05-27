"""
DEBUG TOTAL - Mostra CADA PASSO da leitura de municipios
"""
import pandas as pd
import sys

print("="*80)
print("DEBUG TOTAL - LEITURA DE MUNICIPIOS")
print("="*80)
print()

# Solicitar arquivo
if len(sys.argv) > 1:
    arquivo = sys.argv[1]
else:
    print("Informe o caminho do arquivo Pre-Diagnostico:")
    arquivo = input("> ").strip().strip('"')

print(f"Arquivo: {arquivo}")
print()

# PASSO 1: Listar todas as sheets
print("-"*80)
print("PASSO 1: LISTAR SHEETS")
print("-"*80)

try:
    xl = pd.ExcelFile(arquivo, engine="openpyxl")
    sheets = xl.sheet_names

    print(f"Total de sheets: {len(sheets)}")
    for i, sheet in enumerate(sheets, 1):
        print(f"  {i}. {sheet}")
    print()
except Exception as e:
    print(f"ERRO ao abrir arquivo: {e}")
    sys.exit(1)

# PASSO 2: Identificar sheet de municipios
print("-"*80)
print("PASSO 2: IDENTIFICAR SHEET DE MUNICIPIOS")
print("-"*80)

municipios_sheet = None
for sheet in sheets:
    if 'municipio' in sheet.lower() or 'cidade' in sheet.lower():
        municipios_sheet = sheet
        print(f"Sheet encontrada: '{sheet}'")
        break

if not municipios_sheet:
    print("ERRO: Nenhuma sheet com 'municipio' ou 'cidade' no nome!")
    print()
    print("Por favor, informe o NOME EXATO da sheet de municipios:")
    municipios_sheet = input("> ").strip()

print()

# PASSO 3: Ler sheet SEM header
print("-"*80)
print("PASSO 3: LER SHEET SEM HEADER (RAW)")
print("-"*80)

df_raw = pd.read_excel(arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=None)

print(f"Dimensoes: {len(df_raw)} linhas x {len(df_raw.columns)} colunas")
print()

# Mostrar primeiras 20 linhas
print("Primeiras 20 linhas:")
print()
for i in range(min(20, len(df_raw))):
    if len(df_raw.columns) >= 2:
        col_a = str(df_raw.iloc[i, 0]) if pd.notna(df_raw.iloc[i, 0]) else "[VAZIO]"
        col_b = str(df_raw.iloc[i, 1]) if pd.notna(df_raw.iloc[i, 1]) else "[VAZIO]"
        print(f"  Linha {i:3d} | Col A: {col_a[:30]:30s} | Col B: {col_b[:40]:40s}")

print()

# PASSO 4: Identificar linha de header
print("-"*80)
print("PASSO 4: IDENTIFICAR LINHA DE HEADER")
print("-"*80)

print("Procurando linha que contenha 'UF' e 'Municipio'...")
print()

header_row = None
for i in range(min(20, len(df_raw))):
    row_values = [str(v).lower() for v in df_raw.iloc[i].values if pd.notna(v)]
    row_text = ' '.join(row_values)

    has_uf = any(x in row_text for x in ['uf', 'estado', 'sigla'])
    has_mun = any(x in row_text for x in ['municipio', 'cidade', 'localidade'])

    if has_uf or has_mun:
        print(f"  Linha {i}: {row_text[:80]}")
        if has_uf and has_mun:
            header_row = i
            print(f"  >>> HEADER ENCONTRADO NA LINHA {i} <<<")
            break

if header_row is None:
    print()
    print("HEADER NAO ENCONTRADO AUTOMATICAMENTE!")
    print("Qual linha contem o header (0, 1, 2, ...)? ")
    try:
        header_row = int(input("> ").strip())
    except:
        header_row = 0
        print(f"Usando linha {header_row} como fallback")

print()

# PASSO 5: Reler COM header
print("-"*80)
print("PASSO 5: RELER COM HEADER")
print("-"*80)

df = pd.read_excel(arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=header_row)

print(f"Linhas apos reler: {len(df)}")
print(f"Colunas: {list(df.columns)}")
print()

# PASSO 6: Identificar colunas UF e Municipio
print("-"*80)
print("PASSO 6: IDENTIFICAR COLUNAS")
print("-"*80)

uf_col = None
mun_col = None

print("Procurando coluna de UF...")
for col in df.columns:
    col_lower = str(col).lower()
    if any(x in col_lower for x in ['uf', 'estado', 'sigla']):
        uf_col = col
        print(f"  Coluna UF encontrada: '{col}'")
        break

print()
print("Procurando coluna de Municipio...")
for col in df.columns:
    col_lower = str(col).lower()
    if any(x in col_lower for x in ['municipio', 'cidade', 'localidade']):
        mun_col = col
        print(f"  Coluna Municipio encontrada: '{col}'")
        break

if not uf_col or not mun_col:
    print()
    print("NAO CONSEGUI IDENTIFICAR AUTOMATICAMENTE!")
    print(f"Colunas disponiveis: {list(df.columns)}")
    print()
    print("Informe o NOME ou NUMERO (0, 1, 2...) da coluna de UF:")
    uf_input = input("> ").strip()
    try:
        uf_col = df.columns[int(uf_input)]
    except:
        uf_col = uf_input

    print("Informe o NOME ou NUMERO da coluna de Municipio:")
    mun_input = input("> ").strip()
    try:
        mun_col = df.columns[int(mun_input)]
    except:
        mun_col = mun_input

print()
print(f"Usando:")
print(f"  Coluna UF: '{uf_col}'")
print(f"  Coluna Municipio: '{mun_col}'")
print()

# PASSO 7: Extrair dados
print("-"*80)
print("PASSO 7: EXTRAIR DADOS DAS COLUNAS")
print("-"*80)

resultado = pd.DataFrame({
    'UF': df[uf_col],
    'Municipio': df[mun_col]
})

print(f"Total de linhas extraidas: {len(resultado)}")
print()

# Mostrar primeiros 30
print("Primeiros 30 municipios extraidos:")
for idx, row in resultado.head(30).iterrows():
    print(f"  {row['Municipio']:40s} ({row['UF']})")

print()
print(f"... e mais {len(resultado) - 30} municipios" if len(resultado) > 30 else "")
print()

# PASSO 8: Contar valores vazios
print("-"*80)
print("PASSO 8: ANALISE DE VALORES VAZIOS")
print("-"*80)

vazios_uf = resultado['UF'].isna().sum()
vazios_mun = resultado['Municipio'].isna().sum()

print(f"UF vazias: {vazios_uf}")
print(f"Municipio vazio: {vazios_mun}")
print(f"Linhas validas (sem vazios): {len(resultado.dropna())}")
print()

# RESULTADO FINAL
print("="*80)
print("RESULTADO FINAL")
print("="*80)
print(f"Total de municipios lidos: {len(resultado)}")
print(f"Total sem vazios: {len(resultado.dropna())}")
print()
print("Se este numero NAO for 979, ha um problema na leitura!")
print()
