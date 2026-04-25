# IDT · Analisador de Aderência v2.0

Engine Python + app Streamlit que automatiza a análise de aderência do pré-diagnóstico IDT com **autenticação**, **histórico de análises** e **exportação PDF**.

---

## 🆕 Novidades v2.0

### ✅ Autenticação e Controle de Acesso
- Login seguro com usuário/senha
- Perfis de acesso (Admin, PM, Consultor)
- Sessões persistentes com cookies
- Logout seguro

### ✅ Histórico de Análises
- Banco de dados SQLite para armazenar análises
- Estatísticas por usuário (score médio, total de gaps, etc.)
- Visualização de análises anteriores
- Carregamento de resultados antigos

### ✅ Relatório PDF Executivo
- PDF visual com branding Thomson Reuters
- Resumo executivo com scores
- Principais achados destacados
- Tabelas de gaps e alertas
- Pronto para enviar ao cliente

### ✅ Análise de CFOPs
- Extração automática de CFOPs do pré-diagnóstico
- Cruzamento com operações não-standard
- Alertas visuais para customizações necessárias
- Score de aderência de CFOPs

### ✅ Deploy Ready
- Configuração para Streamlit Cloud
- Guia completo de deploy
- Suporte a Azure App Service
- Secrets management

---

## Estrutura dos arquivos

```
idt_analyzer/
├── app.py                  ← Interface Streamlit com autenticação
├── idt_engine.py           ← Engine de análise (importável ou CLI)
├── db_manager.py           ← Gerenciador de banco de dados SQLite
├── pdf_generator.py        ← Gerador de PDF executivo
├── config_auth.yaml        ← Configuração de usuários e senhas
├── generate_password.py    ← Utilitário para gerar hashes de senha
├── requirements.txt        ← Dependências Python
├── .streamlit/
│   ├── config.toml        ← Configurações do Streamlit
│   └── secrets.toml.example ← Exemplo de secrets
├── README.md              ← Este arquivo
├── GUIA_TESTE.md          ← Guia para testar localmente
└── DEPLOY.md              ← Guia de deploy em produção
```

---

## Instalação

