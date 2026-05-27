"""
Teste final: Simular comportamento do app com arquivo Oxiteno
"""
from pathlib import Path
import idt_engine
import pandas as pd

print("="*70)
print("TESTE FINAL: SIMULACAO DO APP COM ARQUIVO OXITENO")
print("="*70)
print()

arquivo = Path("Respostas_Pre diagnóstico - IDT - TAX - v2_Oxiteno_Indorama 20_05_26.xlsx")
aderencia = Path("config/Aderencia.xlsm")

print("[1/2] Executando análise completa...")
print()

# Simula a chamada do app
result = idt_engine.run_analysis(str(arquivo), str(aderencia))

print("[2/2] Verificando resultados de municípios...")
print()

m = result["municipios"]
detail = m.get("detail", [])
total_unicos = m.get("total", 0)

print(f"METRICAS:")
print(f"  Score: {m['score']:.2f}%")
print(f"  Total de linhas no detail: {len(detail)}")
print(f"  Total de municipios unicos: {total_unicos}")
print(f"  Unicos cobertos: {m.get('covered', 0)}")
print(f"  Unicos nao cobertos: {m.get('not_covered', 0)}")
print()

# Simula o que o app vai exibir
print("MENSAGEM QUE APARECERA NO APP:")
print(f"  'Lista completa de TODAS as {len(detail)} linhas do pré-diagnóstico")
print(f"   ({total_unicos} municípios únicos) — cada linha marcada como Atendido")
print(f"   ou Não Atendido pela lista oficial de aderência do IDT.'")
print()

# Simula o DataFrame
rows = []
for r in detail:
    rows.append({
        "Município": r.get("Cidade", ""),
        "UF": r.get("UF", ""),
        "Status": r.get("Status", ""),
        "Modo de Match": r.get("Modo_Match") or "-",
        "Similaridade": r.get("Similaridade") if r.get("Similaridade") is not None else "-",
    })
df_mun = pd.DataFrame(rows)

print("DATAFRAME (primeiras 20 linhas):")
print(df_mun.head(20).to_string(index=False))
print()

print("DATAFRAME (ultimas 10 linhas):")
print(df_mun.tail(10).to_string(index=False))
print()

print("DISTRIBUICAO POR STATUS:")
print(df_mun["Status"].value_counts())
print()

print("DISTRIBUICAO POR UF (top 10):")
print(df_mun["UF"].value_counts().head(10))
print()

print("="*70)
print("CONCLUSAO:")
if len(detail) == 793:
    print("  SUCESSO: App vai mostrar todas as 793 linhas originais!")
    print(f"  Score de {m['score']:.2f}% calculado com base em {total_unicos} municipios unicos")
    print(f"  Usuario conseguira ver e filtrar todas as {len(detail)} linhas na tabela")
else:
    print(f"  PROBLEMA: Esperado 793 linhas, obtido {len(detail)}")
print("="*70)
