# 🚀 IDT Analyzer v2.0 - Comece Aqui!

Bem-vindo ao **IDT Analyzer v2.0** - versão completa com autenticação, histórico e exportação PDF.

---

## ✅ O que foi implementado

### 1️⃣ Autenticação e Controle de Acesso
- ✅ Login seguro com usuário/senha
- ✅ 3 perfis de usuário (Admin, PM, Consultor)
- ✅ Gerenciamento de credenciais via `config_auth.yaml`
- ✅ Sessões persistentes com cookies

### 2️⃣ Histórico de Análises
- ✅ Banco de dados SQLite (`idt_history.db`)
- ✅ Salvamento automático de todas as análises
- ✅ Visualização de análises anteriores
- ✅ Estatísticas por usuário (score médio, gaps, alertas)
- ✅ Carregamento de resultados antigos

### 3️⃣ Relatório PDF Executivo
- ✅ Geração de PDF visual com branding
- ✅ Resumo executivo com scores coloridos
- ✅ Principais achados destacados
- ✅ Tabelas de gaps NCM×UF
- ✅ Alertas de CFOPs não-standard
- ✅ Pronto para enviar ao cliente

### 4️⃣ Análise de CFOPs (da v1.0)
- ✅ Extração automática de CFOPs
- ✅ Cruzamento com operações não-standard
- ✅ Alertas visuais para customizações
- ✅ Score de aderência

### 5️⃣ Deploy Ready
- ✅ Configuração para Streamlit Cloud
- ✅ Suporte a Azure App Service
- ✅ Secrets management
- ✅ Documentação completa

---

## 🎯 Próximos passos (você escolhe a ordem!)

### Opção 1: Testar localmente primeiro ⭐ RECOMENDADO

```bash
# 1. Instalar Python 3.10+
#    https://www.python.org/downloads/

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Gerar hashes de senha
python generate_password.py

# 4. Copiar os hashes para config_auth.yaml
#    (já tem um arquivo base, basta atualizar os hashes)

# 5. Rodar o app
streamlit run app.py

# 6. Abrir http://localhost:8501
#    Login: admin / admin123
```

📖 **Guia completo**: [GUIA_TESTE.md](GUIA_TESTE.md)

### Opção 2: Deploy direto para produção

```bash
# 1. Criar repositório Git privado
git init
git add .
git commit -m "IDT Analyzer v2.0"

# 2. Push para GitHub
git remote add origin https://github.com/SEU_USUARIO/idt-analyzer.git
git push -u origin main

# 3. Deploy no Streamlit Cloud
#    - Acesse https://share.streamlit.io/
#    - Conecte o repositório
#    - Deploy!
```

📖 **Guia completo**: [DEPLOY.md](DEPLOY.md)

### Opção 3: Revisar o código

**Arquivos principais:**
- [app.py](app.py) — Interface Streamlit com autenticação (550 linhas)
- [idt_engine.py](idt_engine.py) — Core de análise (550 linhas)
- [db_manager.py](db_manager.py) — Banco de dados SQLite (230 linhas)
- [pdf_generator.py](pdf_generator.py) — Gerador de PDF (400 linhas)

---

## 📂 Estrutura de arquivos

```
idt-analyzer/
├── 📱 APLICAÇÃO
│   ├── app.py                      ← Streamlit app principal
│   ├── idt_engine.py               ← Engine de análise
│   ├── db_manager.py               ← Banco de dados
│   └── pdf_generator.py            ← Gerador de PDF
│
├── ⚙️ CONFIGURAÇÃO
│   ├── config_auth.yaml            ← Usuários e senhas
│   ├── generate_password.py       ← Gerar hashes de senha
│   ├── requirements.txt            ← Dependências
│   └── .streamlit/
│       ├── config.toml             ← Config do Streamlit
│       └── secrets.toml.example    ← Exemplo de secrets
│
├── 📊 DADOS (gerados em runtime)
│   ├── idt_history.db              ← Banco SQLite (criado automaticamente)
│   ├── Aderencia.xlsm              ← Base de cobertura IDT
│   └── Pre Diagnóstico*.xlsx       ← Pré-diagnósticos dos clientes
│
└── 📖 DOCUMENTAÇÃO
    ├── START_HERE.md               ← Este arquivo!
    ├── README.md                   ← Documentação completa
    ├── GUIA_TESTE.md              ← Como testar localmente
    ├── DEPLOY.md                   ← Como fazer deploy
    └── .gitignore                  ← O que não commitar
```

---

## 🔐 Segurança

### ⚠️ IMPORTANTE antes de ir para produção:

1. **Alterar senhas padrão**:
```bash
python generate_password.py
# Gere novas senhas FORTES
# Atualize config_auth.yaml com os novos hashes
```

2. **Alterar cookie secret key** em `config_auth.yaml`:
```python
import secrets
print(secrets.token_hex(32))
# Use o resultado como a nova chave
```

3. **Configurar repositório como PRIVATE** no GitHub

4. **Não commitar**:
   - ✅ `config_auth.yaml` (senhas)
   - ✅ `idt_history.db` (dados de clientes)
   - ✅ Planilhas de clientes
   - ✅ `.streamlit/secrets.toml`

---

## 🧪 Testar funcionalidades

### 1. Autenticação
- [ ] Login com usuário válido
- [ ] Login falha com senha errada
- [ ] Logout funciona
- [ ] Sessão persiste após refresh

### 2. Nova Análise
- [ ] Upload de pré-diagnóstico
- [ ] Upload de base de aderência
- [ ] Análise completa sem erros
- [ ] Scores exibidos corretamente
- [ ] Abas de NCM/Municípios/CFOPs funcionam

### 3. Exportação
- [ ] Download Excel funciona
- [ ] Download PDF funciona
- [ ] PDF tem conteúdo correto
- [ ] Arquivos não estão corrompidos

### 4. Histórico
- [ ] Análise é salva automaticamente
- [ ] Histórico exibe análises anteriores
- [ ] Estatísticas calculadas corretamente
- [ ] Carregar análise antiga funciona

---

## 📊 Fluxo completo de uso

```
1. Usuário faz LOGIN
   ↓
2. Acessa "Nova Análise"
   ↓
3. Upload de 2 arquivos:
   - Pré-diagnóstico do cliente
   - Base Aderencia.xlsm
   ↓
4. Clica "Analisar Aderência"
   ↓
5. Sistema processa e:
   ✅ Calcula scores NCM/Municípios/CFOPs
   ✅ Identifica gaps
   ✅ Gera alertas de CFOPs não-standard
   ✅ Salva no banco de dados
   ↓
6. Usuário visualiza resultados
   ↓
7. Baixa relatórios:
   📊 Excel (dados completos)
   📄 PDF (executivo visual)
   ↓
8. Análise fica no HISTÓRICO
   (pode ser consultada depois)
```

---

## 🆘 Problemas comuns

### "Python not found"
- Instale Python 3.10+ de python.org
- Marque "Add to PATH" durante instalação

### "Module not found: streamlit"
```bash
pip install -r requirements.txt
```

### "config_auth.yaml not found"
```bash
python generate_password.py
# Criar arquivo config_auth.yaml com base no exemplo
```

### "Cannot connect to database"
- O arquivo `idt_history.db` será criado automaticamente
- Se corrompido: delete e será recriado

### App muito lento
- Planilhas Excel grandes podem demorar
- Streamlit Cloud gratuito tem recursos limitados
- Para produção: considere Azure/AWS com mais recursos

---

## 📚 Documentação completa

| Arquivo | Conteúdo |
|---------|----------|
| [README.md](README.md) | Documentação técnica completa |
| [GUIA_TESTE.md](GUIA_TESTE.md) | Como testar localmente passo a passo |
| [DEPLOY.md](DEPLOY.md) | Deploy em Streamlit Cloud e Azure |
| [START_HERE.md](START_HERE.md) | Este guia de início rápido |

---

## 💡 Dicas

### Para desenvolvedores
- O código está modular: cada funcionalidade em seu arquivo
- `idt_engine.py` pode ser usado standalone (CLI)
- Banco de dados tem índices para performance
- PDF é gerado com reportlab (customizável)

### Para PMs/Consultores
- Histórico mostra evolução dos clientes
- Estatísticas ajudam a identificar padrões
- PDF executivo está pronto para apresentação
- Alertas de CFOP destacam pontos de atenção

### Para Admins
- Fácil adicionar novos usuários (config_auth.yaml)
- Backup simples: copiar idt_history.db
- Logs em tempo real no Streamlit Cloud
- Escalável: migrar para PostgreSQL se necessário

---

## 🎉 Pronto para começar!

Escolha uma opção:

**→ Testar localmente**: vá para [GUIA_TESTE.md](GUIA_TESTE.md)

**→ Deploy em produção**: vá para [DEPLOY.md](DEPLOY.md)

**→ Entender o código**: vá para [README.md](README.md)

---

## 📞 Precisa de ajuda?

1. Consulte a documentação acima
2. Verifique os logs de erro
3. Abra uma issue no repositório
4. Contate o time de desenvolvimento

---

**IDT Analyzer v2.0** está pronto para uso! 🚀

*Thomson Reuters | 2024*