### Pré-requisitos
- Python 3.10 ou superior ([baixar aqui](https://www.python.org/downloads/))

### Instalar dependências
```bash
pip install -r requirements.txt
```

---

## Como usar

### 1. Configurar autenticação (primeira vez)

Gere hashes de senha para os usuários:
```bash
python generate_password.py
```

Isso mostrará os hashes das senhas padrão. Copie os hashes para `config_auth.yaml`.

**⚠️ IMPORTANTE**: Altere as senhas padrão em produção!

### 2. Interface visual (recomendado)
```bash
streamlit run app.py
```

Faça login com:
- **admin** / **admin123**
- **pm1** / **pm123**
- **consultor1** / **cons123**

### 3. Linha de comando (sem autenticação)
```bash
python idt_engine.py "PreDiagnostico_Cliente.xlsx" "Aderencia.xlsm"
```

---

## Funcionalidades

### 🔍 Nova Análise
1. Faça login na aplicação
2. Upload do pré-diagnóstico do cliente (`.xlsx` ou `.xlsm`)
3. Upload da base de aderência (`Aderencia.xlsm`)
4. Clique em "Analisar Aderência"
5. Visualize os resultados:
   - **Scores** consolidados por dimensão
   - **NCM Compras/Vendas** com gaps detalhados
   - **Municípios ISS** dentro/fora do escopo
   - **⚠️ Alertas de CFOPs** não-standard
   - **CSTs** por tributo
6. Baixe os relatórios:
   - **Excel**: todas as abas com dados completos
   - **PDF**: relatório executivo visual

### 📊 Histórico
- Acesse suas análises anteriores
- Visualize estatísticas (score médio, total de gaps)
- Recarregue análises antigas para visualização completa

### ⚙️ Configurações
- Informações da conta
- Gerenciamento de dados
- Sobre a aplicação

---

## Lógica de cruzamento NCM × UF

| Operação | UF usada no cruzamento |
|----------|------------------------|
| **Compras** | UF do **fornecedor** (coluna `UF Fornecedor` do pré-diagnóstico) |
| **Vendas**  | UF do **cliente / destino** (coluna `UF Cliente` do pré-diagnóstico) |

A cobertura é lida da planilha de aderência no formato:

```
COMMODITY_CODE | SP | AC | AL | AM | AP | BA | ... | TO
1301.20.00     | 100| 100| 100| 100| 100| 100| ... | 100
```

Valor `100` = coberto. Qualquer outro valor (0, NaN) = gap.

**Resultado por NCM:** score consolidado (% de pares cobertos) + detalhe das UFs com gap.

---

## Seleção automática de setor

O engine lê o campo **"Em qual segmento sua empresa se enquadra?"** do pré-diagnóstico
e mapeia para a aba de aderência correta:

| Keyword no segmento | Aba Inbound | Aba Outbound |
|---------------------|-------------|--------------|
| quím / chemical | Chemical - Inbound | Chemical - Oubound |
| farm / pharma | Pharma - Inbound | Pharma - Outbound |
| agro / agric / AWR | AWR | AWR |
| consum / varejo / aliment | CG&Freigth | CG&Freigth |
| *(outros)* | Chemical - Inbound | Chemical - Oubound |

---

## Municípios ISS

Compara cada município da lista do cliente contra os **834 municípios cobertos** 
(`Cfg_Municipios_Cobertos`). Os que não constam são listados como **"Fora do Escopo"** 
— decisão de tratamento fica com o time.

---

## CFOPs e Operações Não-Standard

O engine extrai todos os CFOPs declarados pelo cliente nas abas de NCM Compras e Vendas,
e cruza com a lista de **operações não-standard** (`Cfg_Operacoes_NaoStandard`).

CFOPs que aparecem na lista de "não atendidas" geram **alertas automáticos** indicando
que essas operações requerem customização do IDT.

---

## Output

### No app Streamlit
- Score cards visuais (Geral, NCM Compras, NCM Vendas, Municípios ISS, CFOPs)
- Tabela de cobertura por UF com barra de progresso
- Lista de gaps NCM×UF com detalhe
- Lista de municípios dentro / fora do escopo
- **⚠️ Alertas de CFOPs não-standard** com detalhamento
- Cobertura de CSTs por tributo
- **Histórico** de análises anteriores
- **Estatísticas** por usuário

### Relatório Excel baixável
- Aba **Resumo Executivo** — todos os scores e metadados (inclui CFOPs)
- Aba **NCM Compras por UF** — cobertura por estado
- Aba **NCM Vendas por UF** — cobertura por estado  
- Aba **Gaps NCM Compras** — lista de pares sem cobertura
- Aba **Gaps NCM Vendas** — lista de pares sem cobertura
- Aba **Municípios ISS** — dentro/fora do escopo
- Aba **Alertas CFOPs** — operações não-standard que requerem customização
- Aba **CFOPs Declarados** — lista completa com status (standard/não-standard)

### Relatório PDF executivo (NOVO!)
- **Página 1**: Capa com informações do cliente
- **Resumo Executivo**: tabela de scores com status visual
- **Principais Achados**: highlights dos gaps e alertas
- **Detalhamento de NCM**: tabelas de gaps por operação
- **Alertas de CFOPs**: operações que requerem customização
- **Footer**: branding Thomson Reuters

---

## Autenticação

### Usuários padrão (DEV/TEST)

| Usuário | Senha | Perfil | Email |
|---------|-------|--------|-------|
| admin | admin123 | Admin | admin@thomsonreuters.com |
| pm1 | pm123 | PM | pm1@thomsonreuters.com |
| consultor1 | cons123 | Consultor | consultor1@thomsonreuters.com |

**⚠️ CRÍTICO**: Altere essas senhas antes de ir para produção!

### Gerenciar usuários

1. Edite `config_auth.yaml`:
```yaml
credentials:
  usernames:
    novo_usuario:
      email: usuario@email.com
      name: Nome do Usuário
      password: $2b$12$[HASH_DA_SENHA]
      role: consultor
```

2. Gere hash de senha:
```bash
python generate_password.py
```

3. Reinicie o app

---

## Banco de dados

### SQLite (padrão)
- Arquivo: `idt_history.db`
- Criado automaticamente na primeira execução
- Armazena:
  - Histórico de análises
  - Scores e metadados
  - Resultados completos (JSON)

### Schema
```sql
CREATE TABLE analyses (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    usuario TEXT,
    cliente_nome TEXT,
    score_geral REAL,
    score_ncm_compras REAL,
    score_ncm_vendas REAL,
    score_municipios REAL,
    score_cfops REAL,
    gaps_compras INTEGER,
    gaps_vendas INTEGER,
    cfops_nao_standard INTEGER,
    resultado_json TEXT,
    arquivo_prediag TEXT,
    arquivo_aderencia TEXT
);
```

### Backup
```bash
# Backup manual
cp idt_history.db idt_history_backup_$(date +%Y%m%d).db

# Restaurar
cp idt_history_backup_20240424.db idt_history.db
```

---

## Deploy

Ver guia completo em **[DEPLOY.md](DEPLOY.md)**

### Quick start - Streamlit Cloud

1. Push para GitHub (repositório **private**)
2. Acesse https://share.streamlit.io/
3. Conecte o repositório
4. Configure branch `main` e arquivo `app.py`
5. Deploy!

---

## Desenvolvimento

### Estrutura de módulos

- **idt_engine.py**: Core de análise (pode ser usado standalone)
- **db_manager.py**: Camada de persistência (SQLite)
- **pdf_generator.py**: Geração de PDF com reportlab
- **app.py**: Interface Streamlit (orquestra tudo)

### Adicionar nova análise

1. Implementar função em `idt_engine.py`:
```python
def analyse_new_dimension(data, base):
    # lógica de análise
    return {
        "score": 95.5,
        "details": [...]
    }
```

2. Integrar em `run_analysis()`:
```python
new_result = analyse_new_dimension(diag["data"], base["config"])
return {
    ...
    "new_dimension": new_result
}
```

3. Adicionar visualização em `app.py`:
```python
st.markdown("### Nova Dimensão")
st.metric("Score", f"{result['new_dimension']['score']}%")
```

4. Adicionar no relatório Excel/PDF

---

## Testes

### Teste local completo
```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Gerar senhas
python generate_password.py

# 3. Rodar app
streamlit run app.py

# 4. Testar:
#    - Login
#    - Nova análise
#    - Download Excel/PDF
#    - Histórico
```

### Teste do engine standalone
```bash
python idt_engine.py "Pre Diagnóstico IDT 2025 Trimble_280425_v2_conteudo.xlsx" "Aderencia.xlsm"
```

### Teste do banco de dados
```bash
python db_manager.py
```

---

## Troubleshooting

### Erro: "Module not found"
```bash
pip install -r requirements.txt
```

### Erro: "config_auth.yaml not found"
- Execute `python generate_password.py`
- Crie o arquivo com base no exemplo

### Banco de dados corrupto
```bash
rm idt_history.db
# DB será recriado na próxima execução
```

### Upload falha
- Verifique limite de tamanho em `.streamlit/config.toml`
- Padrão: 200MB

---

## Roadmap futuro

- [ ] Integração com API do IDT (dados em tempo real)
- [ ] Dashboard de analytics agregado (admin)
- [ ] Comparação de análises side-by-side
- [ ] Exportação para PowerPoint
- [ ] Notificações por email de análises concluídas
- [ ] Multi-tenancy (separação por empresa)
- [ ] Integração com Azure AD / SSO
- [ ] App mobile (visualização de resultados)

---

## Contribuindo

1. Fork o repositório
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Add: nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra Pull Request

---

## Licença

**Propriedade de Thomson Reuters**

Uso interno apenas. Não distribuir fora da organização.

---

## Suporte

- **Documentação**: Ver arquivos `*.md` no repositório
- **Issues**: Abra issue no repositório interno
- **Contato**: [Seu email/time]

---

**Thomson Reuters | 2024**
**IDT Analyzer v2.0**
