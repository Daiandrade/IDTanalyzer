# 🐘 Guia de Migração para PostgreSQL

Este guia explica como migrar o histórico de análises do SQLite local para PostgreSQL em produção.

---

## 📋 Checklist Rápido

- [ ] **Passo 1**: Criar banco PostgreSQL no Supabase
- [ ] **Passo 2**: Instalar dependências PostgreSQL
- [ ] **Passo 3**: Executar migração de dados
- [ ] **Passo 4**: Configurar secrets no Streamlit Cloud
- [ ] **Passo 5**: Atualizar código e fazer deploy
- [ ] **Passo 6**: Testar em produção

---

## PASSO 1: Criar Banco PostgreSQL no Supabase

### 1.1. Criar conta

1. Acesse: https://supabase.com/
2. Clique em **"Start your project"**
3. Faça login com GitHub (mesma conta do IDTanalyzer)

### 1.2. Criar projeto

1. Clique em **"New Project"**
2. Preencha:
   - **Name**: `idt-analyzer-db`
   - **Database Password**: **CRIE UMA SENHA FORTE E SALVE EM LOCAL SEGURO**
   - **Region**: `South America (São Paulo)`
   - **Pricing Plan**: `Free` (500MB, suficiente)
3. Clique em **"Create new project"**
4. **Aguarde 2-3 minutos** enquanto o banco é criado

### 1.3. Pegar credenciais de conexão

Após o banco ser criado:

1. No painel do Supabase, clique no ícone de **Settings** (⚙️)
2. Vá em **Database**
3. Role até a seção **"Connection string"**
4. Copie a URI no formato **"URI"** (não Session mode!)
5. A URI será algo como:
   ```
   postgresql://postgres:[SUA-SENHA]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
6. **⚠️ IMPORTANTE**: Substitua `[SUA-SENHA]` pela senha que você criou no passo 1.2
7. **SALVE ESSA URL EM LOCAL SEGURO** - você vai precisar dela!

---

## PASSO 2: Instalar Dependências PostgreSQL

Abra o terminal no diretório do projeto e execute:

```bash
pip install -r requirements.txt
```

Isso instalará `psycopg2-binary` e `sqlalchemy` que foram adicionados ao `requirements.txt`.

---

## PASSO 3: Executar Migração de Dados

### 3.1. Configurar URL do PostgreSQL

**Opção A - Via variável de ambiente (recomendado):**

```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://postgres:[SUA-SENHA]@db.xxxxxxxxxxxx.supabase.co:5432/postgres"

# Windows CMD
set DATABASE_URL=postgresql://postgres:[SUA-SENHA]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
```

**Opção B - Editar o script:**

Abra `migrate_to_postgres.py` e edite a linha 180:

```python
# Descomente e coloque sua URL aqui:
postgres_url = "postgresql://postgres:[SUA-SENHA]@db.xxxxxxxxxxxx.supabase.co:5432/postgres"
```

### 3.2. Executar migração

```bash
python migrate_to_postgres.py
```

O script irá:
- ✅ Ler os 77MB do banco SQLite local
- ✅ Criar a tabela no PostgreSQL
- ✅ Inserir todos os registros em lotes
- ✅ Verificar que tudo foi migrado

**Tempo estimado**: 5-10 minutos (depende da internet)

---

## PASSO 4: Configurar Secrets no Streamlit Cloud

### 4.1. Acessar Streamlit Cloud

1. Acesse: https://share.streamlit.io/
2. Faça login com sua conta GitHub
3. Localize o app **"IDTanalyzer"** (ou clique em **"New app"** se ainda não existir)

### 4.2. Configurar secrets

1. Clique no app (ou após criar)
2. Clique no menu **⋮** (três pontos)
3. Selecione **"Settings"**
4. Vá na aba **"Secrets"**
5. Cole o seguinte (substituindo pela SUA URL):

```toml
DATABASE_URL = "postgresql://postgres:[SUA-SENHA]@db.xxxxxxxxxxxx.supabase.co:5432/postgres"
```

6. Clique em **"Save"**

**⚠️ NUNCA commite essa URL no Git!** Ela contém a senha do banco.

---

## PASSO 5: Atualizar Código e Deploy

### 5.1. Substituir db_manager.py

```bash
# Fazer backup do antigo
copy db_manager.py db_manager_old.py

# Usar a nova versão
copy db_manager_new.py db_manager.py
```

Ou simplesmente:
- Renomeie `db_manager.py` para `db_manager_old.py`
- Renomeie `db_manager_new.py` para `db_manager.py`

### 5.2. Commit e push

```bash
git add .
git commit -m "Update: Migrate to PostgreSQL for production database"
git push origin main
```

### 5.3. Aguardar deploy

1. O Streamlit Cloud detectará as mudanças
2. Fará rebuild automático (~2-5 minutos)
3. Aguarde até o status ficar 🟢 **Running**

---

## PASSO 6: Testar em Produção

### 6.1. Acessar o app em produção

1. Abra a URL do seu app no Streamlit Cloud
2. Faça login como **admin**
3. Vá em **"Histórico"**

### 6.2. Verificar

✅ **Deve mostrar**:
- Todo o histórico de análises que estava no SQLite local
- Estatísticas corretas (score médio, total de gaps, etc.)
- Possibilidade de carregar análises antigas

❌ **Se não mostrar**:
- Verifique os **Logs** do app no Streamlit Cloud
- Veja se há erro de conexão com PostgreSQL
- Confirme que DATABASE_URL está nos secrets

---

## 🔍 Verificação e Troubleshooting

### Verificar conexão local ao PostgreSQL

Para testar se sua máquina consegue conectar ao PostgreSQL:

```bash
python db_manager_new.py
```

Deve mostrar:
```
✅ Database initialized successfully
📁 Database type: PostgreSQL (Production)
🔗 Connection: ✅ OK
📊 Total records: [número de registros]
```

### Comandos úteis Supabase

**Acessar SQL Editor:**
1. Painel Supabase → **SQL Editor**
2. Execute query para verificar dados:

```sql
-- Ver total de registros
SELECT COUNT(*) FROM analyses;

