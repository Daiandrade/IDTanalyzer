"""
Teste: Verificar se todas as 793 linhas aparecem no detail
"""
from pathlib import Path
import idt_engine

print("="*70)
print("TESTE: DETAIL COM TODAS AS LINHAS")
print("="*70)
print()

arquivo = Path("Respostas_Pre diagnóstico - IDT - TAX - v2_Oxiteno_Indorama 20_05_26.xlsx")

print("[1/3] Carregando arquivo...")
diag = idt_engine.load_prediag(arquivo)
mun_df = diag.get("municipios_cliente")
print(f"Total de linhas extraidas: {len(mun_df)}")
print()

print("[2/3] Carregando base de aderencia...")
base = idt_engine.load_adherence_base(Path("config/Aderencia.xlsm"))
print()

print("[3/3] Analisando municipios...")
resultado = idt_engine.analyse_municipios(mun_df, base["municipios"])
print()

print("RESULTADOS:")
print(f"  Total de linhas no detail: {len(resultado.get('detail', []))}")
print(f"  Total de municipios unicos: {resultado.get('total')}")
print(f"  Municipios cobertos: {resultado.get('covered')}")
print(f"  Municipios nao cobertos: {resultado.get('not_covered')}")
print(f"  Score: {resultado.get('score')}%")
print()

detail = resultado.get('detail', [])
if len(detail) > 0:
    print("Primeiras 10 linhas do detail:")
    for i, r in enumerate(detail[:10]):
        print(f"  {i+1}. {r['Cidade']} ({r['UF']}) - {r['Status']} - Match: {r['Modo_Match']}")
    print()

    print("Ultimas 10 linhas do detail:")
    for i, r in enumerate(detail[-10:], start=len(detail)-9):
        print(f"  {i}. {r['Cidade']} ({r['UF']}) - {r['Status']} - Match: {r['Modo_Match']}")
    print()

# Verificar quantas linhas unicas por municipio
from collections import Counter
cidade_counts = Counter(f"{r['Cidade']} ({r['UF']})" for r in detail)
print("Top 10 municipios com mais linhas:")
for cidade, count in cidade_counts.most_common(10):
    print(f"  {cidade}: {count} linhas")

print()
print("="*70)
if len(detail) == len(mun_df):
    print("SUCESSO: Detail contem TODAS as 793 linhas originais!")
else:
    print(f"PROBLEMA: Detail tem {len(detail)} linhas, esperado {len(mun_df)}")
print("="*70)
