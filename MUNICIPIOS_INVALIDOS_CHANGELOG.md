# Changelog: Análise de Municípios Incluindo UFs Inválidas

## Resumo da Mudança

A análise de municípios agora **INCLUI municípios com UF inválida** no cálculo de aderência, ao invés de descartá-los silenciosamente.

## Motivação

No arquivo da Oxiteno, **88 municípios (54%)** tinham `UF="NI"` (Não Informado) e estavam sendo descartados da análise. Isso distorcia o score de aderência real.

## Alterações no `idt_engine.py`

### 1. Nova Categoria de Status

**Antes**: 2 status
- `"Atendido"` - Município encontrado na base oficial (834 cidades)
- `"Não Atendido"` - Município com UF válida mas não encontrado na base

**Depois**: 3 status
- `"Atendido"` - Município encontrado na base oficial (834 cidades)
- `"Não Atendido"` - Município com UF válida mas não encontrado na base
- `"Município Não Válido"` - **NOVO**: Município com UF inválida (ex: "NI", "NA")

### 2. Novo Cálculo de Score

**Antes**:
```
Score = (Atendidos / Total) × 100
Total = Municípios com UF válida apenas
```

**Depois**:
```
Score = (Atendidos / Total) × 100
Total = TODOS os municípios (válidos + inválidos)
```

### 3. Novos Campos no Retorno

```python
{
    "total": 161,                 # Total de municípios únicos (TODOS)
    "covered": 73,                # Atendidos
    "not_covered": 0,             # Não Atendidos
    "invalid_count": 88,          # NOVO: Municípios com UF inválida
    "score": 45.34,               # % considerando TODOS
    "in_scope": [...],            # Lista de atendidos
    "out_of_scope": [...],        # Lista de não atendidos
    "invalid": [...],             # NOVO: Lista de inválidos
    "detail": [...]               # NOVO: TODAS as linhas com status
}
```

### 4. Campo `detail` para Frontend

**NOVO**: Array com TODAS as linhas do arquivo (sem deduplicação), cada uma com status detalhado:

```python
"detail": [
    {
        "Cidade": "RIBEIRAO PRETO",
        "Cidade_Cliente": "RIBEIRAO PRETO",
        "UF": "NI",                          # UF inválida original
        "Coberto": False,
        "Status": "Município Não Válido",   # NOVO status
        "Modo_Match": None,
        "Similaridade": None
    },
    {
        "Cidade": "SAO PAULO",
        "Cidade_Cliente": "SAO PAULO",
        "UF": "SP",
        "Coberto": True,
        "Status": "Atendido",
        "Modo_Match": "exact",
        "Similaridade": 1.0
    },
    # ... mais linhas
]
```

### 5. Correção de Bug em Placeholders

**Problema**: Municípios reais como "Cidade Ocidental (GO)" estavam sendo ignorados como placeholders.

**Solução**: Removida lógica `startswith()`, usa apenas match EXATO em PLACEHOLDERS.

## Exemplo: Arquivo Oxiteno

### Antes da Mudança
```
Total: 73 municípios (descartou 88 com UF="NI")
Atendidos: 73
Não Atendidos: 0
Score: 100%  ❌ INCORRETO - ignora 88 inválidos
```

### Depois da Mudança
```
Total: 161 municípios (TODOS)
Atendidos: 73
Não Atendidos: 0
Inválidos: 88
Score: 45.34%  ✅ CORRETO - reflete realidade
```

## Impacto no Frontend

### Exibição Recomendada

1. **Card de Score Geral**
   ```
   Score de Aderência: 45.34%
   
   ✓ Atendidos: 73 (45%)
   ✗ Não Atendidos: 0 (0%)
   ⚠ Inválidos: 88 (55%)
   ```

2. **Tabela Detalhada** (use o campo `detail`)
   ```
   | Município          | UF | Status                  |
   |--------------------|----|-----------------------  |
   | Ribeirao Preto     | NI | ⚠ Município Não Válido |
   | Aracaju            | NI | ⚠ Município Não Válido |
   | São Paulo          | SP | ✓ Atendido             |
   | Cidade Fake        | SP | ✗ Não Atendido         |
   ```

3. **Alertas**
   ```
   ⚠ ATENÇÃO: 88 municípios (55%) possuem UF inválida ou não informada.
   Recomenda-se revisar o arquivo para corrigir estas UFs.
   ```

## Teste de Validação

Arquivo: `test_municipios_invalidos.py`

**Resultado**: ✅ 5/5 testes passaram

- Total: 9 únicos ✓
- Atendidos: 5 ✓
- Não Atendidos: 1 ✓
- Inválidos: 3 ✓
- Score: 55.56% ✓

## Compatibilidade

✅ **Backward Compatible**: Arquivos sem UF inválida funcionam como antes.

✅ **Novos campos opcionais**: `invalid`, `invalid_count`, `detail` não quebram código existente.

## Deployment

1. Substituir `idt_engine.py` pela versão no worktree `municipios-invalidos-fix`
2. Atualizar frontend para exibir os 3 status (Atendido, Não Atendido, Município Não Válido)
3. Usar campo `detail` para exibir tabela completa com todas as linhas
4. Adicionar alerta visual quando `invalid_count > 0`

## Arquivos Modificados

- `idt_engine.py` (função `analyse_municipios`)
- Saída CLI (exibe inválidos)

## Próximos Passos para Frontend

1. Criar badges para os 3 status
2. Adicionar filtro por status na tabela de municípios
3. Permitir exportar lista de inválidos para correção
4. Adicionar sugestão automática de UF (se possível via geocoding)
