"""
Teste para validar calculo de score por volumetria (linhas)
"""

import pandas as pd
import sys
from idt_engine import analyse_municipios, normalize

# Cria DataFrame de teste simulando arquivo Oxiteno
test_data = pd.DataFrame({
    'Cidade': [
        'SAO PAULO',      # Servico 1
        'SAO PAULO',      # Servico 2
        'SAO PAULO',      # Servico 3
        'RIO DE JANEIRO', # Servico 1
        'RIO DE JANEIRO', # Servico 2
        'SALVADOR',       # Servico 1
        'RIBEIRAO PRETO', # UF invalida
        'ARACAJU',        # UF invalida
    ],
    'UF': [
        'SP',
        'SP',
        'SP',
        'RJ',
        'RJ',
        'BA',
        'NI',
        'NI',
    ]
})

# Base oficial
covered_dict = {
    (normalize('SAO PAULO'), 'SP'): True,
    (normalize('RIO DE JANEIRO'), 'RJ'): True,
    (normalize('SALVADOR'), 'BA'): True,
}

# Executar analise
result = analyse_municipios(test_data, covered_dict)

print("Teste: Score = (6 linhas atendidas / 8 linhas totais) x 100 = 75%")
print(f"Resultado: Score = {result['score']}%")
print(f"Total linhas: {result['total_linhas']}")
print(f"Linhas atendidas: {result['linhas_atendidas']}")
print(f"Linhas invalidas: {result['linhas_invalidas']}")

if result['score'] == 75.0:
    print("[OK] Teste passou!")
else:
    print("[FAIL] Teste falhou!")
