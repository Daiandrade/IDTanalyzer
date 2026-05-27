"""
IDT Adherence Engine
====================
Reads a pre-diagnosis Excel (client-filled) + Aderencia.xlsm (coverage base)
and produces a structured adherence report.

NCM cross-reference rules:
  - Purchases : UF = UF_Fornecedor (supplier state)
  - Sales      : UF = UF_Cliente   (customer/origin state)

Coverage score = % of NCM×UF combinations where cell value > 0 (1 for Pharma, 100 for Chemical)
Partial coverage ->consolidated score + list of UFs with gap
Municipalities   ->compare against 834-city list; flag out-of-scope ones
"""

import re
import unicodedata
import difflib
import pandas as pd
from pathlib import Path


# ── Global flags ──────────────────────────────────────────────────────────────
QUIET_MODE = False  # Set to True to suppress all debug/info messages

def debug_print(*args, **kwargs):
    """Print only if not in QUIET_MODE"""
    if not QUIET_MODE:
        print(*args, **kwargs)


# ── helpers ──────────────────────────────────────────────────────────────────

UF_COLS = [
    "SP","AC","AL","AM","AP","BA","CE","DF","ES","GO",
    "MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ",
    "RN","RO","RR","RS","SC","SE","TO"
]

SECTOR_MAP = {
    # keywords from "segmento" field ->(inbound_sheet, outbound_sheet)
    "quim":    ("Chemical - Inbound", "Chemical - Oubound"),
    "farm":    ("Pharma - Inbound",   "Pharma -  Outbound"),
    "agro":    ("AWR",                "AWR"),
    "agric":   ("AWR",                "AWR"),
    "consum":  ("CG&Freigth",         "CG&Freigth"),
    "varejo":  ("CG&Freigth",         "CG&Freigth"),
    "aliment": ("CG&Freigth",         "CG&Freigth"),
}
DEFAULT_SECTOR = ("Chemical - Inbound", "Chemical - Oubound")

# Sinônimos para detecção inteligente de sheets
SHEET_SYNONYMS = {
    # Compras / Purchases / Inbound
    "compras": ["purchases", "purchase", "entrada", "entradas", "inbound", "acquisitions"],
    "ncm": ["commodity", "product", "codigo", "código", "hs"],
    "lista": ["list", "listing", "relacao", "relação"],

    # Vendas / Sales / Outbound
    "vendas": ["sales", "sale", "saida", "saídas", "saidas", "outbound", "saída", "revenue"],

    # Municípios / Cities / ISS
    "municipios": ["municipio", "cidades", "cidade", "cities", "city", "localidades"],
    "servicos": ["serviços", "services", "service", "iss"],

    # Informações Gerais
    "informacoes": ["informações", "information", "info", "data", "dados"],
    "gerais": ["geral", "general", "master", "main", "principal"],
}


def normalize(s: str) -> str:
    s = str(s).lower().strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


# Caracteres de substituição (encoding corrompido: ô ->�, ã ->�, etc.)
_REPLACEMENT_CHARS = "�﻿\x00"

# Mapeamento heurístico para tentar recuperar caracteres corrompidos comuns
# em nomes de municípios brasileiros. Chave: padrão na string corrompida (lowercase, sem acentos)
# Valor: caractere de substituição para o "�"
_CORRUPTION_HINTS = {
    # São ->S�o
    "s�o ": "a",
    # não ->n�o
    "n�o ": "a",
    # Rondônia, Goiânia, Espírito ->letras intermediárias
}

# Stopwords curtas que costumam variar entre versões do mesmo município
# (ex.: "São Paulo do Sul" vs "Sao Paulo Sul"). Usado APENAS na chave secundária.
_CITY_STOPWORDS = {"de", "do", "da", "dos", "das", "e"}


def normalize_city(s: str) -> str:
    """
    Normalização robusta para nomes de municípios.

    Trata:
      - Acentos (NFKD)
      - Caractere de substituição U+FFFD (encoding corrompido) ->tratado como letra vazia
      - Pontuação (apóstrofos, hífens, pontos, vírgulas) ->vira espaço
      - Múltiplos espaços ->um espaço
      - Lowercase + strip

    Exemplos:
      "São Paulo"            ->"sao paulo"
      "S�o Paulo"            ->"so paulo"   (degradado, mas comparável via fuzzy)
      "Alta Floresta D'Oeste"→ "alta floresta d oeste"
      "Mogi-Mirim"           ->"mogi mirim"
      "Espírito Santo"       ->"espirito santo"
    """
    if s is None:
        return ""
    s = str(s).strip()
    if not s or s.lower() == "nan":
        return ""

    # Remove caracteres de controle/replacement ->vira espaço
    for ch in _REPLACEMENT_CHARS:
        s = s.replace(ch, " ")

    # Lowercase + remove acentos via NFKD
    s = unicodedata.normalize("NFKD", s.lower())
    s = s.encode("ascii", "ignore").decode("ascii")

    # Substitui qualquer pontuação por espaço (apóstrofos, hífens, pontos, etc.)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)

    # Colapsa múltiplos espaços
    s = re.sub(r"\s+", " ", s).strip()

    return s


def normalize_city_key(s: str) -> str:
    """
    Chave secundária mais agressiva: remove também stopwords ("de", "do", "da"...)
    e espaços, para casar variações como "São Paulo do Sul" vs "Sao Paulo Sul".

    Retorna string vazia se a entrada for inválida.
    """
    base = normalize_city(s)
    if not base:
        return ""
    tokens = [t for t in base.split() if t not in _CITY_STOPWORDS]
    return "".join(tokens)


def best_fuzzy_match(name: str, candidates: list, threshold: float = 0.88):
    """
    Encontra o melhor candidato similar a `name` dentro de `candidates`.

    Args:
        name: nome já normalizado (via normalize_city)
        candidates: lista de nomes já normalizados
        threshold: similaridade mínima (0.0 a 1.0) — 0.88 cobre erros de
                   digitação típicos sem causar falsos positivos.

    Returns:
        (matched_name, similarity) ou (None, 0.0) se nenhum bater.
    """
    if not name or not candidates:
        return None, 0.0

    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=threshold)
    if not matches:
        return None, 0.0

    similarity = difflib.SequenceMatcher(None, name, matches[0]).ratio()
    return matches[0], similarity


def expand_all_ufs(df: pd.DataFrame, uf_column: str) -> pd.DataFrame:
    """
    Expande linhas onde UF = 'Todas', 'Todos', 'All', etc. em 27 linhas (uma para cada UF).

    Args:
        df: DataFrame com dados
        uf_column: Nome da coluna que contém a UF

    Returns:
        DataFrame expandido
    """
    if df.empty or uf_column not in df.columns:
        return df

    # Identifica linhas com "todas UFs"
    all_ufs_keywords = ["todas", "todos", "all", "todo", "todas as ufs", "todos os estados", "all states"]

    def check_all_ufs(x):
        # Garante que x seja um valor escalar, não uma Series
        if isinstance(x, pd.Series):
            return False
        if pd.isna(x):
            return False
        return any(keyword in normalize(str(x)) for keyword in all_ufs_keywords)

    mask_all_ufs = df[uf_column].apply(check_all_ufs)

    if not mask_all_ufs.any():
        return df  # Nenhuma linha com "todas UFs"

    # Separa linhas normais e linhas com "todas UFs"
    df_normal = df[~mask_all_ufs].copy()
    df_all_ufs = df[mask_all_ufs].copy()

    # Expande cada linha "todas UFs" em 27 linhas (uma por UF)
    expanded_rows = []
    for _, row in df_all_ufs.iterrows():
        for uf in UF_COLS:
            new_row = row.copy()
            new_row[uf_column] = uf
            expanded_rows.append(new_row)

    if expanded_rows:
        df_expanded = pd.DataFrame(expanded_rows)
        df = pd.concat([df_normal, df_expanded], ignore_index=True)

    return df


def find_sheet_by_keywords(sheets: list, keywords: list, synonyms: dict = None, context: str = "") -> str:
    """
    Find sheet name that contains all keywords (case-insensitive).
    Returns first match or None.

    Args:
        sheets: Lista de nomes de sheets disponíveis
        keywords: Lista de keywords primárias obrigatórias
        synonyms: Dict {keyword: [sinônimos]} para busca alternativa
        context: Contexto para logging (ex: "NCM Compras")

    Example: find_sheet_by_keywords(['Lista NCM Compras - POR'], ['compras', 'ncm'])
    """
    # Tentativa 1: Keywords exatas
    for sheet in sheets:
        normalized = normalize(sheet)
        if all(normalize(kw) in normalized for kw in keywords):
            if context:
                debug_print(f"[OK] Sheet '{sheet}' encontrada para {context} (match exato: {keywords})")
            return sheet

    # Tentativa 2: Com sinônimos
    if synonyms:
        for sheet in sheets:
            normalized = normalize(sheet)
            # Verifica se pelo menos uma variação de cada keyword está presente
            matches_all = True
            for kw in keywords:
                kw_variations = [normalize(kw)] + [normalize(syn) for syn in synonyms.get(kw, [])]
                if not any(var in normalized for var in kw_variations):
                    matches_all = False
                    break

            if matches_all:
                if context:
                    debug_print(f"[OK] Sheet '{sheet}' encontrada para {context} (match com sinonimos)")
                return sheet

    if context:
        debug_print(f"[AVISO] Nenhuma sheet encontrada para {context}. Keywords tentadas: {keywords}")
        if synonyms:
            debug_print(f"   Sinonimos disponiveis: {list(synonyms.keys())}")
        debug_print(f"   Sheets disponiveis: {', '.join(sheets[:10])}{'...' if len(sheets) > 10 else ''}")
    return None


def pick_sector(segmento: str):
    seg = normalize(segmento)
    for key, sheets in SECTOR_MAP.items():
        if key in seg:
            return sheets
    return DEFAULT_SECTOR


