"""
Diagnostico: passar o caminho do arquivo de pre-diagnostico do cliente.
Mostra exatamente onde as linhas de municipios estao sendo perdidas.

Uso:
    python diagnosticar_municipios.py "caminho/do/arquivo.xlsx"
"""
import sys
from pathlib import Path
import pandas as pd
import idt_engine

# Reset modo de log para mostrar tudo
idt_engine.QUIET_MODE = False


def safe_print(s):
    """Imprime tratando encoding do terminal Windows."""
    print(str(s).encode("ascii", "replace").decode())


def main():
    if len(sys.argv) < 2:
        print("Uso: python diagnosticar_municipios.py <arquivo.xlsx>")
        sys.exit(1)

    arquivo = Path(sys.argv[1])
    if not arquivo.exists():
        print(f"ERRO: arquivo nao encontrado: {arquivo}")
        sys.exit(1)

    safe_print("=" * 70)
    safe_print(f"DIAGNOSTICO DE MUNICIPIOS - {arquivo.name}")
    safe_print("=" * 70)
    safe_print("")

    # 1. Listar TODAS as sheets
    xl = pd.ExcelFile(arquivo, engine="openpyxl")
    sheets = xl.sheet_names
    safe_print(f"[1/5] Sheets encontradas no arquivo: {len(sheets)}")
    for s in sheets:
        df_count = pd.read_excel(arquivo, sheet_name=s, engine="openpyxl", header=None)
        safe_print(f"   - '{s}' ({len(df_count)} linhas, {len(df_count.columns)} colunas)")
    safe_print("")

    # 2. Detectar qual sheet o sistema escolhe
    safe_print(f"[2/5] Detectando sheet de municipios via load_prediag...")
    diag = idt_engine.load_prediag(arquivo)
    mun_df = diag.get("municipios_cliente")
    if mun_df is None or mun_df.empty:
        safe_print("ERRO: load_prediag NAO conseguiu extrair municipios!")
        safe_print(f"   Sheets detectadas pelo sistema: {diag.get('_debug_sheets', {})}")
        sys.exit(1)
    safe_print(f"   load_prediag retornou {len(mun_df)} linhas extraidas")
    safe_print("")

    # 3. Mostrar amostra do que foi extraido
    safe_print(f"[3/5] Amostra dos dados extraidos (primeiras 5 e ultimas 5 linhas):")
    safe_print("   Primeiras 5:")
    for _, row in mun_df.head(5).iterrows():
        safe_print(f"      UF={row['UF']!r:8s}  Cidade={row['Cidade']!r}")
    safe_print("   Ultimas 5:")
    for _, row in mun_df.tail(5).iterrows():
        safe_print(f"      UF={row['UF']!r:8s}  Cidade={row['Cidade']!r}")
    safe_print("")

    # 4. Analisar contra a base
    safe_print(f"[4/5] Carregando base de aderencia e analisando...")
    base = idt_engine.load_adherence_base(Path("config/Aderencia.xlsm"))
    resultado = idt_engine.analyse_municipios(mun_df, base["municipios"])
    safe_print("")

    # 5. Resultado final + diagnostico
    safe_print(f"[5/5] RESULTADO FINAL:")
    safe_print(f"   Total analisado (unicos): {resultado['total']}")
    safe_print(f"   Cobertos: {resultado.get('covered')}")
    safe_print(f"   Nao cobertos: {resultado.get('not_covered')}")
    safe_print(f"   Score: {resultado.get('score')}%")
    safe_print("")
    safe_print(f"   Diagnostico passo-a-passo:")
    for k, v in resultado.get("diagnostico", {}).items():
        safe_print(f"      {k}: {v}")

    safe_print("")
    if resultado.get("fuzzy_matches"):
        safe_print(f"   Matches fuzzy (similaridade < 1.0): {len(resultado['fuzzy_matches'])}")
        for fm in resultado["fuzzy_matches"][:10]:
            safe_print(f"      ~ {fm['input']} -> {fm['matched']} ({fm['similarity']})")

    safe_print("")
    safe_print("=" * 70)
    safe_print("CONCLUSAO:")
    extraidos = len(mun_df)
    final = resultado["total"]
    if extraidos == final:
        safe_print(f"OK: Todos os {extraidos} municipios extraidos foram analisados.")
    else:
        perdidos = extraidos - final
        diagnostico = resultado.get("diagnostico", {})
        safe_print(f"PERDA: De {extraidos} extraidos, apenas {final} chegaram ao resultado.")
        safe_print(f"       Perdeu {perdidos} no caminho:")
        safe_print(f"       - vazias: {diagnostico.get('vazias', 0)}")
        safe_print(f"       - UF invalida: {diagnostico.get('uf_invalida', 0)}")
        safe_print(f"       - cidade < 3 chars: {diagnostico.get('cidade_muito_curta', 0)}")
        safe_print(f"       - placeholders: {diagnostico.get('placeholder', 0)}")
        safe_print(f"       - duplicatas (colapsadas no dedup): {diagnostico.get('duplicatas_colapsadas', 0)}")


if __name__ == "__main__":
    main()