-- Ver últimas 10 análises
SELECT id, timestamp, usuario, cliente_nome, score_geral
FROM analyses
ORDER BY timestamp DESC
LIMIT 10;

-- Ver estatísticas por usuário
SELECT usuario, COUNT(*) as total, AVG(score_geral) as score_medio
FROM analyses
GROUP BY usuario;
```

### Erros comuns

**Erro: "connection refused"**
- Verifique se a URL está correta
- Confirme que o banco no Supabase está ativo (não pausado)

**Erro: "password authentication failed"**
- A senha na URL está incorreta
- Copie novamente do Supabase e substitua `[YOUR-PASSWORD]`

**Erro: "table does not exist"**
- Execute `python db_manager_new.py` para criar as tabelas
- Ou execute o script de migração novamente

**App não conecta ao PostgreSQL em produção:**
- Verifique se DATABASE_URL está nos **Secrets** do Streamlit
- Reboot o app: Dashboard → App → Menu ⋮ → Reboot app

---

## 📊 Comparação: Antes vs Depois

### Antes (SQLite)

- ✅ Fácil de usar localmente
- ❌ Histórico NÃO sincroniza com produção
- ❌ Cada ambiente tem seu próprio banco
- ❌ 77MB não vai para o Git

### Depois (PostgreSQL)

- ✅ Histórico unificado entre local e produção
- ✅ Dados persistentes e profissionais
- ✅ Backup automático (Supabase)
- ✅ Escalável para múltiplos usuários
- ✅ Pode conectar de qualquer lugar

---

## 🔄 Desenvolvimento Local com PostgreSQL

Se quiser usar PostgreSQL também localmente (opcional):

### Opção 1: Usar mesmo banco de produção

```bash
# Configure DATABASE_URL localmente
$env:DATABASE_URL="postgresql://postgres:[SUA-SENHA]@db.xxx.supabase.co:5432/postgres"

# Rode o app
streamlit run app.py
```

**⚠️ Cuidado**: Você estará mexendo nos dados de produção!

### Opção 2: Criar banco separado para dev

1. Crie outro projeto no Supabase (ou use PostgreSQL local)
2. Configure URL diferente localmente
3. Produção usa uma URL, dev usa outra

### Opção 3: Continuar com SQLite local

Deixe `DATABASE_URL` vazio localmente:
- Local: usará `idt_history.db` (SQLite)
- Produção: usará PostgreSQL (via secrets)

Cada ambiente tem seu histórico separado, mas produção terá persistência.

---

## 🎯 Próximos Passos (Opcional)

### Backup automático

Configure rotina de backup no Supabase:
1. Painel → **Database** → **Backups**
2. Backups diários automáticos (plano grátis: 7 dias de retenção)

### Monitoramento

1. Supabase Dashboard mostra:
   - Uso de storage
   - Queries por segundo
   - Conexões ativas

2. Configure alertas de uso se necessário

### Migração incremental

Se quiser continuar usando SQLite local e sincronizar apenas o necessário:
1. Modifique `migrate_to_postgres.py` para inserir apenas novos registros
2. Execute periodicamente para sincronizar

---

## ✅ Checklist Final

Antes de considerar a migração completa:

- [ ] Banco PostgreSQL criado no Supabase
- [ ] URL de conexão salva em local seguro
- [ ] Dependências instaladas (`requirements.txt`)
- [ ] Migração executada com sucesso (todos os registros migrados)
- [ ] `DATABASE_URL` configurada nos Secrets do Streamlit Cloud
- [ ] `db_manager.py` atualizado (nova versão com suporte PostgreSQL)
- [ ] Código commitado e pushed para GitHub
- [ ] Deploy concluído no Streamlit Cloud (status 🟢)
- [ ] Teste realizado: histórico aparece em produção
- [ ] Teste realizado: nova análise salva corretamente

---

## 📞 Suporte

**Problemas durante migração?**

1. Verifique os logs do script de migração
2. Teste conexão com `python db_manager_new.py`
3. Consulte logs do Streamlit Cloud
4. Verifique SQL no Supabase Dashboard

**Documentação oficial:**
- Supabase: https://supabase.com/docs
- SQLAlchemy: https://docs.sqlalchemy.org/
- Streamlit Secrets: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management

---

**🎉 Migração completa! Seu app agora tem histórico persistente em produção.**

Thomson Reuters | IDT Analyzer v2.0  
Última atualização: 2024-05-05