def detect_column_types(df: pd.DataFrame, sample_size=100) -> dict:
    """
    Detecta o tipo de dado em cada coluna baseado no CONTEÚDO, não no nome.
    Retorna dict com {col_index: tipo} onde tipo pode ser: 'ncm', 'uf', 'cfop', 'municipio', 'descricao', etc.
    """
    VALID_UFS = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
                 "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
                 "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

    column_types = {}

    for col_idx in range(len(df.columns)):
        col = df.iloc[:sample_size, col_idx]
        col_clean = col.dropna().astype(str).str.strip()

        if len(col_clean) == 0:
            continue

        # Testa se é UF (>50% são códigos de UF válidos)
        uf_count = sum(1 for v in col_clean if v.upper() in VALID_UFS)
        if uf_count / len(col_clean) > 0.5:
            column_types[col_idx] = 'uf'
            continue

        # Testa se é NCM (>50% são números de 4-8 dígitos)
        ncm_count = sum(1 for v in col_clean if re.match(r'^\d{4,8}$', re.sub(r'[^\d]', '', v)))
        if ncm_count / len(col_clean) > 0.5:
            column_types[col_idx] = 'ncm'
            continue

        # Testa se é CFOP (>50% são números de 4 dígitos começando com 1-7)
        cfop_count = sum(1 for v in col_clean if re.match(r'^[1-7]\d{3}$', re.sub(r'[^\d]', '', v)))
        if cfop_count / len(col_clean) > 0.5:
            column_types[col_idx] = 'cfop'
            continue

        # Testa se é descrição (textos longos, >20 chars em média)
        avg_len = col_clean.str.len().mean()
        if avg_len > 20:
            column_types[col_idx] = 'descricao'
            continue

        # Testa se é município (palavras com letras, não muito longo)
        municipio_count = sum(1 for v in col_clean if 3 <= len(v) <= 50 and re.search(r'[a-zA-Z]', v))
        if municipio_count / len(col_clean) > 0.7:
            column_types[col_idx] = 'municipio'

    return column_types


def clean_ncm(v) -> str:
    """
    Normaliza NCM para formato padronizado (apenas dígitos).

    Aceita múltiplos formatos:
    - Com pontos: 3004.90.00 ->30049000
    - Sem pontos: 30049000 ->30049000
    - Com espaços: 3004 90 00 ->30049000
    - Com hífen: 3004-90-00 ->30049000
    - Com barra: 3004/90/00 ->30049000
    - Formato HS: 3004.90 ->300490

    Returns: NCM apenas com dígitos
    """
    s = str(v).strip()

    # Remove tudo que não seja dígito (pontos, espaços, hífens, barras, etc)
    s = re.sub(r"[^0-9]", "", s)

    # Remove zeros à esquerda (se houver)
    s = s.lstrip("0")

    # Se ficou vazio após remover zeros, retorna "0"
    if not s:
        return "0"

    return s


# ── loaders ──────────────────────────────────────────────────────────────────

def load_adherence_base(path: Path) -> dict:
    """
    Returns dict with keys:
      cst_coverage  : dict {tributo: {cst: bool}}
      municipios    : dict {(municipio_normalized, uf): True} - par Município+UF
      sector_sheets : dict {sheet_name: DataFrame(NCM × UF)}
      non_standard  : set of CFOPs flagged as non-standard
    """
    import time

    # Retry logic para lidar com arquivo temporariamente bloqueado
    max_retries = 3
    retry_delay = 1  # segundos

    for attempt in range(max_retries):
        try:
            xl = pd.ExcelFile(path, engine="openpyxl")
            break
        except PermissionError:
            if attempt < max_retries - 1:
                debug_print(f"[AVISO] Arquivo bloqueado, tentando novamente em {retry_delay}s... (tentativa {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                raise PermissionError(f"Não foi possível abrir o arquivo '{path}'. Verifique se está aberto no Excel ou em outro programa.")

    with xl:
        # ── CSTs ──
        df_cst = pd.read_excel(path, sheet_name="Cfg_CSTs", engine="openpyxl")
        # Renomeia apenas as primeiras 4 colunas (pode haver mais no Excel)
        new_cols = ["Tributo", "CST", "Descricao", "Atendido"] + list(df_cst.columns[4:])
        df_cst.columns = new_cols
        df_cst = df_cst.dropna(subset=["Tributo", "CST"])
        cst_coverage = {}
        for _, row in df_cst.iterrows():
            trib = str(row["Tributo"]).strip()
            cst  = str(row["CST"]).strip()
            ok   = str(row["Atendido"]).strip().lower() == "sim"
            cst_coverage.setdefault(trib, {})[cst] = ok

        # ── Municipalities ──
        # Estrutura: Coluna 0=Nome_Estado, 1=UF, 2=Nome_Municipio, 3=Nome_Normalizado, 4=Aderencia
        df_mun = pd.read_excel(path, sheet_name="Cfg_Municipios_Cobertos", engine="openpyxl", header=0)

        # Lista de UFs válidas
        VALID_UFS = {
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
            "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
            "RS", "RO", "RR", "SC", "SP", "SE", "TO"
        }

        # Criar índice de municípios cobertos com 3 níveis de busca:
        #   1. Match exato em chave primária  -> normalize_city(nome)
        #   2. Match em chave secundária (sem stopwords) -> normalize_city_key(nome)
        #   3. Fuzzy match (similaridade ≥ 0.88) por UF
        #
        # Estrutura:
        #   municipios = {
        #       "_primary": {(key_normalized, uf): display_name},
        #       "_secondary": {(key_compacted, uf): display_name},
        #       "_by_uf": {uf: [list of normalized names]},
        #       (legado) (key, uf): True   -> mantido para compatibilidade
        #   }
        municipios = {}
        index_primary = {}
        index_secondary = {}
        # Mapeia QUALQUER chave (primária ou secundária) ->chave canônica única
        # da linha da base, para evitar duplicatas quando a base tem 2 versões
        # do mesmo nome (ex.: col C corrompida + col D ASCII).
        index_primary_to_canonical = {}
        index_secondary_to_canonical = {}
        names_by_uf = {}

        for _, row in df_mun.iterrows():
            uf = str(row.iloc[1]).strip().upper()  # Coluna B (índice 1)
            mun_c = str(row.iloc[2]).strip()  # Coluna C (índice 2) - Nome com acentos (pode estar corrompido)
            mun_d = str(row.iloc[3]).strip()  # Coluna D (índice 3) - Nome ASCII (sem acentos)
            aderencia_raw = row.iloc[4] if len(row) > 4 else 0  # Coluna E (índice 4) - Aderencia

            # CRÍTICO: Apenas municípios com Aderencia cobertos
            # Aceita tanto número (1) quanto texto ("Atendido", "Atentido", etc)
            aderencia_str = normalize(str(aderencia_raw))
            is_covered = (
                aderencia_raw == 1 or  # Aceita número 1
                aderencia_str == "atendido" or  # Aceita "Atendido" (correto)
                aderencia_str == "atentido"  # Aceita "Atentido" (typo na base)
            )

            if not is_covered:
                continue

            # Validações rigorosas
            if not uf or uf.lower() == 'nan' or uf not in VALID_UFS:
                continue

            # Escolha do nome de exibição (display_name):
            #   - Se coluna C tem caracteres corrompidos (�), prefere coluna D
            #   - Caso contrário, usa coluna C (com acentos originais)
            c_corrupted = any(ch in mun_c for ch in _REPLACEMENT_CHARS)
            c_valid = mun_c and mun_c.lower() != 'nan'
            d_valid = mun_d and mun_d.lower() != 'nan'

            if c_valid and not c_corrupted:
                display_name = mun_c
            elif d_valid:
                display_name = mun_d
            elif c_valid:
                display_name = mun_c
            else:
                continue

            # Montamos chaves a partir de AMBAS coluna C e D para máxima cobertura
            sources = []
            if d_valid:
                sources.append(mun_d)  # prioridade: coluna D (ASCII limpo)
            if c_valid and mun_c != mun_d:
                sources.append(mun_c)

            # Chave canônica do município: priorizamos a chave primária da coluna D
            # (ASCII limpo, sem caracteres corrompidos). Se só temos coluna C, usamos ela.
            canonical_key = None
            for src in sources:
                kp = normalize_city(src)
                if len(kp) >= 3:
                    canonical_key = kp
                    break
            if canonical_key is None:
                continue

            added_for_uf = set()
            for src in sources:
                key_primary = normalize_city(src)
                if len(key_primary) < 3:
                    continue

                # Chave primária (com espaços, sem acentos/pontuação)
                index_primary.setdefault((key_primary, uf), display_name)
                # Mapeia QUALQUER variação primária ->chave canônica (única por linha)
                index_primary_to_canonical.setdefault((key_primary, uf), canonical_key)

                # Compatibilidade com código legado que faz `(key, uf) in municipios`
                municipios[(key_primary, uf)] = True

                # Chave secundária (sem stopwords e sem espaços)
                key_secondary = normalize_city_key(src)
                if len(key_secondary) >= 3:
                    index_secondary.setdefault((key_secondary, uf), display_name)
                    index_secondary_to_canonical.setdefault(
                        (key_secondary, uf), canonical_key
                    )

                # Lista por UF para fuzzy match
                if key_primary not in added_for_uf:
                    names_by_uf.setdefault(uf, []).append(key_primary)
                    added_for_uf.add(key_primary)

        # Anexa índices auxiliares ao dict municipios (sem quebrar API existente)
        municipios["_primary"] = index_primary
        municipios["_secondary"] = index_secondary
        municipios["_primary_to_canonical"] = index_primary_to_canonical
        municipios["_secondary_to_canonical"] = index_secondary_to_canonical
        municipios["_by_uf"] = names_by_uf

        # ── Non-standard operations ──
        df_ns = pd.read_excel(path, sheet_name="Cfg_Operacoes_NaoStandard", engine="openpyxl", header=1)
        # Renomeia apenas as primeiras 4 colunas (pode haver mais no Excel)
        new_cols_ns = ["CFOP", "Desc", "CFOP_DESC", "Status"] + list(df_ns.columns[4:])
        df_ns.columns = new_cols_ns
        non_standard = set(str(r["CFOP"]).strip() for _, r in df_ns.iterrows()
                           if "não atendida" in str(r.get("Status", "")).lower())

        # ── Aderencia por NCM (aba principal consolidada) ──
        sector_sheets = {}
        try:
            # Ler a aba principal "Aderencia por NCM" que contém TODOS os setores
            df_aderencia = pd.read_excel(path, sheet_name="Aderencia por NCM", engine="openpyxl", header=1)

            # Filtrar por segmento e criar sheets virtuais por setor
            if "Segmento" in df_aderencia.columns and "NCM" in df_aderencia.columns:
                # Pharma
                df_pharma = df_aderencia[df_aderencia["Segmento"].str.contains("pharma", case=False, na=False)].copy()
                if not df_pharma.empty:
                    df_pharma = df_pharma.rename(columns={"NCM": "COMMODITY_CODE"})
                    df_pharma = df_pharma[["COMMODITY_CODE"] + [c for c in UF_COLS if c in df_pharma.columns]].copy()
                    df_pharma["COMMODITY_CODE"] = df_pharma["COMMODITY_CODE"].apply(clean_ncm)
                    df_pharma = df_pharma[df_pharma["COMMODITY_CODE"].str.len() > 0].reset_index(drop=True)
                    sector_sheets["Pharma - Inbound"] = df_pharma
                    sector_sheets["Pharma -  Outbound"] = df_pharma  # Mesmo dados para in/out

                # Chemical
                df_chemical = df_aderencia[df_aderencia["Segmento"].str.contains("chemical", case=False, na=False)].copy()
                if not df_chemical.empty:
                    df_chemical = df_chemical.rename(columns={"NCM": "COMMODITY_CODE"})
                    df_chemical = df_chemical[["COMMODITY_CODE"] + [c for c in UF_COLS if c in df_chemical.columns]].copy()
                    df_chemical["COMMODITY_CODE"] = df_chemical["COMMODITY_CODE"].apply(clean_ncm)
                    df_chemical = df_chemical[df_chemical["COMMODITY_CODE"].str.len() > 0].reset_index(drop=True)
                    sector_sheets["Chemical - Inbound"] = df_chemical
                    sector_sheets["Chemical - Oubound"] = df_chemical  # Mesmo dados para in/out

                # AWR (Agro)
                df_awr = df_aderencia[df_aderencia["Segmento"].str.contains("awr", case=False, na=False)].copy()
                if not df_awr.empty:
                    df_awr = df_awr.rename(columns={"NCM": "COMMODITY_CODE"})
                    df_awr = df_awr[["COMMODITY_CODE"] + [c for c in UF_COLS if c in df_awr.columns]].copy()
                    df_awr["COMMODITY_CODE"] = df_awr["COMMODITY_CODE"].apply(clean_ncm)
                    df_awr = df_awr[df_awr["COMMODITY_CODE"].str.len() > 0].reset_index(drop=True)
                    sector_sheets["AWR"] = df_awr

                # CG&Freigth (Consumer Goods)
                df_cg = df_aderencia[df_aderencia["Segmento"].str.contains("cg|freight|consumer", case=False, na=False)].copy()
                if not df_cg.empty:
                    df_cg = df_cg.rename(columns={"NCM": "COMMODITY_CODE"})
                    df_cg = df_cg[["COMMODITY_CODE"] + [c for c in UF_COLS if c in df_cg.columns]].copy()
                    df_cg["COMMODITY_CODE"] = df_cg["COMMODITY_CODE"].apply(clean_ncm)
                    df_cg = df_cg[df_cg["COMMODITY_CODE"].str.len() > 0].reset_index(drop=True)
                    sector_sheets["CG&Freigth"] = df_cg

                # ── COMBINADO: Todas as sheets em uma única base ──
                # Combina TODOS os setores para análise multi-setor
                all_sectors = []
                for sector_df in [df_pharma, df_chemical, df_awr, df_cg]:
                    if not sector_df.empty:
                        all_sectors.append(sector_df)

                if all_sectors:
                    df_all = pd.concat(all_sectors, ignore_index=True)
                    # Remove duplicatas, mantendo o maior valor de cobertura por NCM×UF
                    # Para cada NCM, agrupa por UF e pega o máximo valor
                    df_all_grouped = df_all.groupby("COMMODITY_CODE", as_index=False).agg({
                        **{uf: 'max' for uf in UF_COLS if uf in df_all.columns}
                    })
                    sector_sheets["ALL_SECTORS"] = df_all_grouped
                    debug_print(f"[OK] Base consolidada criada com {len(df_all_grouped)} NCMs únicos de todos os setores")

        except Exception as e:
            debug_print(f"[ERRO] Não foi possível ler aba 'Aderencia por NCM': {e}")
            import traceback
            traceback.print_exc()
            # Fallback para método antigo se falhar
            pass

        # ── IPI/PIS/COFINS sheet ──
        df_ipc = pd.read_excel(path, sheet_name="IPI-PIS-COFINS Adherence", engine="openpyxl", header=0)
        df_ipc.columns = ["COMMODITY_CODE", "PIS", "COFINS", "IPI"] + list(df_ipc.columns[4:])
        df_ipc = df_ipc.dropna(subset=["COMMODITY_CODE"])
        df_ipc["COMMODITY_CODE"] = df_ipc["COMMODITY_CODE"].apply(clean_ncm)
        sector_sheets["IPI-PIS-COFINS"] = df_ipc

        return dict(
            cst_coverage=cst_coverage,
            municipios=municipios,
            sector_sheets=sector_sheets,
            non_standard=non_standard,
        )


def detect_sheet_content(df: pd.DataFrame) -> str:
    """
    Detecta o tipo de conteúdo de uma sheet baseado nas colunas.
    Retorna: 'info', 'ncm_compras', 'ncm_vendas', 'municipios', ou None
    """
    if df.empty:
        return None

    # Normaliza nomes de colunas para análise
    cols_normalized = [normalize(str(c)) for c in df.columns]
    cols_text = ' '.join(cols_normalized)

    # Detecta Informações Gerais
    if any(keyword in cols_text for keyword in ['empresas', 'segmento', 'atividade', 'volumetria']):
        return 'info'

    # Detecta Municípios
    if any(keyword in cols_text for keyword in ['municipio', 'cidade', 'cities', 'city']):
        if any(keyword in cols_text for keyword in ['servico', 'service', 'iss']):
            return 'municipios'

    # Detecta NCM Compras (UF Fornecedor)
    if 'ncm' in cols_text or 'codigo' in cols_text or 'commodity' in cols_text:
        if 'fornecedor' in cols_text or 'supplier' in cols_text or 'entrada' in cols_text:
            return 'ncm_compras'
        # Se tem NCM e UF Cliente/Destino ->Vendas
        if 'cliente' in cols_text or 'destino' in cols_text or 'saida' in cols_text:
            return 'ncm_vendas'
        # Se tem NCM mas não tem indicador claro, pode ser Compras (default)
        if 'uf' in cols_text:
            return 'ncm_compras'

    return None


VALID_UFS_SET = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
                 "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
                 "RS", "RO", "RR", "SC", "SP", "SE", "TO"}

