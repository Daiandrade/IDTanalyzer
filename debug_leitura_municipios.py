"""
Debug: Verificar por que so 73 municipios foram lidos de 979
"""
import pandas as pd
import sys

# Solicitar caminho do arquivo
if len(sys.argv) > 1:
    arquivo = sys.argv[1]
else:
    print("Por favor, informe o caminho do arquivo Pre-Diagnostico:")
    arquivo = input("> ").strip().strip('"')

print("="*70)
print("DEBUG: LEITURA DE MUNICIPIOS")
print("="*70)
print()
print(f"Arquivo: {arquivo}")
print()

# Abrir arquivo e listar sheets
xl = pd.ExcelFile(arquivo, engine="openpyxl")
all_sheets = xl.sheet_names

print(f"Sheets no arquivo ({len(all_sheets)}):")
for i, sheet in enumerate(all_sheets, 1):
    print(f"  {i}. {sheet}")
print()

# Encontrar sheet de municipios
municipios_sheet = None
for sheet in all_sheets:
    if 'municipio' in sheet.lower() or 'cidade' in sheet.lower():
        municipios_sheet = sheet
        break

if not municipios_sheet:
    print("ERRO: Nenhuma sheet com 'municipio' ou 'cidade' no nome!")
    sys.exit(1)

print(f"Sheet de municipios encontrada: '{municipios_sheet}'")
print()

# Ler sheet sem header
df_raw = pd.read_excel(arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=None)

print(f"Total de linhas na sheet: {len(df_raw)}")
print(f"Total de colunas: {len(df_raw.columns)}")
print()

# Mostrar primeiras 10 linhas
print("Primeiras 10 linhas da sheet:")
print(df_raw.head(10).to_string())
print()

# Procurar header
print("-"*70)
print("Procurando linha de header...")
print()

for i in range(min(10, len(df_raw))):
    print(f"Linha {i}:")
    if len(df_raw.columns) >= 2:
        col_a = str(df_raw.iloc[i, 0]) if pd.notna(df_raw.iloc[i, 0]) else "NaN"
        col_b = str(df_raw.iloc[i, 1]) if pd.notna(df_raw.iloc[i, 1]) else "NaN"
        print(f"  Col A: '{col_a}'")
        print(f"  Col B: '{col_b}'")
    print()

# Tentar ler com diferentes headers
print("-"*70)
print("Tentando ler com diferentes posicoes de header:")
print()

for header_row in [0, 1, 2]:
    try:
        df_test = pd.read_excel(arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=header_row)

        # Contar linhas nao vazias nas primeiras 2 colunas
        if len(df_test.columns) >= 2:
            linhas_validas = df_test.dropna(subset=[df_test.columns[0], df_test.columns[1]])

            print(f"Header na linha {header_row}:")
            print(f"  Total de linhas: {len(df_test)}")
            print(f"  Linhas validas (sem NaN): {len(linhas_validas)}")
            print(f"  Colunas: {list(df_test.columns[:5])}")
            print()
    except Exception as e:
        print(f"Header na linha {header_row}: ERRO - {e}")
        print()

print("="*70)
print()
print("DIAGNOSTICO:")
print()
print("1. Verifique qual linha tem o header correto (UF, Municipio)")
print("2. Conte quantas linhas tem dados validos apos o header")
print("3. Verifique se ha filtros removendo linhas validas")
