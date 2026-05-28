"""
IDT Adherence Engine
====================
Reads a pre-diagnosis Excel (client-filled) + Aderencia.xlsm (coverage base)
and produces a structured adherence report.

NCM cross-reference rules:
  - Purchases : UF = UF_Fornecedor (supplier state)
  - Sales      : UF = UF_Cliente   (customer/origin state)

Coverage score = % of NCM×UF combinations where cell value > 0 (1 for Pharma, 100 for Chemical)
Partial coverage → consolidated score + list of UFs with gap
Municipalities   → compare against 834-city list; flag out-of-scope ones
"""

import re
import unicodedata
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
    # keywords from "segmento" field → (inbound_sheet, outbound_sheet)
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
    - Com pontos: 3004.90.00 → 30049000
    - Sem pontos: 30049000 → 30049000
    - Com espaços: 3004 90 00 → 30049000
    - Com hífen: 3004-90-00 → 30049000
    - Com barra: 3004/90/00 → 30049000
    - Formato HS: 3004.90 → 300490

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

        # Criar lookup de (municipio_normalizado, UF) → True
        # APENAS para municípios com Aderencia = 1 (cobertos)
        municipios = {}
        for _, row in df_mun.iterrows():
            uf = str(row.iloc[1]).strip().upper()  # Coluna B (índice 1)
            mun_c = str(row.iloc[2]).strip()  # Coluna C (índice 2) - Nome com acentos
            mun_d = str(row.iloc[3]).strip()  # Coluna D (índice 3) - Nome normalizado
            aderencia_raw = row.iloc[4] if len(row) > 4 else 0  # Coluna E (índice 4) - Aderencia

            # CRÍTICO: Apenas municípios com Aderencia cobertos
            # Aceita tanto número (1) quanto texto ("Atendido", "Atentido", etc)
            aderencia_str = normalize(str(aderencia_raw))
            is_covered = (
                aderencia_raw == 1 or  # Aceita número 1
                "atend" in aderencia_str or  # Aceita "Atendido" (correto)
                "atent" in aderencia_str  # Aceita "Atentido" (typo na base)
            )

            if not is_covered:
                continue

            # Validações rigorosas
            if not mun_c or mun_c.lower() == 'nan' or len(mun_c) < 3:
                continue
            if not uf or uf.lower() == 'nan' or uf not in VALID_UFS:
                continue

            # Normaliza e adiciona à lookup
            mun_normalized = normalize(mun_c)

            # Só adiciona se o nome normalizado for válido (mínimo 3 caracteres)
            if len(mun_normalized) >= 3:
                municipios[(mun_normalized, uf)] = True

            # Se a coluna D (normalizado) existir e for diferente da C, adiciona também
            if mun_d and mun_d.lower() != 'nan' and mun_d != mun_c:
                mun_d_normalized = normalize(mun_d)
                if len(mun_d_normalized) >= 3:
                    municipios[(mun_d_normalized, uf)] = True

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
        # Se tem NCM e UF Cliente/Destino → Vendas
        if 'cliente' in cols_text or 'destino' in cols_text or 'saida' in cols_text:
            return 'ncm_vendas'
        # Se tem NCM mas não tem indicador claro, pode ser Compras (default)
        if 'uf' in cols_text:
            return 'ncm_compras'

    return None


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
        # Ler sheet sem header para procurar linha do header
        df_mun_raw = pd.read_excel(path, sheet_name=municipios_sheet, engine="openpyxl", header=None)

        header_row_mun = None
        # Procura linha que contém "Cidade" ou "Município" E "Estado" ou "UF"
        for i in range(min(10, len(df_mun_raw))):
            row_text = ' '.join([normalize(str(v)) for v in df_mun_raw.iloc[i].values if pd.notna(v)])
            if ('cidade' in row_text or 'municipio' in row_text) and ('estado' in row_text or 'uf' in row_text):
                header_row_mun = i
                debug_print(f"[OK] Header de Municípios encontrado na linha {i}")
                break

        if header_row_mun is not None:
            # Reler com header correto
            df_mun = pd.read_excel(path, sheet_name=municipios_sheet, engine="openpyxl", header=header_row_mun)
            df_mun.columns = [normalize(str(c)) for c in df_mun.columns]

            # find cidade/estado columns
            cidade_col = next((c for c in df_mun.columns if "cidade" in c or "municipio" in c), None)
            estado_col = next((c for c in df_mun.columns if "estado" in c or c == "uf"), None)
            status_col = next((c for c in df_mun.columns if "status" in c), None)

            # VALIDAÇÃO: Só processa se encontrar colunas de cidade E estado
            if not cidade_col or not estado_col:
                debug_print(f"[AVISO] Sheet '{municipios_sheet}' não tem colunas de Cidade/Município e UF/Estado - ignorando")
                mun_rows = pd.DataFrame()
            elif cidade_col:
                mun_rows = df_mun[[c for c in [estado_col, cidade_col, status_col] if c]].dropna(subset=[cidade_col])
                mun_rows = mun_rows.rename(columns={
                    cidade_col: "Cidade",
                    estado_col: "UF",
                    status_col: "Status"
                } if status_col else {cidade_col: "Cidade", estado_col: "UF"})

                # Filtrar linhas inválidas (placeholders como "Fora do escopo")
                mun_rows = mun_rows[~mun_rows["Cidade"].str.lower().str.contains("fora do escopo|placeholder|exemplo", na=False)]

                # VALIDAÇÃO: Se tiver muito pouco dado (< 3 linhas), provavelmente não é sheet de municípios
                if len(mun_rows) < 3:
                    debug_print(f"[AVISO] Sheet '{municipios_sheet}' tem muito pouco dado ({len(mun_rows)} linhas) - provavelmente não é sheet de municípios")
                    mun_rows = pd.DataFrame()
                else:
                    debug_print(f"[OK] Municípios carregados: {len(mun_rows)} linhas")
            else:
                debug_print(f"[AVISO] Sheet '{municipios_sheet}' não tem estrutura de municípios esperada - ignorando")
                mun_rows = pd.DataFrame()
        else:
            debug_print(f"[ERRO] Header não encontrado na sheet de Municípios '{municipios_sheet}'")
            mun_rows = pd.DataFrame()

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
    Analisa pares (NCM, UF) contra a base oficial de aderência.

    3 Status possíveis:
    - "Atendido": NCM encontrado na base + cobertura "Atendido" para a UF
    - "Não Atendido": NCM encontrado na base + cobertura "Não Atendido" para a UF
    - "NCM Não Encontrado": NCM NÃO existe na base oficial

    Modos de Match (auditoria):
    - "exato": NCM completo bate com a base
    - "parent_6": Match aproximado via NCM[:6] (subposição)
    - "parent_4": Match aproximado via NCM[:4] (capítulo)
    - None: Sem match (NCM Não Encontrado)

    Score = (linhas_atendidas / total_linhas) × 100  [por volumetria de pares]

    direction : 'Compras' or 'Vendas'
    uf_col    : column name in ncm_df that holds the relevant UF
    """
    empty_result = {
        "score": None,
        "total_pairs": 0, "total_linhas": 0,
        "covered": 0, "linhas_atendidas": 0,
        "linhas_nao_atendidas": 0, "linhas_nao_encontradas": 0,
        "linhas_match_aproximado": 0,
        "total_ncms_unicos": 0,
        "ncms_atendidos": 0, "ncms_nao_atendidos": 0, "ncms_nao_encontrados": 0,
        "gaps": [], "detail": [],
        "ncms_nao_encontrados_lista": [],
    }
    if ncm_df.empty or sector_sheet_df is None:
        return empty_result

    # Build lookup: NCM → {UF: coverage_value}
    lookup = {}
    for _, row in sector_sheet_df.iterrows():
        ncm_raw = str(row["COMMODITY_CODE"])
        ncm_normalized = clean_ncm(ncm_raw)
        lookup[ncm_normalized] = {uf: row.get(uf, None) for uf in UF_COLS}

    results = []
    for _, row in ncm_df.iterrows():
        ncm_raw = str(row.get("NCM", "")).strip()
        ncm_normalized = clean_ncm(ncm_raw)
        uf = str(row.get(uf_col, "")).strip().upper()

        if not ncm_normalized or not uf or uf == "NAN":
            continue

        # Determina tipo de match
        cov = None
        modo_match = None
        ncm_match = None  # NCM efetivamente casado na base

        # 1. Match exato
        if ncm_normalized in lookup:
            cov = lookup[ncm_normalized].get(uf, None)
            if cov is not None:
                modo_match = "exato"
                ncm_match = ncm_normalized

        # 2. Match aproximado via parent 6 dígitos
        if modo_match is None and len(ncm_normalized) >= 6:
            parent_ncm = ncm_normalized[:6]
            if parent_ncm in lookup:
                cov = lookup[parent_ncm].get(uf, None)
                if cov is not None:
                    modo_match = "parent_6"
                    ncm_match = parent_ncm

        # 3. Match aproximado via parent 4 dígitos
        if modo_match is None and len(ncm_normalized) >= 4:
            parent_ncm = ncm_normalized[:4]
            if parent_ncm in lookup:
                cov = lookup[parent_ncm].get(uf, None)
                if cov is not None:
                    modo_match = "parent_4"
                    ncm_match = parent_ncm

        # Determina Status
        if modo_match is None:
            # NCM não está na base oficial
            status = "NCM Não Encontrado"
            covered = False
        else:
            # Verifica se há cobertura na célula
            cov_str = normalize(str(cov)) if cov is not None else ""
            covered = (cov_str == "atendido") or (isinstance(cov, (int, float)) and cov > 0)
            status = "Atendido" if covered else "Não Atendido"

        results.append({
            "NCM": ncm_raw,
            "NCM_Normalizado": ncm_normalized,
            "NCM_Match": ncm_match,
            "UF": uf,
            "Cobertura": cov,
            "Coberto": covered,
            "Status": status,
            "Modo_Match": modo_match,
            "Descricao": str(row.get("Descricao", "")),
        })

    if not results:
        return empty_result

    # Totais por LINHAS (volumetria - pares NCM × UF)
    total_linhas = len(results)
    linhas_atendidas = sum(1 for r in results if r["Status"] == "Atendido")
    linhas_nao_atendidas = sum(1 for r in results if r["Status"] == "Não Atendido")
    linhas_nao_encontradas = sum(1 for r in results if r["Status"] == "NCM Não Encontrado")
    linhas_match_aproximado = sum(1 for r in results if r["Modo_Match"] in ("parent_6", "parent_4"))

    # Totais por NCMs ÚNICOS
    ncms_unicos = {r["NCM_Normalizado"]: r["Status"] for r in results}
    # Re-classifica: NCM é "Atendido" se pelo menos 1 par dele foi atendido
    ncm_best_status = {}
    for r in results:
        ncm_n = r["NCM_Normalizado"]
        if ncm_n not in ncm_best_status:
            ncm_best_status[ncm_n] = r["Status"]
        else:
            # Prioridade: Atendido > Não Atendido > NCM Não Encontrado
            priorities = {"Atendido": 3, "Não Atendido": 2, "NCM Não Encontrado": 1}
            if priorities.get(r["Status"], 0) > priorities.get(ncm_best_status[ncm_n], 0):
                ncm_best_status[ncm_n] = r["Status"]

    total_ncms_unicos = len(ncm_best_status)
    ncms_atendidos = sum(1 for s in ncm_best_status.values() if s == "Atendido")
    ncms_nao_atendidos = sum(1 for s in ncm_best_status.values() if s == "Não Atendido")
    ncms_nao_encontrados = sum(1 for s in ncm_best_status.values() if s == "NCM Não Encontrado")

    # Lista de NCMs não encontrados (únicos)
    ncms_nao_encontrados_lista = sorted({
        r["NCM"] for r in results if r["Status"] == "NCM Não Encontrado"
    })

    # Score baseado em LINHAS (volumetria) - igual municípios
    score = round(linhas_atendidas / total_linhas * 100, 2) if total_linhas else 0

    # Gaps: TODOS os pares não atendidos (inclui Não Atendido + NCM Não Encontrado)
    gaps = [r for r in results if not r["Coberto"]]

    return {
        # Score principal (por volumetria)
        "score": score,

        # Volumetria (PARES) - NOVO
        "total_pairs": total_linhas,  # alias para compatibilidade
        "total_linhas": total_linhas,
        "linhas_atendidas": linhas_atendidas,
        "linhas_nao_atendidas": linhas_nao_atendidas,
        "linhas_nao_encontradas": linhas_nao_encontradas,
        "linhas_match_aproximado": linhas_match_aproximado,

        # NCMs únicos - NOVO
        "total_ncms_unicos": total_ncms_unicos,
        "ncms_atendidos": ncms_atendidos,
        "ncms_nao_atendidos": ncms_nao_atendidos,
        "ncms_nao_encontrados": ncms_nao_encontrados,
        "ncms_nao_encontrados_lista": ncms_nao_encontrados_lista,

        # Compatibilidade
        "covered": linhas_atendidas,
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


def analyse_municipios(client_mun_df: pd.DataFrame, covered_dict: dict) -> dict:
    """
    Analisa municípios verificando SEMPRE contra a lista oficial de aderência (834 cidades).

    IMPORTANTE: Ignora a coluna "Status" do arquivo do cliente.
    A validação é feita APENAS contra a base oficial de municípios cobertos.

    NOVO: Inclui municípios não válidos (UF inválida) no cálculo de aderência.

    Status possíveis:
    - "Atendido": Município com UF válida encontrado na base oficial (834 cidades)
    - "Não Atendido": Município com UF válida MAS não encontrado na base oficial
    - "Município Não Válido": Município com UF inválida (ex: "NI", "NA", códigos inválidos)

    Retorna:
    - in_scope: Municípios cobertos (na lista oficial)  - Status: "Atendido"
    - out_of_scope: Municípios não cobertos (fora da lista oficial) - Status: "Não Atendido"
    - invalid: Municípios com UF inválida - Status: "Município Não Válido"
    - score: % de municípios ATENDIDOS em relação ao TOTAL (incluindo inválidos)
    - total: Quantidade total de municípios únicos (válidos + inválidos)
    - detail: TODAS as linhas com status detalhado para exibição no frontend
    """
    if client_mun_df.empty:
        return {"total": 0, "in_scope": [], "out_of_scope": [], "invalid": [], "score": None, "detail": []}

    # Placeholders/headers comuns que devem ser ignorados
    PLACEHOLDERS = [
        "cidade",
        "estado",
        "municipio",
        "sigla",
        "nome do municipio",
        "cidade (estado)",
        "nome do município (sigla da uf)",
        "município",
        "uf",
        "n a",
        "na",
        "exemplo",
        "placeholder",
    ]

    # Lista de UFs válidas do Brasil
    VALID_UFS = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    }

    cidade_col = "Cidade" if "Cidade" in client_mun_df.columns else client_mun_df.columns[0]

    in_scope = []
    out_of_scope = []
    invalid = []
    detail = []  # Lista DETALHADA para exibir no frontend

    # Conjunto para rastrear municípios únicos (deduplicação)
    seen_municipalities = set()

    for _, row in client_mun_df.iterrows():
        cidade = str(row.get(cidade_col, "")).strip()
        uf_raw = str(row.get("UF", "")).strip().upper()

        # Pula células vazias ou inválidas
        if not cidade or cidade.lower() == "nan" or not uf_raw or uf_raw.lower() == "nan":
            continue

        cidade_normalized = normalize(cidade)

        # Ignora strings muito curtas (provavelmente não são nomes de cidades válidos)
        if len(cidade_normalized) < 3:
            continue

        # Verifica se é placeholder/header - ignora completamente
        # Usa match EXATO apenas, sem startswith para evitar ignorar municípios reais
        # como "Cidade Ocidental (GO)"
        is_placeholder = cidade_normalized in PLACEHOLDERS
        if is_placeholder:
            continue

        # === NOVA LÓGICA: Valida UF ANTES de fazer lookup ===
        if uf_raw not in VALID_UFS:
            # UF INVÁLIDA: marca como "Município Não Válido"
            municipality_key = f"{cidade_normalized}|{uf_raw}"

            # Adiciona ao detail (TODAS as linhas)
            detail.append({
                "Cidade": cidade,
                "Cidade_Cliente": cidade,
                "UF": uf_raw,  # Mantém UF inválida original (ex: "NI")
                "Coberto": False,
                "Status": "Município Não Válido",
                "Modo_Match": None,
                "Similaridade": None,
            })

            # Adiciona à lista de inválidos (apenas únicos)
            if municipality_key not in seen_municipalities:
                invalid.append(f"{cidade} ({uf_raw})")
                seen_municipalities.add(municipality_key)

            continue

        # UF VÁLIDA: Procede com validação contra base oficial
        uf = uf_raw  # UF já validada
        lookup_key = (cidade_normalized, uf)
        is_covered = lookup_key in covered_dict

        municipality_key = f"{cidade_normalized}|{uf}"

        # Adiciona ao detail (TODAS as linhas)
        if is_covered:
            detail.append({
                "Cidade": cidade,
                "Cidade_Cliente": cidade,
                "UF": uf,
                "Coberto": True,
                "Status": "Atendido",
                "Modo_Match": "exact",  # Simplificado para esta versão
                "Similaridade": 1.0,
            })
        else:
            detail.append({
                "Cidade": cidade,
                "Cidade_Cliente": cidade,
                "UF": uf,
                "Coberto": False,
                "Status": "Não Atendido",
                "Modo_Match": None,
                "Similaridade": None,
            })

        # Adiciona às listas de únicos
        if municipality_key not in seen_municipalities:
            if is_covered:
                in_scope.append(f"{cidade} ({uf})")
            else:
                out_of_scope.append(f"{cidade} ({uf})")
            seen_municipalities.add(municipality_key)

    # DEDUPLIFICAR listas (já foi feito via seen_municipalities)
    in_scope_unique = sorted(set(in_scope))
    out_of_scope_unique = sorted(set(out_of_scope))
    invalid_unique = sorted(set(invalid))

    # Calcular totais baseados em LINHAS (volumetria)
    total_linhas = len(detail)
    linhas_atendidas = sum(1 for d in detail if d["Status"] == "Atendido")
    linhas_nao_atendidas = sum(1 for d in detail if d["Status"] == "Não Atendido")
    linhas_invalidas = sum(1 for d in detail if d["Status"] == "Município Não Válido")

    # Calcular totais baseados em MUNICÍPIOS ÚNICOS (mantido para compatibilidade)
    total_municipios = len(in_scope_unique) + len(out_of_scope_unique) + len(invalid_unique)

    # Se não houver nenhuma linha, não analisa
    if total_linhas == 0:
        return {
            "total": 0,
            "total_linhas": 0,
            "in_scope": [],
            "out_of_scope": [],
            "invalid": [],
            "covered": 0,
            "not_covered": 0,
            "invalid_count": 0,
            "linhas_atendidas": 0,
            "linhas_nao_atendidas": 0,
            "linhas_invalidas": 0,
            "score": None,
            "detail": [],
        }

    # NOVO: Score baseado em LINHAS (volumetria), não municípios únicos
    score = round((linhas_atendidas / total_linhas) * 100.0, 2)

    # Ordena detail: não atendidos e inválidos primeiro, depois alfabético
    detail = sorted(
        detail,
        key=lambda r: (r["Status"] != "Não Atendido", r["Status"] != "Município Não Válido", r["UF"], r["Cidade"])
    )

    return {
        # Totais baseados em LINHAS (volumetria) - NOVO
        "total_linhas": total_linhas,
        "linhas_atendidas": linhas_atendidas,
        "linhas_nao_atendidas": linhas_nao_atendidas,
        "linhas_invalidas": linhas_invalidas,

        # Totais baseados em MUNICÍPIOS ÚNICOS (mantido para compatibilidade)
        "total": total_municipios,
        "in_scope": in_scope_unique,
        "out_of_scope": out_of_scope_unique,
        "invalid": invalid_unique,
        "covered": len(in_scope_unique),
        "not_covered": len(out_of_scope_unique),
        "invalid_count": len(invalid_unique),

        # Score por VOLUMETRIA
        "score": score,
        "detail": detail,
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
    debug_print(f"  Total: {m['total']} | Atendidos: {m.get('covered', 0)} | Não Atendidos: {m.get('not_covered', 0)} | Inválidos: {m.get('invalid_count', 0)}")
    debug_print(f"  Score: {m.get('score', 0)}% (Atendidos / Total)")
    if m.get("out_of_scope"):
        debug_print(f"  Não Atendidos: {', '.join(m['out_of_scope'][:5])}" +
              ("..." if len(m["out_of_scope"]) > 5 else ""))
    if m.get("invalid"):
        debug_print(f"  Inválidos (UF incorreta): {', '.join(m['invalid'][:5])}" +
              ("..." if len(m["invalid"]) > 5 else ""))

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