# Mapeamento de nomes de estados (com/sem acento) para sigla UF
UF_NAME_TO_CODE = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM",
    "bahia": "BA", "ceara": "CE", "distrito federal": "DF", "espirito santo": "ES",
    "goias": "GO", "maranhao": "MA", "mato grosso": "MT", "mato grosso do sul": "MS",
    "minas gerais": "MG", "para": "PA", "paraiba": "PB", "parana": "PR",
    "pernambuco": "PE", "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondonia": "RO", "roraima": "RR", "santa catarina": "SC",
    "sao paulo": "SP", "sergipe": "SE", "tocantins": "TO",
}


def _normalize_uf(value) -> str:
    """
    Converte UF de qualquer formato para sigla de 2 letras.
    Aceita: 'SP', 'sp', 'São Paulo', 'são paulo', 'SAO PAULO', '35' (código IBGE), etc.
    Retorna '' se inválido.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return ""

    # Tentativa 1: já é sigla de 2 letras
    up = s.upper()
    if len(up) == 2 and up in VALID_UFS_SET:
        return up

    # Tentativa 2: nome do estado por extenso
    normalized = normalize(s)  # lowercase + sem acentos
    if normalized in UF_NAME_TO_CODE:
        return UF_NAME_TO_CODE[normalized]

    # Tentativa 3: extrair sigla de string composta tipo "SP - São Paulo" ou "São Paulo (SP)"
    # Pega tokens de 2 letras maiúsculas
    tokens_2letras = re.findall(r"\b([A-Z]{2})\b", s.upper())
    for t in tokens_2letras:
        if t in VALID_UFS_SET:
            return t

    return ""


def _detect_city_column(df: pd.DataFrame, max_cols: int = 8) -> tuple:
    """
    Detecta heuristicamente quais colunas contêm UF e Cidade no DataFrame.

    Estratégia (usa dados reais, não só o header):
      - UF: coluna onde a maioria dos valores tem 2 letras E é sigla brasileira válida,
            OU é nome de estado por extenso
      - Cidade: coluna OUTRA que UF onde a maioria dos valores são strings com 3+ chars,
                contendo letras (não puramente numérico)

    Returns:
        (uf_col_idx, cidade_col_idx) ou (None, None) se não conseguir detectar
    """
    if df.empty or len(df.columns) < 2:
        return None, None

    max_cols = min(max_cols, len(df.columns))
    sample_size = min(50, len(df))  # examina até 50 linhas para evitar overhead
    if sample_size == 0:
        return None, None

    sample = df.head(sample_size)

    # Score cada coluna como candidato a UF / Cidade
    scores_uf = []
    scores_cidade = []
    for j in range(max_cols):
        col = sample.iloc[:, j]
        valores_validos = 0
        uf_validos = 0
        cidade_validas = 0
        for v in col:
            if pd.isna(v):
                continue
            s = str(v).strip()
            if not s or s.lower() == "nan":
                continue
            valores_validos += 1
            if _normalize_uf(s):
                uf_validos += 1
            # Cidade: string com letras, 3+ chars, não puramente número
            if len(s) >= 3 and re.search(r"[A-Za-zÀ-ÿ]", s) and not s.isdigit():
                cidade_validas += 1

        score_uf = uf_validos / valores_validos if valores_validos else 0
        score_cidade = cidade_validas / valores_validos if valores_validos else 0
        scores_uf.append((j, score_uf, valores_validos))
        scores_cidade.append((j, score_cidade, valores_validos))

    # UF: coluna com maior score_uf (precisa ser >= 0.5 para confiar)
    scores_uf_sorted = sorted(scores_uf, key=lambda x: (-x[1], x[0]))
    uf_col = scores_uf_sorted[0][0] if scores_uf_sorted and scores_uf_sorted[0][1] >= 0.5 else None

    # Cidade: coluna OUTRA que UF, com maior score_cidade E onde valores
    # NÃO são predominantemente UFs (para evitar pegar a coluna UF como Cidade)
    cidade_col = None
    for j, score, n_vals in sorted(scores_cidade, key=lambda x: (-x[1], x[0])):
        if j == uf_col:
            continue
        # Pula colunas que são predominantemente UFs (já cobertas)
        score_uf_j = scores_uf[j][1] if j < len(scores_uf) else 0
        if score_uf_j > 0.5:
            continue
        if score >= 0.5 and n_vals >= 3:
            cidade_col = j
            break

    return uf_col, cidade_col


def _extract_municipios_from_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    """
    Extrai municípios de uma sheet com detecção heurística robusta.

    Estratégia:
      1. Lê a sheet inteira (header=None) para ver todo o conteúdo
      2. Tenta detectar o header buscando texto "UF"/"Cidade" nas primeiras 10 linhas
      3. Se não acha header, detecta colunas por CONTEÚDO (cols com 2-letras válidas
         = UF, cols com strings longas = Cidade)
      4. Aceita UF como sigla OU nome por extenso (converte para sigla)
      5. Reporta diagnóstico passo-a-passo
    """
    df_mun_raw = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", header=None)
    total_excel_rows = len(df_mun_raw)
    debug_print(f"[DEBUG Municípios] Sheet '{sheet_name}' tem {total_excel_rows} linhas totais (incluindo header)")

    if total_excel_rows < 2 or len(df_mun_raw.columns) < 2:
        debug_print(f"[ERRO] Sheet '{sheet_name}' muito pequena ou sem colunas suficientes")
        return pd.DataFrame()

    # ── Etapa 1: detectar header por texto ──
    header_row = None
    uf_col_idx = None
    cidade_col_idx = None
    max_cols_check = min(8, len(df_mun_raw.columns))

    for i in range(min(15, total_excel_rows)):
        found_uf = None
        found_cidade = None
        for j in range(max_cols_check):
            val = normalize(str(df_mun_raw.iloc[i, j])) if pd.notna(df_mun_raw.iloc[i, j]) else ""
            if found_uf is None and (val in ("uf", "estado") or "sigla" in val):
                found_uf = j
            if found_cidade is None and ("municipio" in val or "cidade" in val or "city" in val or "localidade" in val):
                found_cidade = j

        if found_uf is not None and found_cidade is not None:
            header_row = i
            uf_col_idx = found_uf
            cidade_col_idx = found_cidade
            debug_print(
                f"[OK] Header detectado na linha {i}: "
                f"UF=coluna {chr(65+found_uf)}, Cidade=coluna {chr(65+found_cidade)}"
            )
            break

    # ── Etapa 2: se header não foi encontrado, detectar por CONTEÚDO ──
    if header_row is None:
        debug_print("[INFO] Header por texto não encontrado. Tentando detecção por conteúdo (heurística)...")
        # Tenta diferentes linhas iniciais de dados (0, 1, 2)
        for skip in range(0, 5):
            df_test = df_mun_raw.iloc[skip:].reset_index(drop=True)
            uf_j, cid_j = _detect_city_column(df_test, max_cols=max_cols_check)
            if uf_j is not None and cid_j is not None:
                header_row = skip - 1 if skip > 0 else None
                uf_col_idx = uf_j
                cidade_col_idx = cid_j
                debug_print(
                    f"[OK] Detecção heurística: dados começam na linha {skip}, "
                    f"UF=coluna {chr(65+uf_j)}, Cidade=coluna {chr(65+cid_j)}"
                )
                break

    if uf_col_idx is None or cidade_col_idx is None:
        debug_print(f"[ERRO] Não foi possível detectar colunas UF/Cidade em '{sheet_name}'")
        # Último recurso: usar A e B
        uf_col_idx = 0
        cidade_col_idx = 1
        header_row = 0

    # ── Etapa 3: relê o DataFrame com header correto ──
    if header_row is not None:
        df_mun = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", header=header_row)
    else:
        # Sem header — usa os dados direto
        df_mun = df_mun_raw.copy()

    debug_print(f"[DEBUG Municípios] Após releitura: {len(df_mun)} linhas de dados")

    if len(df_mun.columns) <= max(uf_col_idx, cidade_col_idx):
        debug_print(f"[ERRO] Sheet não tem colunas suficientes (esperado {max(uf_col_idx, cidade_col_idx)+1})")
        return pd.DataFrame()

    # ── Etapa 4: extrai UF e Cidade ──
    mun_rows = pd.DataFrame({
        'UF_raw': df_mun.iloc[:, uf_col_idx],
        'Cidade': df_mun.iloc[:, cidade_col_idx]
    })

    total_extraido = len(mun_rows)

    # Normaliza UF (aceita sigla OU nome por extenso)
    mun_rows['UF'] = mun_rows['UF_raw'].apply(_normalize_uf)
    mun_rows = mun_rows.drop(columns=['UF_raw'])

    # Remove linhas vazias (qualquer coluna ausente)
    antes_dropna = len(mun_rows)
    mun_rows = mun_rows[
        mun_rows['Cidade'].notna() &
        (mun_rows['Cidade'].astype(str).str.strip() != "") &
        (mun_rows['Cidade'].astype(str).str.lower() != "nan") &
        (mun_rows['UF'] != "")
    ]
    apos_dropna = len(mun_rows)

    # Remove placeholders/headers
    _placeholders_exatos = {
        "cidade", "estado", "municipio", "município", "uf", "sigla",
        "nome do municipio", "nome do município",
        "fora do escopo", "placeholder", "exemplo", "n/a", "na", "-",
    }
    mask_placeholder = mun_rows["Cidade"].astype(str).str.strip().str.lower().isin(_placeholders_exatos)
    placeholders_removidos = int(mask_placeholder.sum())
    mun_rows = mun_rows[~mask_placeholder]
    apos_placeholder = len(mun_rows)

    debug_print(
        f"[DEBUG Municípios] {total_extraido} extraidas -> "
        f"{apos_dropna} apos remover vazias (perdeu {total_extraido-apos_dropna}) -> "
        f"{apos_placeholder} apos remover placeholders (perdeu {placeholders_removidos})"
    )

    # Amostra das primeiras linhas para conferência visual
    if len(mun_rows) > 0:
        amostra = mun_rows.head(3).to_dict('records')
        debug_print(f"[DEBUG Municípios] Amostra dos dados extraidos: {amostra}")

    # Validação: se restou muito pouco, alerta (mas NÃO descarta — pode ser legítimo)
    if len(mun_rows) < 3:
        debug_print(f"[AVISO] Sheet '{sheet_name}' resultou em apenas {len(mun_rows)} linhas válidas")
        if len(mun_rows) == 0:
            return pd.DataFrame()

    debug_print(f"[OK] Municípios extraidos: {len(mun_rows)} linhas válidas")
    return mun_rows[['UF', 'Cidade']]


def load_prediag(path: Path) -> dict:
    """
    Parses the client-filled pre-diagnosis Excel.
    DETECÇÃO AUTOMÁTICA: Identifica sheets baseado no CONTEÚDO, não no nome.
    Returns dict with all relevant fields.
    """
    # Get all sheet names for intelligent matching
    with pd.ExcelFile(path, engine="openpyxl") as xl:
        all_sheets = xl.sheet_names

    debug_print(f"[DEBUG] Total de sheets encontradas: {len(all_sheets)}")
    debug_print(f"[DEBUG] Sheets: {', '.join(all_sheets)}")

    # Detectar conteúdo de cada sheet
    detected_sheets = {
        'info': None,
        'ncm_compras': None,
        'ncm_vendas': None,
        'municipios': None
    }

    # Para debug: armazenar todas as detecções tentadas
    detection_log = []
    columns_info = {}  # Armazena informações sobre colunas de cada sheet

    for sheet_name in all_sheets:
        try:
            # Ler primeiras linhas para detectar conteúdo
            df_sample = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", nrows=5, header=None)

            # Tentar detectar header em diferentes linhas
            detected_as = None
            header_found_at = None
            for header_row in range(min(5, len(df_sample))):
                df_test = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", header=header_row, nrows=10)
                content_type = detect_sheet_content(df_test)

                if content_type and not detected_sheets[content_type]:
                    detected_sheets[content_type] = sheet_name
                    detected_as = content_type
                    header_found_at = header_row
                    # Armazenar colunas para debug
                    columns_info[sheet_name] = {
                        'type': content_type,
                        'header_row': header_row,
                        'columns': list(df_test.columns)[:10]  # Primeiras 10 colunas
                    }
                    debug_print(f"[OK] Sheet '{sheet_name}' detectada como: {content_type}")
                    break

            if not detected_as:
                detection_log.append(f"'{sheet_name}': não detectada")
            else:
                detection_log.append(f"'{sheet_name}': {detected_as}")

        except Exception as e:
            debug_print(f"[AVISO] Erro ao ler sheet '{sheet_name}': {e}")
            detection_log.append(f"'{sheet_name}': ERRO - {str(e)[:50]}")
            continue

    debug_print(f"[DEBUG] Detecções: {'; '.join(detection_log)}")

    # ── General info ──
    info_sheet = detected_sheets['info']
    if not info_sheet:
        # Fallback: tentar encontrar por nome
        info_sheet = (
            find_sheet_by_keywords(all_sheets, ["informacoes", "gerais"], SHEET_SYNONYMS, "Informações Gerais") or
            find_sheet_by_keywords(all_sheets, ["informacoes"], SHEET_SYNONYMS, "Informações") or
            find_sheet_by_keywords(all_sheets, ["general", "information"], SHEET_SYNONYMS, "General Information") or
            all_sheets[0] if all_sheets else None
        )

    if not info_sheet:
        debug_print("[ERRO] Nenhuma sheet de informações gerais encontrada!")
        general = {}
    else:
        df_g = pd.read_excel(path, sheet_name=info_sheet, engine="openpyxl", header=None)
        def extract_answer(keyword):
            for _, row in df_g.iterrows():
                q = normalize(str(row.iloc[0]))
                if keyword in q:
                    for cell in row.iloc[1:]:
                        if pd.notna(cell) and str(cell).strip():
                            return str(cell).strip()
            return ""

        general = {
            "empresas":      extract_answer("quantas empresas"),
            "estados":       extract_answer("quais estados a empresa"),
            "segmento":      extract_answer("segmento"),
            "atividade":     extract_answer("atividade economica"),
            "escopo":        extract_answer("processos de negocio"),
            "prod_servico":  extract_answer("produtos e/ou servicos"),
            "vol_saida":     extract_answer("volumetria anual de documentos fiscais de saida"),
            "vol_entrada":   extract_answer("volumetria anual de documentos fiscais de entrada"),
        }

    # ── NCM Compras (Purchases) ──
    compras_sheet = detected_sheets['ncm_compras']

    # Se a sheet detectada não tem "NCM" ou "Compra" no nome, tentar fallback por nome
    if compras_sheet and not any(kw in compras_sheet.lower() for kw in ["ncm", "compra", "purchase", "inbound"]):
        debug_print(f"[AVISO] Sheet detectada '{compras_sheet}' não tem nome relevante para NCM Compras, tentando fallback...")
        compras_sheet = None

    if not compras_sheet:
        # Fallback: tentar encontrar por nome
        compras_sheet = (
            find_sheet_by_keywords(all_sheets, ["ncm", "compras"], SHEET_SYNONYMS, "NCM Compras") or
            find_sheet_by_keywords(all_sheets, ["ncm", "compra"], SHEET_SYNONYMS, "NCM Compra") or
            find_sheet_by_keywords(all_sheets, ["compras", "lista"], SHEET_SYNONYMS, "Lista Compras") or
            find_sheet_by_keywords(all_sheets, ["purchase", "ncm"], SHEET_SYNONYMS, "NCM Purchase") or
            find_sheet_by_keywords(all_sheets, ["inbound", "ncm"], SHEET_SYNONYMS, "NCM Inbound")
        )

    if not compras_sheet:
        debug_print("[AVISO] Sheet de NCM Compras não encontrada!")
        ncm_compras = pd.DataFrame()
    else:
        debug_print(f"[DEBUG] Processando sheet de Compras: '{compras_sheet}'")

        # ABORDAGEM: Ler sheet inteira sem header, procurar linha de header por nome de coluna
        df_nc_raw = pd.read_excel(path, sheet_name=compras_sheet, engine="openpyxl", header=None)

        header_row = None
        # Procura linha que contém "Código NCM" ou "NCM" como coluna (não título)
        for i in range(min(10, len(df_nc_raw))):
            row_text = ' '.join([normalize(str(v)) for v in df_nc_raw.iloc[i].values if pd.notna(v)])
            # Verifica se tem NCM E pelo menos mais 2 palavras-chave de colunas
            has_ncm = 'codigo ncm' in row_text or (row_text.strip().split() and 'ncm' in [normalize(w) for w in row_text.split()])
            column_keywords = ['tipo', 'descricao', 'produto', 'cest', 'cfop', 'st', 'cst', 'beneficio']
            keyword_count = sum(1 for kw in column_keywords if kw in row_text)
            if has_ncm and keyword_count >= 2:
                header_row = i
                debug_print(f"[OK] Header de Compras encontrado na linha {i}")
                break

        if header_row is not None:
            # Ler novamente com o header correto
            df_nc = pd.read_excel(path, sheet_name=compras_sheet, engine="openpyxl", header=header_row)

            # Mapear colunas por nome
            col_map = {}
            for c in df_nc.columns:
                nc = normalize(str(c))
                if "uf fornecedor" in nc:
                    col_map[c] = "UF_Fornecedor"
                elif "uf filial" in nc and "UF_Fornecedor" not in col_map.values():
                    col_map[c] = "UF_Fornecedor"
                elif "uf cliente" in nc and "UF_Fornecedor" not in col_map.values():
                    col_map[c] = "UF_Fornecedor"
                elif "codigo ncm" in nc or nc.strip() == "codigo ncm" or nc.strip() == "ncm":
                    col_map[c] = "NCM"
                elif "descricao" in nc or "descri" in nc:
                    col_map[c] = "Descricao"
                elif "beneficio" in nc:
                    col_map[c] = "Beneficio"
                elif "possui st" in nc:
                    col_map[c] = "PossuiST"
                elif "cfop" in nc:
                    col_map[c] = "CFOP"

            df_nc = df_nc.rename(columns=col_map)

            # Verifica se tem coluna NCM
            if "NCM" not in df_nc.columns:
                debug_print(f"[ERRO] Coluna NCM não encontrada após renomear")
                ncm_compras = pd.DataFrame()
            else:
                # Verifica se tem coluna UF
                has_uf = "UF_Fornecedor" in df_nc.columns

                if not has_uf:
                    # Sem UF: criar coluna UF_Fornecedor com "TODAS" para expandir depois
                    debug_print(f"[INFO] Coluna UF não encontrada em Compras - expandindo para todas as UFs")
                    df_nc["UF_Fornecedor"] = "TODAS"

                # Expande linhas com "Todas UFs" em 27 linhas (uma por UF)
                if "UF_Fornecedor" in df_nc.columns:
                    df_nc = expand_all_ufs(df_nc, "UF_Fornecedor")

                df_nc = df_nc.dropna(subset=["NCM"])
                df_nc = df_nc.reset_index(drop=True).copy()

                # Limpa NCM
                ncm_col = df_nc["NCM"]
                if isinstance(ncm_col, pd.DataFrame):
                    ncm_col = ncm_col.iloc[:, 0]

                df_nc["NCM"] = ncm_col.apply(clean_ncm).astype(str).values

                # Filtra NCMs válidos (>= 4 caracteres)
                valid_indices = [i for i, ncm in enumerate(df_nc["NCM"].values) if len(str(ncm)) >= 4]
                ncm_compras = df_nc.iloc[valid_indices].reset_index(drop=True)
                debug_print(f"[OK] NCM Compras carregado: {len(ncm_compras)} linhas" + (" (expandido para todas UFs)" if not has_uf else ""))
        else:
            debug_print(f"[ERRO] Header não encontrado na sheet de Compras '{compras_sheet}'")
            debug_print(f"[DEBUG] Primeiras 5 linhas da sheet:")
            try:
                df_nc_debug = pd.read_excel(path, sheet_name=compras_sheet, engine="openpyxl", header=None, nrows=5)
                debug_print(df_nc_debug.head().to_string())
            except Exception as e:
                debug_print(f"[DEBUG] Erro ao ler sheet: {e}")
            ncm_compras = pd.DataFrame()

    # ── NCM Vendas (Sales) ──
    vendas_sheet = detected_sheets['ncm_vendas']

    # Se a sheet detectada não tem "NCM" ou "Venda" no nome, tentar fallback por nome
    if vendas_sheet and not any(kw in vendas_sheet.lower() for kw in ["ncm", "venda", "sales", "outbound"]):
        debug_print(f"[AVISO] Sheet detectada '{vendas_sheet}' não tem nome relevante para NCM Vendas, tentando fallback...")
        vendas_sheet = None

    if not vendas_sheet:
        # Fallback: tentar encontrar por nome
        vendas_sheet = (
            find_sheet_by_keywords(all_sheets, ["ncm", "vendas"], SHEET_SYNONYMS, "NCM Vendas") or
            find_sheet_by_keywords(all_sheets, ["ncm", "venda"], SHEET_SYNONYMS, "NCM Venda") or
            find_sheet_by_keywords(all_sheets, ["vendas", "lista"], SHEET_SYNONYMS, "Lista Vendas") or
            find_sheet_by_keywords(all_sheets, ["sales", "ncm"], SHEET_SYNONYMS, "NCM Sales") or
            find_sheet_by_keywords(all_sheets, ["outbound", "ncm"], SHEET_SYNONYMS, "NCM Outbound")
        )

    if not vendas_sheet:
        debug_print("[AVISO] Sheet de NCM Vendas não encontrada!")
        ncm_vendas = pd.DataFrame()
    else:
        debug_print(f"[DEBUG] Processando sheet de Vendas: '{vendas_sheet}'")

        # ABORDAGEM: Ler sheet inteira sem header, procurar linha de header por nome de coluna
        df_nv_raw = pd.read_excel(path, sheet_name=vendas_sheet, engine="openpyxl", header=None)

        header_row_v = None
        # Procura linha que contém "Código NCM" ou "NCM" como coluna (não título)
        for i in range(min(10, len(df_nv_raw))):
            row_text = ' '.join([normalize(str(v)) for v in df_nv_raw.iloc[i].values if pd.notna(v)])
            # Verifica se tem NCM E pelo menos mais 2 palavras-chave de colunas
            has_ncm = 'codigo ncm' in row_text or (row_text.strip().split() and 'ncm' in [normalize(w) for w in row_text.split()])
            column_keywords = ['tipo', 'descricao', 'produto', 'cest', 'cfop', 'st', 'cst', 'beneficio']
            keyword_count = sum(1 for kw in column_keywords if kw in row_text)
            if has_ncm and keyword_count >= 2:
                header_row_v = i
                debug_print(f"[OK] Header de Vendas encontrado na linha {i}")
                break

        if header_row_v is not None:
            # Ler novamente com o header correto
            df_nv = pd.read_excel(path, sheet_name=vendas_sheet, engine="openpyxl", header=header_row_v)

            # Mapear colunas por nome
            col_map_v = {}
            for c in df_nv.columns:
                nc = normalize(str(c))
                # Para vendas, usa UF de origem (Cliente/Filial), NÃO destino
                if "uf cliente" in nc and "destino" not in nc:
                    col_map_v[c] = "UF_Cliente"
                elif "uf filial" in nc and "destino" not in nc:
                    col_map_v[c] = "UF_Cliente"
                elif "codigo ncm" in nc or nc.strip() == "ncm":
                    col_map_v[c] = "NCM"
                elif "descricao" in nc or "descri" in nc:
                    col_map_v[c] = "Descricao"
                elif "beneficio" in nc:
                    col_map_v[c] = "Beneficio"
                elif "possui st" in nc:
                    col_map_v[c] = "PossuiST"
                elif "cfop" in nc:
                    col_map_v[c] = "CFOP"

            df_nv = df_nv.rename(columns=col_map_v)

            # Verifica se tem coluna NCM
            if "NCM" not in df_nv.columns:
                debug_print(f"[ERRO] Coluna NCM não encontrada na sheet de Vendas")
                ncm_vendas = pd.DataFrame()
            else:
                # Verifica se tem coluna UF
                has_uf = "UF_Cliente" in df_nv.columns

                if not has_uf:
                    # Sem UF: criar coluna UF_Cliente com "TODAS" para expandir depois
                    debug_print(f"[INFO] Coluna UF não encontrada em Vendas - expandindo para todas as UFs")
                    df_nv["UF_Cliente"] = "TODAS"

                # Expande linhas com "Todas UFs" em 27 linhas (uma por UF)
                if "UF_Cliente" in df_nv.columns:
                    df_nv = expand_all_ufs(df_nv, "UF_Cliente")

                df_nv = df_nv.dropna(subset=["NCM"])
                df_nv = df_nv.reset_index(drop=True).copy()

                # Limpa NCM
                ncm_col = df_nv["NCM"]
                if isinstance(ncm_col, pd.DataFrame):
                    ncm_col = ncm_col.iloc[:, 0]

                df_nv["NCM"] = ncm_col.apply(clean_ncm).astype(str).values

                # Filtra NCMs válidos (>= 4 caracteres)
                valid_indices = [i for i, ncm in enumerate(df_nv["NCM"].values) if len(str(ncm)) >= 4]
                ncm_vendas = df_nv.iloc[valid_indices].reset_index(drop=True)
                debug_print(f"[OK] NCM Vendas carregado: {len(ncm_vendas)} linhas" + (" (expandido para todas UFs)" if not has_uf else ""))
        else:
            debug_print(f"[ERRO] Header não encontrado na sheet de Vendas '{vendas_sheet}'")
            try:
                df_nv_debug = pd.read_excel(path, sheet_name=vendas_sheet, engine="openpyxl", header=None, nrows=5)
                debug_print(f"[DEBUG] Primeiras 5 linhas da sheet:")
                debug_print(df_nv_debug.head().to_string())
            except Exception as e:
                debug_print(f"[DEBUG] Erro ao ler sheet: {e}")
            ncm_vendas = pd.DataFrame()

    # ── Municipalities ──
    municipios_sheet = detected_sheets['municipios']

    # Se a sheet detectada não tem "Município" ou "Cidade" no nome, tentar fallback por nome
    if municipios_sheet and not any(kw in municipios_sheet.lower() for kw in ["municipio", "cidade", "city", "cities", "iss", "servico"]):
        debug_print(f"[AVISO] Sheet detectada '{municipios_sheet}' não tem nome relevante para Municípios, tentando fallback...")
        municipios_sheet = None

    if not municipios_sheet:
        # Fallback: tentar encontrar por nome
        municipios_sheet = (
            find_sheet_by_keywords(all_sheets, ["municipios", "servicos"], SHEET_SYNONYMS, "Municípios") or
            find_sheet_by_keywords(all_sheets, ["municipio"], SHEET_SYNONYMS, "Município") or
            find_sheet_by_keywords(all_sheets, ["municipios"], SHEET_SYNONYMS, "Municípios") or
            find_sheet_by_keywords(all_sheets, ["cidades"], SHEET_SYNONYMS, "Cidades") or
            find_sheet_by_keywords(all_sheets, ["cities"], SHEET_SYNONYMS, "Cities") or
            find_sheet_by_keywords(all_sheets, ["iss"], SHEET_SYNONYMS, "ISS")
        )

    if not municipios_sheet:
        debug_print("[AVISO] Sheet de Municípios não encontrada!")
        mun_rows = pd.DataFrame()
    else:
        mun_rows = _extract_municipios_from_sheet(path, municipios_sheet)

    # ── Collect unique CFOPs ──
    cfops_declarados = set()

    # REGRA 1: Coletar CFOPs das sheets de NCM Compras e Vendas (existente)
    if not ncm_compras.empty and "CFOP" in ncm_compras.columns:
        for cfop in ncm_compras["CFOP"].dropna():
            cfop_str = str(cfop).strip()
            if cfop_str and cfop_str.lower() != "nan":
                cfops_declarados.add(cfop_str)
    if not ncm_vendas.empty and "CFOP" in ncm_vendas.columns:
        for cfop in ncm_vendas["CFOP"].dropna():
            cfop_str = str(cfop).strip()
            if cfop_str and cfop_str.lower() != "nan":
                cfops_declarados.add(cfop_str)

    # REGRA 2: Coletar CFOPs de uma sheet específica de CFOP (colunas A e C)
    # Procura por sheet que contenha "CFOP" no nome
    cfop_sheet = find_sheet_by_keywords(all_sheets, ["cfop"], SHEET_SYNONYMS, "CFOP")

    if cfop_sheet:
        try:
            debug_print(f"[DEBUG] Processando sheet específica de CFOP: '{cfop_sheet}'")

            # Ler sheet inteira sem header para procurar linha de dados
            df_cfop_raw = pd.read_excel(path, sheet_name=cfop_sheet, engine="openpyxl", header=None)

            # Procura linha de header (que contenha "CFOP" ou "Código")
            header_row_cfop = None
            for i in range(min(10, len(df_cfop_raw))):
                row_text = ' '.join([normalize(str(v)) for v in df_cfop_raw.iloc[i].values if pd.notna(v)])
                if 'cfop' in row_text or 'codigo' in row_text:
                    header_row_cfop = i
                    debug_print(f"[OK] Header de CFOP encontrado na linha {i}")
                    break

            # Se não encontrou header, assume que os dados começam na linha 0
            if header_row_cfop is None:
                header_row_cfop = 0
                debug_print(f"[INFO] Header de CFOP não encontrado, assumindo dados começam na linha 0")

            # Ler sheet com header ou a partir da primeira linha de dados
            df_cfop = pd.read_excel(path, sheet_name=cfop_sheet, engine="openpyxl", header=header_row_cfop)

            # IMPORTANTE: Usar colunas A (índice 0) e C (índice 2) como solicitado
            # Coluna A = CFOP, Coluna C = Descrição (para referência)
            if len(df_cfop.columns) >= 3:
                col_a = df_cfop.iloc[:, 0]  # Coluna A (índice 0)
                col_c = df_cfop.iloc[:, 2]  # Coluna C (índice 2)

                debug_print(f"[INFO] Lendo CFOPs da sheet '{cfop_sheet}' - Coluna A (CFOP) e Coluna C (Descrição)")

                # Extrair CFOPs da coluna A
                for idx, cfop_value in enumerate(col_a):
                    if pd.notna(cfop_value):
                        cfop_str = str(cfop_value).strip()
                        # Limpa CFOP (remove pontos, espaços, etc) e valida formato (4 dígitos)
                        cfop_clean = re.sub(r'[^\d]', '', cfop_str)

                        # Valida se é um CFOP válido (4 dígitos começando com 1-7)
                        if cfop_clean and len(cfop_clean) == 4 and cfop_clean[0] in '1234567':
                            cfops_declarados.add(cfop_clean)

                            # Log para debug (primeiros 5 apenas)
                            if len(cfops_declarados) <= 5:
                                desc = str(col_c.iloc[idx]) if idx < len(col_c) and pd.notna(col_c.iloc[idx]) else ""
                                debug_print(f"   - CFOP {cfop_clean}: {desc[:50]}")

                debug_print(f"[OK] {len([c for c in cfops_declarados if len(c) == 4])} CFOPs adicionados da sheet específica")
            else:
                debug_print(f"[AVISO] Sheet '{cfop_sheet}' não tem pelo menos 3 colunas (A, B, C)")

        except Exception as e:
            debug_print(f"[AVISO] Erro ao processar sheet de CFOP '{cfop_sheet}': {e}")
    else:
        debug_print("[INFO] Nenhuma sheet específica de CFOP encontrada (isso é normal se CFOPs estão nas sheets de NCM)")

    return dict(
        general=general,
        ncm_compras=ncm_compras,
        ncm_vendas=ncm_vendas,
        municipios_cliente=mun_rows,
        cfops_declarados=sorted(cfops_declarados),
        _debug_sheets=detection_log,  # Para debug: mostra quais sheets foram detectadas
        _debug_all_sheets=all_sheets,  # Para debug: lista todas as sheets do arquivo
        _debug_columns=columns_info,  # Para debug: colunas encontradas em cada sheet
    )


# ── analysis functions ────────────────────────────────────────────────────────

def analyse_ncm(ncm_df: pd.DataFrame, uf_col: str, direction: str,
                sector_sheet_df: pd.DataFrame) -> dict:
    """
    For each (NCM, UF) pair in ncm_df, looks up coverage in sector_sheet_df.
    direction : 'Compras' or 'Vendas'
    uf_col    : column name in ncm_df that holds the relevant UF
    Returns structured result dict.
    """
    if ncm_df.empty or sector_sheet_df is None:
        return {"score": None, "total_pairs": 0, "covered": 0, "gaps": [], "detail": []}

    # Build lookup: NCM ->{UF: coverage_value}
    # IMPORTANTE: Normaliza NCMs para formato padrão (apenas dígitos)
    lookup = {}
    original_ncm_map = {}  # Mantém NCM original para exibição
    for _, row in sector_sheet_df.iterrows():
        ncm_raw = str(row["COMMODITY_CODE"])
        ncm_normalized = clean_ncm(ncm_raw)
        # Preserva valores como estão na planilha (texto "Atendido"/"Não atendido")
        lookup[ncm_normalized] = {uf: row.get(uf, None) for uf in UF_COLS}
        original_ncm_map[ncm_normalized] = ncm_raw

    results = []
    for _, row in ncm_df.iterrows():
        ncm_raw = str(row.get("NCM", "")).strip()
        ncm_normalized = clean_ncm(ncm_raw)
        uf  = str(row.get(uf_col, "")).strip().upper()

        if not ncm_normalized or not uf or uf == "NAN":
            continue

        # Busca exata com NCM normalizado
        cov = lookup.get(ncm_normalized, {}).get(uf, None)

        # Try parent NCM (ex: 30049019 ->300490, 30049000 ->300490)
        if cov is None and len(ncm_normalized) >= 6:
            # Tenta com 6 dígitos (capítulo + posição)
            parent_ncm = ncm_normalized[:6]
            cov = lookup.get(parent_ncm, {}).get(uf, None)

            # Se não encontrou, tenta com 4 dígitos (capítulo)
            if cov is None and len(ncm_normalized) >= 4:
                parent_ncm = ncm_normalized[:4]
                cov = lookup.get(parent_ncm, {}).get(uf, None)

        # Verifica se há cobertura (valores > 0, como 1 para Pharma ou 100 para Chemical)
        # Também aceita texto "Atendido" se houver
        if cov is not None:
            cov_str = normalize(str(cov))
            covered = (cov_str == "atendido") or (isinstance(cov, (int, float)) and cov > 0)
        else:
            covered = False
        results.append({
            "NCM": ncm_raw,  # Mantém formato original do cliente para exibição
            "UF":  uf,
            "Cobertura": cov,
            "Coberto": covered,
            "Descricao": str(row.get("Descricao", "")),
        })

    if not results:
        return {"score": None, "total_pairs": 0, "covered": 0, "gaps": [], "detail": []}

    total = len(results)
    covered_count = sum(1 for r in results if r["Coberto"])
    score = round(covered_count / total * 100, 1) if total else 0

    gaps = [r for r in results if not r["Coberto"]]

    return {
        "score": score,
        "total_pairs": total,
        "covered": covered_count,
        "gaps": gaps,
        "detail": results,
    }


def analyse_ncm_by_uf_summary(detail: list) -> dict:
    """Score consolidado + detalhe por UF com gap."""
    if not detail:
        return {}
    uf_stats = {}
    for r in detail:
        uf = r["UF"]
        uf_stats.setdefault(uf, {"total": 0, "covered": 0})
        uf_stats[uf]["total"] += 1
        if r["Coberto"]:
            uf_stats[uf]["covered"] += 1
    result = {}
    for uf, s in sorted(uf_stats.items()):
        score = round(s["covered"] / s["total"] * 100, 1) if s["total"] else 0
        result[uf] = {
            "score": score,
            "covered": s["covered"],
            "total": s["total"],
            "gap": s["total"] - s["covered"],
            "has_gap": score < 100,
        }
    return result


def _match_city(cidade_norm: str, cidade_compact: str, uf: str, covered_dict: dict,
                fuzzy_threshold: float = 0.88):
    """
    Tenta casar um município do cliente contra a base oficial em 3 níveis:
      1. Match exato pela chave primária (normalize_city)
      2. Match pela chave secundária (sem stopwords "de/do/da", sem espaços)
      3. Fuzzy match (similaridade ≥ threshold) limitado à mesma UF

    Returns:
        dict {"matched": bool, "mode": "exact"|"secondary"|"fuzzy"|None,
              "matched_name": str|None, "canonical_key": str|None,
              "similarity": float}

        canonical_key: chave estável (primary key + uf) que pode ser usada
        para deduplicar entradas equivalentes do cliente.
    """
    empty = {"matched": False, "mode": None, "matched_name": None,
             "canonical_key": None, "similarity": 0.0}

    if not cidade_norm or not uf:
        return empty

    primary = covered_dict.get("_primary", {})
    secondary = covered_dict.get("_secondary", {})
    primary_to_canonical = covered_dict.get("_primary_to_canonical", {})
    secondary_to_canonical = covered_dict.get("_secondary_to_canonical", {})
    by_uf = covered_dict.get("_by_uf", {})

    # Nível 1: match exato (chave primária)
    if (cidade_norm, uf) in primary:
        canonical = primary_to_canonical.get((cidade_norm, uf), cidade_norm)
        return {
            "matched": True,
            "mode": "exact",
            "matched_name": primary[(cidade_norm, uf)],
            "canonical_key": f"{canonical}|{uf}",
            "similarity": 1.0,
        }

    # Compatibilidade: dict no formato legado
    if not primary and (cidade_norm, uf) in covered_dict:
        return {
            "matched": True,
            "mode": "exact",
            "matched_name": cidade_norm,
            "canonical_key": f"{cidade_norm}|{uf}",
            "similarity": 1.0,
        }

    # Nível 2: match na chave secundária (sem stopwords)
    if cidade_compact and (cidade_compact, uf) in secondary:
        canonical = secondary_to_canonical.get((cidade_compact, uf), cidade_compact)
        return {
            "matched": True,
            "mode": "secondary",
            "matched_name": secondary[(cidade_compact, uf)],
            "canonical_key": f"{canonical}|{uf}",
            "similarity": 1.0,
        }

    # Nível 3: fuzzy match dentro da mesma UF
    candidates = by_uf.get(uf, [])
    if candidates:
        matched_name, similarity = best_fuzzy_match(cidade_norm, candidates, fuzzy_threshold)
        if matched_name:
            display = primary.get((matched_name, uf), matched_name)
            canonical = primary_to_canonical.get((matched_name, uf), matched_name)
            return {
                "matched": True,
                "mode": "fuzzy",
                "matched_name": display,
                "canonical_key": f"{canonical}|{uf}",
                "similarity": similarity,
            }

    return empty


def analyse_municipios(client_mun_df: pd.DataFrame, covered_dict: dict,
                        fuzzy_threshold: float = 0.90) -> dict:
    """
    Analisa municípios verificando SEMPRE contra a lista oficial de aderência.

    Estratégia de matching (em ordem):
      1. Match exato após normalização (acentos, pontuação, caixa)
      2. Match após remover stopwords ("de/do/da/dos") e espaços
      3. Fuzzy match por similaridade (≥ fuzzy_threshold) restrito à mesma UF

    O fuzzy match resolve:
      - Encoding corrompido no base ("Rond�nia" vs "Rondônia")
      - Erros de digitação leves ("Joao Pesoa" vs "João Pessoa")
      - Variações de pontuação/apóstrofo ("D'Oeste" vs "D Oeste" vs "DOeste")

    IMPORTANTE: Ignora a coluna "Status" do arquivo do cliente.
    A validação é feita APENAS contra a base oficial.

    Retorna:
      - detail: TODAS as linhas originais do arquivo, cada uma marcada com status de cobertura
      - in_scope / out_of_scope: listas formatadas "Cidade (UF)" de municípios ÚNICOS
      - score: % de cobertura considerando apenas municípios únicos (2 casas decimais)
      - fuzzy_matches: lista de matches via fuzzy (para auditoria)
    """
    if client_mun_df.empty:
        return {"total": 0, "in_scope": [], "score": None, "detail": []}

    # Placeholders/cabeçalhos que devem ser ignorados — EXATOS (sem startswith)
    # para não filtrar municípios reais como "Cidade Ocidental (GO)".
    PLACEHOLDERS = {
        "cidade", "estado", "municipio", "sigla",
        "nome do municipio", "cidade estado",
        "nome do municipio sigla da uf",
        "uf", "n a", "na",
        "fora do escopo", "placeholder", "exemplo",
    }

    VALID_UFS = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    }

    cidade_col = "Cidade" if "Cidade" in client_mun_df.columns else client_mun_df.columns[0]

    # Cache de matches: cada cidade única (normalized + UF) -> resultado do match
    # para evitar fazer match múltiplas vezes da mesma cidade
    match_cache = {}

    # Conjunto de municípios únicos (para calcular score)
    unique_keys = set()

    # Lista DETALHADA: TODAS as linhas do arquivo original, cada uma com status de cobertura
    detail = []

    # Diagnóstico: contadores de cada filtro
    diag = {
        "linhas_input": len(client_mun_df),
        "vazias": 0,
        "uf_invalida": 0,
        "cidade_muito_curta": 0,
        "placeholder": 0,
        "validas_pre_dedup": 0,
        "duplicatas_colapsadas": 0,
    }

    for _, row in client_mun_df.iterrows():
        cidade = str(row.get(cidade_col, "")).strip()
        uf_raw = str(row.get("UF", "")).strip()

        if not cidade or cidade.lower() == "nan" or not uf_raw or uf_raw.lower() == "nan":
            diag["vazias"] += 1
            continue

        # Normaliza UF: aceita sigla OU nome por extenso ("São Paulo" -> "SP")
        uf = _normalize_uf(uf_raw)
        if not uf or uf not in VALID_UFS:
            diag["uf_invalida"] += 1
            continue

        cidade_norm = normalize_city(cidade)
        if len(cidade_norm) < 3:
            diag["cidade_muito_curta"] += 1
            continue

        if cidade_norm in PLACEHOLDERS:
            diag["placeholder"] += 1
            continue

        diag["validas_pre_dedup"] += 1

        # Cache key para este município
        cache_key = f"{cidade_norm}|{uf}"

        # Se já processamos esta cidade, reutiliza o resultado
        if cache_key not in match_cache:
            cidade_compact = normalize_city_key(cidade)
            match = _match_city(cidade_norm, cidade_compact, uf, covered_dict, fuzzy_threshold)

            if match["matched"]:
                display = match["matched_name"] or cidade
            else:
                display = cidade

            match_cache[cache_key] = {
                "display": display,
                "matched": match["matched"],
                "mode": match["mode"] if match["matched"] else None,
                "similarity": round(match["similarity"], 3) if match["matched"] else None,
            }

        # Adiciona à lista de únicos (para cálculo de score)
        if cache_key not in unique_keys:
            unique_keys.add(cache_key)
        else:
            diag["duplicatas_colapsadas"] += 1

        # IMPORTANTE: Adiciona TODAS as linhas ao detail (sem dedup)
        cached = match_cache[cache_key]
        detail.append({
            "Cidade": cached["display"],
            "Cidade_Cliente": cidade,
            "UF": uf,
            "Coberto": cached["matched"],
            "Status": "Atendido" if cached["matched"] else "Não Atendido",
            "Modo_Match": cached["mode"],
            "Similaridade": cached["similarity"],
        })

    # Ordena: não-cobertos primeiro, depois alfabético — para o gap
    # aparecer no topo (mesmo padrão de NCMs)
    detail = sorted(
        detail,
        key=lambda r: (r["Coberto"], r["UF"], r["Cidade"])
    )

    # Para in_scope/out_of_scope: usar apenas municípios ÚNICOS (deduplicados)
    unique_detail = {}
    for r in detail:
        key = f"{r['Cidade']}|{r['UF']}"
        if key not in unique_detail:
            unique_detail[key] = r

    in_scope_unique = sorted(f"{r['Cidade']} ({r['UF']})" for r in unique_detail.values() if r["Coberto"])
    out_of_scope_unique = sorted(f"{r['Cidade']} ({r['UF']})" for r in unique_detail.values() if not r["Coberto"])

    # Fuzzy matches também apenas para únicos (para não duplicar na lista de auditoria)
    fuzzy_seen = set()
    fuzzy_matches = []
    for r in detail:
        if r["Modo_Match"] == "fuzzy":
            key = f"{r['Cidade_Cliente']}|{r['UF']}"
            if key not in fuzzy_seen:
                fuzzy_seen.add(key)
                fuzzy_matches.append({
                    "input": f"{r['Cidade_Cliente']} ({r['UF']})",
                    "matched": f"{r['Cidade']} ({r['UF']})",
                    "similarity": r["Similaridade"],
                })

    # Score calculado com base em municípios ÚNICOS, não em todas as linhas
    total_municipios = len(unique_detail)
    covered_count = sum(1 for r in unique_detail.values() if r["Coberto"])
    not_covered_count = total_municipios - covered_count

    debug_print(
        f"[DEBUG Análise Municípios] input={diag['linhas_input']} -> "
        f"vazias={diag['vazias']}, UF inválida={diag['uf_invalida']}, "
        f"cidade <3 chars={diag['cidade_muito_curta']}, placeholders={diag['placeholder']}, "
        f"válidas={diag['validas_pre_dedup']}, "
        f"duplicatas colapsadas={diag['duplicatas_colapsadas']} -> "
        f"únicos={total_municipios} (cobertos={covered_count}, fora={not_covered_count})"
    )

    if total_municipios == 0:
        return {
            "total": 0,
            "in_scope": [],
            "out_of_scope": [],
            "covered": 0,
            "not_covered": 0,
            "score": None,
            "detail": [],
            "fuzzy_matches": [],
            "diagnostico": diag,
        }

    score = round((covered_count / total_municipios) * 100.0, 2)

    return {
        "total": total_municipios,
        "in_scope": in_scope_unique,
        "out_of_scope": out_of_scope_unique,
        "covered": covered_count,
        "not_covered": not_covered_count,
        "score": score,
        "detail": detail,              # NOVO: lista completa com status por cidade
        "fuzzy_matches": fuzzy_matches,
        "diagnostico": diag,
    }


def analyse_csts(general: dict, cst_base: dict) -> dict:
    """
    Placeholder: in a real flow the client fills CSTs in the pre-diag.
    Here we return the full coverage map so the caller can render it.
    """
    return cst_base


def analyse_cfops(cfops_declarados: list, non_standard_cfops: set) -> dict:
    """
    Cross-reference client CFOPs against non-standard operations list.
    Returns alerts for operations requiring customization.
    """
    if not cfops_declarados:
        return {
            "total_cfops": 0,
            "standard": [],
            "non_standard": [],
            "alertas": [],
        }

    standard = []
    non_standard = []
    alertas = []

    for cfop in cfops_declarados:
        if cfop in non_standard_cfops:
            non_standard.append(cfop)
            alertas.append({
                "CFOP": cfop,
                "Tipo": "Não Atendida",
                "Mensagem": f"CFOP {cfop} requer customização - operação não-standard"
            })
        else:
            standard.append(cfop)

    return {
        "total_cfops": len(cfops_declarados),
        "standard": sorted(standard),
        "non_standard": sorted(non_standard),
        "alertas": alertas,
        # CFOP não tem score - apenas informativo (como CST)
    }


# ── orchestrator ─────────────────────────────────────────────────────────────

def run_analysis(prediag_path: str, aderencia_path: str) -> dict:
    base = load_adherence_base(Path(aderencia_path))
    diag = load_prediag(Path(prediag_path))

    segmento = diag["general"].get("segmento", "")
    inbound_sheet, outbound_sheet = pick_sector(segmento)

    debug_print(f"[DEBUG] Segmento detectado: '{segmento}' (apenas informativo)")
    debug_print(f"[DEBUG] Sheets selecionadas (legado): Inbound='{inbound_sheet}', Outbound='{outbound_sheet}'")
    debug_print(f"[DEBUG] Sheets disponíveis na base: {list(base['sector_sheets'].keys())}")

    # ── NOVA LÓGICA: Usa base consolidada de TODOS os setores ──
    # Analisa contra ALL_SECTORS ao invés de sheets específicas por segmento
    all_sectors = base["sector_sheets"].get("ALL_SECTORS")

    if all_sectors is not None:
        debug_print(f"[OK] Usando base consolidada com {len(all_sectors)} NCMs de todos os setores")
        sector_in = all_sectors
        sector_out = all_sectors
    else:
        # Fallback: usa lógica antiga se ALL_SECTORS não existir
        debug_print(f"[AVISO] Base consolidada não encontrada, usando lógica por segmento")
        sector_in  = base["sector_sheets"].get(inbound_sheet)
        sector_out = base["sector_sheets"].get(outbound_sheet)

    # ── NCM × UF analysis ──
    ncm_compras_result = analyse_ncm(
        diag["ncm_compras"], "UF_Fornecedor", "Compras", sector_in
    )
    ncm_vendas_result = analyse_ncm(
        diag["ncm_vendas"], "UF_Cliente", "Vendas", sector_out
    )

    uf_summary_compras = analyse_ncm_by_uf_summary(ncm_compras_result["detail"])
    uf_summary_vendas  = analyse_ncm_by_uf_summary(ncm_vendas_result["detail"])

    # ── Municipalities ──
    municipios_result = analyse_municipios(
        diag["municipios_cliente"], base["municipios"]
    )

    # ── CSTs ──
    cst_result = analyse_csts(diag["general"], base["cst_coverage"])

    # ── CFOPs ──
    cfop_result = analyse_cfops(diag.get("cfops_declarados", []), base["non_standard"])

    # ── Overall score (weighted: NCM compras 35%, vendas 35%, municípios 30%) ──
    # CFOP não entra no score geral, apenas é informativo
    scores = []
    weights = []
    if ncm_compras_result["score"] is not None:
        scores.append(ncm_compras_result["score"])
        weights.append(0.35)
    if ncm_vendas_result["score"] is not None:
        scores.append(ncm_vendas_result["score"])
        weights.append(0.35)
    if municipios_result["score"] is not None:
        scores.append(municipios_result["score"])
        weights.append(0.30)

    if scores:
        total_w = sum(weights)
        overall = round(sum(s * w for s, w in zip(scores, weights)) / total_w, 1)
    else:
        overall = None

    return {
        "general": diag["general"],
        "sector": {"inbound": inbound_sheet, "outbound": outbound_sheet},
        "overall_score": overall,
        "ncm_compras": {**ncm_compras_result, "uf_summary": uf_summary_compras},
        "ncm_vendas":  {**ncm_vendas_result,  "uf_summary": uf_summary_vendas},
        "municipios":  municipios_result,
        "cst_coverage": cst_result,
        "cfops": cfop_result,
        # Debug info
        "_debug_sheets": diag.get("_debug_sheets", []),
        "_debug_all_sheets": diag.get("_debug_all_sheets", []),
        "_debug_columns": diag.get("_debug_columns", {}),
    }


# ── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json, sys

    # Verifica se deve imprimir apenas JSON (sem debug)
    json_only = "--json-only" in sys.argv
    if json_only:
        sys.argv.remove("--json-only")
        # Ativa modo silencioso (sem debug)
        import idt_engine
        idt_engine.QUIET_MODE = True
        globals()['QUIET_MODE'] = True

    prediag   = sys.argv[1] if len(sys.argv) > 1 else "Pre Diagnóstico IDT 2025 Trimble_280425_v2_conteudo.xlsx"
    aderencia = sys.argv[2] if len(sys.argv) > 2 else "Aderencia-.xlsm"

    result = run_analysis(prediag, aderencia)

    # Se --json-only, imprime apenas o JSON e sai
    if json_only:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        sys.exit(0)

    debug_print("=" * 60)
    debug_print(f"CLIENTE   : {result['general'].get('segmento','?')} | {result['general'].get('estados','?')}")
    debug_print(f"SETOR     : {result['sector']['inbound']} / {result['sector']['outbound']}")
    debug_print(f"SCORE GERAL: {result['overall_score']}%")
    debug_print()
    debug_print("-- NCM COMPRAS --")
    nc = result["ncm_compras"]
    debug_print(f"  Score: {nc['score']}%  ({nc['covered']}/{nc['total_pairs']} pares NCM x UF cobertos)")
    if nc.get("uf_summary"):
        gaps_uf = {uf: v for uf, v in nc["uf_summary"].items() if v["has_gap"]}
        if gaps_uf:
            debug_print(f"  UFs com gap ({len(gaps_uf)}): " + ", ".join(
                f"{uf} {v['score']}%" for uf, v in sorted(gaps_uf.items())))
    if nc["gaps"]:
        debug_print(f"  Gaps ({len(nc['gaps'])} pares): " +
              ", ".join(f"{g['NCM']} x {g['UF']}" for g in nc["gaps"][:5]) +
              ("..." if len(nc["gaps"]) > 5 else ""))

    debug_print()
    debug_print("-- NCM VENDAS --")
    nv = result["ncm_vendas"]
    debug_print(f"  Score: {nv['score']}%  ({nv['covered']}/{nv['total_pairs']} pares NCM x UF cobertos)")
    if nv.get("uf_summary"):
        gaps_uf = {uf: v for uf, v in nv["uf_summary"].items() if v["has_gap"]}
        if gaps_uf:
            debug_print(f"  UFs com gap ({len(gaps_uf)}): " + ", ".join(
                f"{uf} {v['score']}%" for uf, v in sorted(gaps_uf.items())))

    debug_print()
    debug_print("-- MUNICIPIOS --")
    m = result["municipios"]
    debug_print(f"  Total: {m['total']} | Dentro do escopo: {len(m.get('in_scope', []))} | Fora: {len(m.get('out_of_scope', []))}")
    if m.get("out_of_scope"):
        debug_print(f"  Fora do escopo: {', '.join(m['out_of_scope'][:10])}" +
              ("..." if len(m["out_of_scope"]) > 10 else ""))

    debug_print()
    debug_print("-- CFOPs --")
    cfop = result["cfops"]
    debug_print(f"  Total CFOPs declarados: {cfop['total_cfops']}")
    debug_print(f"  Standard (atendidos): {len(cfop['standard'])}")
    debug_print(f"  Nao-standard (requerem customizacao): {len(cfop['non_standard'])}")
    if cfop["alertas"]:
        debug_print(f"  ALERTAS ({len(cfop['alertas'])}):")
        for alerta in cfop["alertas"][:5]:
            debug_print(f"     - CFOP {alerta['CFOP']}: {alerta['Mensagem']}")
        if len(cfop["alertas"]) > 5:
            debug_print(f"     ... e mais {len(cfop['alertas']) - 5} alertas")

    debug_print()
    # Salva JSON completo em arquivo para o site
    json_output = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    output_file = "idt_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json_output)
    debug_print(f"[OK] Resultado completo salvo em: {output_file}")
    debug_print()
    debug_print("-- JSON COMPLETO --")
    debug_print(json_output)
