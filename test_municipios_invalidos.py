"""
Teste para validar a análise de municípios incluindo inválidos
"""

import pandas as pd
import sys

# Simula a função normalize
def normalize(s):
    import unicodedata
    s = str(s).lower().strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()

# Cria DataFrame de teste com municípios válidos e inválidos
test_data = pd.DataFrame({
    'Cidade': [
        'SAO PAULO',
        'SAO PAULO',  # Duplicata
        'RIO DE JANEIRO',
        'SALVADOR',
        'BARUERI',
        'CIDADE FAKE',  # Não existe na base
        'RIBEIRAO PRETO',  # UF inválida (NI)
        'ARACAJU',  # UF inválida (NI)
        'CAMPO GRANDE',  # UF inválida (NI)
        'CURITIBA',  # UF válida
    ],
    'UF': [
        'SP',
        'SP',  # Duplicata
        'RJ',
        'BA',
        'SP',
        'SP',
        'NI',  # INVÁLIDO
        'NI',  # INVÁLIDO
        'NI',  # INVÁLIDO
        'PR',
    ]
})

# Simula base oficial (apenas alguns municípios para teste)
covered_dict = {
    (normalize('SAO PAULO'), 'SP'): True,
    (normalize('RIO DE JANEIRO'), 'RJ'): True,
    (normalize('SALVADOR'), 'BA'): True,
    (normalize('BARUERI'), 'SP'): True,
    (normalize('CURITIBA'), 'PR'): True,
    # RIBEIRAO PRETO, ARACAJU, CAMPO GRANDE não estão na base (mas deveriam)
    # CIDADE FAKE nunca existiu
}

# Importa função do idt_engine
sys.path.insert(0, '.')
from idt_engine import analyse_municipios

# Executa análise
result = analyse_municipios(test_data, covered_dict)

# Exibe resultados
print("=" * 60)
print("TESTE DE MUNICÍPIOS COM VALORES INVÁLIDOS")
print("=" * 60)
print()
print("ENTRADA:")
print(f"  Total de linhas: {len(test_data)}")
print(f"  Municípios únicos esperados: 7 (2 duplicatas)")
print()

print("RESULTADO:")
print(f"  Total municípios únicos: {result['total']}")
print(f"  Atendidos: {result['covered']}")
print(f"  Não Atendidos: {result['not_covered']}")
print(f"  Inválidos (UF incorreta): {result['invalid_count']}")
print(f"  Score: {result['score']}%")
print()

print("ATENDIDOS (in_scope):")
for cidade in result['in_scope']:
    print(f"  [OK] {cidade}")
print()

print("NAO ATENDIDOS (out_of_scope):")
for cidade in result['out_of_scope']:
    print(f"  [X] {cidade}")
print()

print("INVALIDOS (UF incorreta):")
for cidade in result['invalid']:
    print(f"  [!] {cidade}")
print()

print("DETALHE (todas as linhas):")
for i, item in enumerate(result['detail'], 1):
    status_icon = "[OK]" if item['Status'] == "Atendido" else "[!]" if item['Status'] == "Municipio Nao Valido" else "[X]"
    print(f"  {i}. {status_icon} {item['Cidade']} ({item['UF']}) - {item['Status']}")
print()

print("=" * 60)
print("VALIDAÇÃO:")
print("=" * 60)

# Validações
expected_total = 9  # 10 linhas - 1 duplicata (SAO PAULO) = 9 únicos
expected_covered = 5  # SAO PAULO, RIO DE JANEIRO, SALVADOR, BARUERI, CURITIBA = 5
expected_not_covered = 1  # CIDADE FAKE (SP)
expected_invalid = 3  # RIBEIRAO PRETO (NI), ARACAJU (NI), CAMPO GRANDE (NI)

# Score = (5 / 9) * 100 = 55.56%
expected_score = round((expected_covered / expected_total) * 100, 2)

tests_passed = 0
tests_total = 5

if result['total'] == expected_total:
    print(f"[OK] Total correto: {result['total']} == {expected_total}")
    tests_passed += 1
else:
    print(f"[FAIL] Total incorreto: {result['total']} != {expected_total}")

if result['covered'] == expected_covered:
    print(f"[OK] Atendidos correto: {result['covered']} == {expected_covered}")
    tests_passed += 1
else:
    print(f"[FAIL] Atendidos incorreto: {result['covered']} != {expected_covered}")

if result['not_covered'] == expected_not_covered:
    print(f"[OK] Nao Atendidos correto: {result['not_covered']} == {expected_not_covered}")
    tests_passed += 1
else:
    print(f"[FAIL] Nao Atendidos incorreto: {result['not_covered']} != {expected_not_covered}")

if result['invalid_count'] == expected_invalid:
    print(f"[OK] Invalidos correto: {result['invalid_count']} == {expected_invalid}")
    tests_passed += 1
else:
    print(f"[FAIL] Invalidos incorreto: {result['invalid_count']} != {expected_invalid}")

if result['score'] == expected_score:
    print(f"[OK] Score correto: {result['score']}% == {expected_score}%")
    tests_passed += 1
else:
    print(f"[FAIL] Score incorreto: {result['score']}% != {expected_score}%")

print()
print(f"RESULTADO: {tests_passed}/{tests_total} testes passaram")
print()

if tests_passed == tests_total:
    print("*** TODOS OS TESTES PASSARAM ***")
    sys.exit(0)
else:
    print("*** ALGUNS TESTES FALHARAM ***")
    sys.exit(1)
