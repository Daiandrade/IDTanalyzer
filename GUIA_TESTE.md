# Guia Rápido de Teste — IDT Analisador de Aderência

## 📋 Pré-requisitos

1. **Python 3.10+** instalado
   - Verificar: abra o terminal e digite `python --version`
   - Se não tiver, baixe em: https://www.python.org/downloads/
   - ⚠️ Durante a instalação, marque "Add Python to PATH"

## 🚀 Passo a Passo

### 1. Instalar dependências

Abra o terminal na pasta do projeto e execute:

```bash
pip install -r requirements.txt
```

### 2. Testar via linha de comando (opcional)

Para um teste rápido sem interface, execute:

```bash
python idt_engine.py
```

Isso vai processar os arquivos default e mostrar um resumo no terminal.

### 3. Rodar a interface Streamlit (recomendado)

```bash
streamlit run app.py
```

O navegador deve abrir automaticamente em `http://localhost:8501`

### 4. Usar a aplicação

1. **Fazer upload dos arquivos:**
   - Pré-Diagnóstico do cliente (`.xlsx` ou `.xlsm`)
   - Base de Aderência (`Aderencia.xlsm`)

2. **Clicar em "▶ Analisar Aderência"**

3. **Visualizar resultados:**
   - **Score Geral** — aderência consolidada
   - **NCM Compras/Vendas** — cobertura por UF com gaps detalhados
   - **Municípios ISS** — dentro/fora do escopo (834 cobertos)
   - **⚠️ CFOPs** — alertas de operações não-standard que requerem customização
   - **CSTs** — cobertura por tributo

4. **Baixar relatório Excel** com todas as abas consolidadas

## 🔍 O que foi implementado (novo!)

### Análise de CFOPs ✅
- Extração automática de CFOPs das abas de NCM Compras e Vendas
- Cruzamento com lista de operações não-standard (`Cfg_Operacoes_NaoStandard`)
- **Alertas automáticos** para CFOPs que requerem customização
- Score de aderência de CFOPs (% standard vs. não-standard)
- Visualização destacada na interface e no relatório Excel

### Relatório Excel atualizado
Novas abas:
- **Alertas CFOPs** — lista de operações não-standard
- **CFOPs Declarados** — todos os CFOPs com status

## ❓ Troubleshooting

### Erro: "Python was not found"
- Instale Python 3.10+ e marque "Add to PATH" durante instalação
- Ou use o caminho completo: `C:\Python310\python.exe app.py`

### Erro ao importar pandas/openpyxl/streamlit
```bash
pip install --upgrade pandas openpyxl streamlit
```

### Porta 8501 já está em uso
```bash
streamlit run app.py --server.port 8502
```

### Planilha não é reconhecida
- Verifique se o arquivo tem as abas esperadas:
  - Pré-diagnóstico: `Lista NCM Compras - POR`, `Lista NCM Vendas - POR`
  - Aderência: abas de setor (Chemical, Pharma, AWR, CG&Freigth)

## 📊 Estrutura esperada das planilhas

### Pré-Diagnóstico
Deve conter:
- `Informações Gerais - POR` → segmento, estados, volumetria
- `Lista NCM Compras - POR` → NCM, UF Fornecedor, **CFOP** (opcional)
- `Lista NCM Vendas - POR` → NCM, UF Cliente, **CFOP** (opcional)
- `Lista Municípios&Serviços - POR` → cidades/estados

### Base de Aderência
Deve conter:
- Abas de setor com matriz NCM × UF (valor 100 = coberto)
- `Cfg_Municipios_Cobertos` → 834 municípios
- `Cfg_CSTs` → cobertura de CSTs por tributo
- `Cfg_Operacoes_NaoStandard` → CFOPs não atendidos

## 📝 Notas importantes

- **CFOPs são opcionais** no pré-diagnóstico. Se não existir coluna CFOP, a análise ignora essa dimensão.
- O engine detecta automaticamente o setor (Chemical, Pharma, AWR, CG&Freigth) baseado no campo "segmento"
- Score Geral = 35% NCM Compras + 35% NCM Vendas + 30% Municípios
- Municípios fora do escopo **não afetam negativamente** o score — são apenas listados para decisão do time

## 🎯 Validação dos resultados

1. Verifique se o **setor detectado** está correto (Chemical/Pharma/AWR/CG&Freigth)
2. Confira se as **UFs dos gaps** fazem sentido (compras = UF fornecedor, vendas = UF cliente)
3. Revise os **alertas de CFOP** — confirme se são realmente operações não-standard
4. Valide os **municípios fora do escopo** — podem existir grafias diferentes

---

**Em caso de dúvidas ou bugs, documente:**
- Mensagem de erro completa
- Arquivos usados (sem dados sensíveis)
- Passos para reproduzir o problema
