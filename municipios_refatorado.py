"""
NOVA LOGICA DE MUNICIPIOS - COMPLETA E ROBUSTA

Estruturas:
- Cliente: Sheet com UF e Município
- Base: Coluna B=UF, C=Município (com acento), D=Município (sem acento), E=Status
"""
import pandas as pd
import unicodedata
import re
from pathlib import Path


def normalize_municipio(texto: str) -> str:
    """
    Normaliza nome de município de forma MUITO inteligente.

    Remove:
    - Acentos
    - Caracteres especiais
    - Espaços extras
    - Maiúsculas/minúsculas

    Exemplos:
    - "São Paulo" → "sao paulo"
    - "Mogi das Cruzes" → "mogi das cruzes"
    - "D'Ávila" → "davila"
    """
    if pd.isna(texto) or not texto:
        return ""

    # Converter para string
    texto = str(texto).strip()

    # Remover acentos (NFKD)
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")

    # Converter para minúsculas
    texto = texto.lower()

    # Remover caracteres especiais (manter apenas letras, números e espaços)
    texto = re.sub(r'[^a-z0-9\s]', '', texto)

    # Remover espaços extras
    texto = ' '.join(texto.split())

    return texto


def carregar_base_municipios(caminho_aderencia: str) -> dict:
    """
    Carrega base de municípios da planilha de aderência.

    Estrutura esperada:
    - Coluna B (índice 1): UF
    - Coluna C (índice 2): Município (com acento)
    - Coluna D (índice 3): Município (sem acento)
    - Coluna E (índice 4): Status ("Atendido"/"Não Atendido")

    Retorna: dict {(municipio_normalizado, UF): status_atendido}
    """
    print("Carregando base de aderência de municípios...")

    df = pd.read_excel(
        caminho_aderencia,
        sheet_name="Cfg_Municipios_Cobertos",
        engine="openpyxl",
        header=0
    )

    print(f"  Linhas na base: {len(df)}")

    # Dicionário: (municipio_normalizado, UF) → True/False (coberto ou não)
    base_municipios = {}

    VALID_UFS = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    }

    for idx, row in df.iterrows():
        # Coluna B = UF
        uf = str(row.iloc[1]).strip().upper() if pd.notna(row.iloc[1]) else ""

        # Coluna C = Município (com acento)
        mun_com_acento = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""

        # Coluna D = Município (sem acento) - pode estar vazio
        mun_sem_acento = str(row.iloc[3]).strip() if len(row) > 3 and pd.notna(row.iloc[3]) else ""

        # Coluna E = Status
        status = str(row.iloc[4]).strip().lower() if len(row) > 4 and pd.notna(row.iloc[4]) else ""

        # Validações
        if not uf or uf not in VALID_UFS:
            continue

        if not mun_com_acento or len(mun_com_acento) < 3:
            continue

        # Determinar se está coberto
        is_coberto = "atend" in status  # "atendido" ou "atentido"

        # Normalizar município
        mun_normalizado = normalize_municipio(mun_com_acento)

        if len(mun_normalizado) >= 3:
            base_municipios[(mun_normalizado, uf)] = is_coberto

        # Se existe Coluna D (sem acento) diferente, adicionar também
        if mun_sem_acento and mun_sem_acento != mun_com_acento:
            mun_d_normalizado = normalize_municipio(mun_sem_acento)
            if len(mun_d_normalizado) >= 3:
                base_municipios[(mun_d_normalizado, uf)] = is_coberto

    cobertos = sum(1 for v in base_municipios.values() if v)
    nao_cobertos = sum(1 for v in base_municipios.values() if not v)

    print(f"  Municípios únicos na base: {len(base_municipios)}")
    print(f"  Cobertos: {cobertos}")
    print(f"  Não cobertos: {nao_cobertos}")

    return base_municipios


def ler_municipios_cliente(caminho_arquivo: str) -> pd.DataFrame:
    """
    Lê municípios da planilha do cliente.

    Procura sheet com "municipio" ou "cidade" no nome.
    Procura colunas com UF e Município.

    Retorna: DataFrame com colunas ['UF', 'Municipio']
    """
    print()
    print("Lendo municípios do arquivo do cliente...")

    # Abrir arquivo
    xl = pd.ExcelFile(caminho_arquivo, engine="openpyxl")

    # Encontrar sheet de municípios
    municipios_sheet = None
    for sheet in xl.sheet_names:
        if 'municipio' in sheet.lower() or 'cidade' in sheet.lower():
            municipios_sheet = sheet
            break

    if not municipios_sheet:
        print("  ERRO: Sheet de municípios não encontrada!")
        return pd.DataFrame()

    print(f"  Sheet encontrada: '{municipios_sheet}'")

    # Ler sheet completa sem header
    df_raw = pd.read_excel(caminho_arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=None)

    print(f"  Total de linhas na sheet: {len(df_raw)}")

    # Procurar linha de header
    header_row = None
    for i in range(min(15, len(df_raw))):
        # Pegar todas as células da linha
        row_values = [str(v).lower() for v in df_raw.iloc[i].values if pd.notna(v)]
        row_text = ' '.join(row_values)

        # Verificar se tem indicadores de header
        has_uf = any(x in row_text for x in ['uf', 'estado', 'sigla'])
        has_mun = any(x in row_text for x in ['municipio', 'cidade', 'localidade'])

        if has_uf and has_mun:
            header_row = i
            print(f"  Header encontrado na linha {i}")
            break

    if header_row is None:
        print("  AVISO: Header não encontrado, usando linha 0")
        header_row = 0

    # Reler com header correto
    df = pd.read_excel(caminho_arquivo, sheet_name=municipios_sheet, engine="openpyxl", header=header_row)

    print(f"  Linhas após header: {len(df)}")
    print(f"  Colunas: {list(df.columns[:10])}")

    # Identificar colunas de UF e Município
    uf_col = None
    mun_col = None

    for col in df.columns:
        col_lower = str(col).lower()

        if not uf_col and any(x in col_lower for x in ['uf', 'estado', 'sigla']):
            uf_col = col

        if not mun_col and any(x in col_lower for x in ['municipio', 'cidade', 'localidade']):
            mun_col = col

    # Se não encontrou por nome, usar primeiras colunas
    if not uf_col and not mun_col:
        print("  AVISO: Colunas não identificadas por nome, usando posição")
        if len(df.columns) >= 2:
            uf_col = df.columns[0]
            mun_col = df.columns[1]

    if not uf_col or not mun_col:
        print(f"  ERRO: Não foi possível identificar colunas UF e Município")
        return pd.DataFrame()

    print(f"  Coluna UF: '{uf_col}'")
    print(f"  Coluna Município: '{mun_col}'")

    # Criar DataFrame limpo
    resultado = pd.DataFrame({
        'UF': df[uf_col],
        'Municipio': df[mun_col]
    })

    # Limpar dados
    resultado = resultado.dropna(subset=['UF', 'Municipio'])

    # Remover linhas que são headers duplicados ou placeholders
    PLACEHOLDERS = ['uf', 'estado', 'municipio', 'cidade', 'sigla', 'exemplo', 'placeholder']

    def is_placeholder(texto):
        texto_lower = str(texto).lower().strip()
        return any(ph in texto_lower for ph in PLACEHOLDERS) or len(texto_lower) < 3

    resultado = resultado[~resultado['Municipio'].apply(is_placeholder)]
    resultado = resultado[~resultado['UF'].apply(is_placeholder)]

    # Converter UF para maiúsculas
    resultado['UF'] = resultado['UF'].astype(str).str.upper().str.strip()

    # Limpar espaços em Município
    resultado['Municipio'] = resultado['Municipio'].astype(str).str.strip()

    print(f"  Municípios válidos lidos: {len(resultado)}")

    return resultado


def analisar_municipios(df_cliente: pd.DataFrame, base_municipios: dict) -> dict:
    """
    Analisa municípios do cliente contra a base de aderência.

    Retorna:
    {
        'total': int,
        'cobertos': [lista],
        'nao_cobertos': [lista],
        'score': float
    }
    """
    print()
    print("Analisando municípios...")

    if df_cliente.empty:
        return {
            'total': 0,
            'cobertos': [],
            'nao_cobertos': [],
            'score': 0.0
        }

    cobertos = []
    nao_cobertos = []

    for idx, row in df_cliente.iterrows():
        uf = str(row['UF']).strip().upper()
        municipio_original = str(row['Municipio']).strip()

        # Normalizar município
        municipio_norm = normalize_municipio(municipio_original)

        # Buscar na base
        chave = (municipio_norm, uf)

        if chave in base_municipios:
            # Encontrado na base
            is_coberto = base_municipios[chave]

            if is_coberto:
                cobertos.append(f"{municipio_original} ({uf})")
            else:
                nao_cobertos.append(f"{municipio_original} ({uf}) - NA BASE MAS NÃO ATENDIDO")
        else:
            # Não encontrado na base
            nao_cobertos.append(f"{municipio_original} ({uf}) - NÃO ESTÁ NA BASE")

    # Deduplificar
    cobertos = sorted(set(cobertos))
    nao_cobertos = sorted(set(nao_cobertos))

    total = len(cobertos) + len(nao_cobertos)
    score = (len(cobertos) / total * 100.0) if total > 0 else 0.0

    print(f"  Total analisado: {total}")
    print(f"  Cobertos: {len(cobertos)}")
    print(f"  Não cobertos: {len(nao_cobertos)}")
    print(f"  Score: {score:.2f}%")

    return {
        'total': total,
        'cobertos': cobertos,
        'nao_cobertos': nao_cobertos,
        'score': round(score, 2)
    }


# TESTE
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Uso: python municipios_refatorado.py <arquivo_cliente> <arquivo_aderencia>")
        sys.exit(1)

    arquivo_cliente = sys.argv[1]
    arquivo_aderencia = sys.argv[2]

    print("="*70)
    print("ANÁLISE DE MUNICÍPIOS - NOVA LÓGICA")
    print("="*70)
    print()

    # 1. Carregar base
    base = carregar_base_municipios(arquivo_aderencia)

    # 2. Ler cliente
    df_cliente = ler_municipios_cliente(arquivo_cliente)

    # 3. Analisar
    resultado = analisar_municipios(df_cliente, base)

    print()
    print("="*70)
    print("RESULTADO FINAL")
    print("="*70)
    print(f"Total de municípios: {resultado['total']}")
    print(f"Cobertos: {len(resultado['cobertos'])}")
    print(f"Não cobertos: {len(resultado['nao_cobertos'])}")
    print(f"Score de aderência: {resultado['score']}%")

    if resultado['cobertos']:
        print()
        print(f"Municípios COBERTOS ({len(resultado['cobertos'])}):")
        for mun in resultado['cobertos'][:20]:
            print(f"  ✅ {mun}")
        if len(resultado['cobertos']) > 20:
            print(f"  ... e mais {len(resultado['cobertos']) - 20}")

    if resultado['nao_cobertos']:
        print()
        print(f"Municípios NÃO COBERTOS ({len(resultado['nao_cobertos'])}):")
        for mun in resultado['nao_cobertos'][:20]:
            print(f"  ❌ {mun}")
        if len(resultado['nao_cobertos']) > 20:
            print(f"  ... e mais {len(resultado['nao_cobertos']) - 20}")
