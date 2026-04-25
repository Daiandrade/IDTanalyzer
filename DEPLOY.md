# Guia de Deploy — IDT Analyzer

Este guia explica como fazer deploy da aplicação IDT Analyzer em produção.

---

## 📋 Pré-requisitos

1. **Conta no Streamlit Cloud** (gratuita)
   - Acesse: https://share.streamlit.io/
   - Faça login com GitHub

2. **Repositório Git** (GitHub, GitLab, ou Bitbucket)
   - O código precisa estar em um repositório para deploy

3. **Arquivos configurados**:
   - ✅ `requirements.txt`
   - ✅ `.streamlit/config.toml`
   - ✅ `config_auth.yaml` (com senhas hasheadas)

---

## 🚀 Deploy no Streamlit Cloud

### Passo 1: Preparar o repositório

1. **Criar repositório Git** (se ainda não tiver):
```bash
git init
git add .
git commit -m "Initial commit - IDT Analyzer v2.0"
```

2. **Criar repositório no GitHub**:
   - Acesse: https://github.com/new
   - Nome: `idt-analyzer` (ou o nome que preferir)
   - **⚠️ IMPORTANTE**: Marque como **Private** (contém dados sensíveis)

3. **Push para GitHub**:
```bash
git remote add origin https://github.com/SEU_USUARIO/idt-analyzer.git
git branch -M main
git push -u origin main
```

### Passo 2: Configurar senhas de autenticação

1. **Gerar hashes de senha** (localmente):
```bash
python generate_password.py
```

2. **Atualizar `config_auth.yaml`** com os hashes gerados

3. **Criar senhas fortes para produção** (não use as senhas de exemplo!)

### Passo 3: Deploy no Streamlit Cloud

1. **Acesse Streamlit Cloud**: https://share.streamlit.io/

2. **Clique em "New app"**

3. **Configurar deployment**:
   - **Repository**: selecione seu repositório `idt-analyzer`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL**: escolha um nome único (ex: `idt-analyzer-tr`)

4. **Configurar secrets** (se necessário):
   - Clique em "Advanced settings"
   - Aba "Secrets"
   - Cole o conteúdo do arquivo `config_auth.yaml` se quiser gerenciar senhas via secrets

5. **Clique em "Deploy!"**

### Passo 4: Upload dos arquivos base

Como a planilha `Aderencia.xlsm` é grande e não deve ir para o Git:

**Opção A: Git LFS** (recomendado para arquivos grandes)
```bash
git lfs install
git lfs track "*.xlsm"
git add .gitattributes
git add Aderencia.xlsm
git commit -m "Add base file with LFS"
git push
```

**Opção B: Hard-code path** (se a base não muda):
- Fazer upload manual da `Aderencia.xlsm` para um storage (S3, Azure Blob, etc.)
- Modificar o app para baixar de lá

**Opção C: Deixar usuário fazer upload**
- Atualmente o app já permite upload da base
- Mas isso exige que o usuário tenha acesso ao arquivo

### Passo 5: Configurar domínio customizado (opcional)

Se quiser usar um domínio próprio (ex: `idt-analyzer.thomsonreuters.com`):

1. Vá em **Settings** → **General**
2. Configure **Custom subdomain**
3. Configure DNS CNAME apontando para o Streamlit Cloud

---

## 🔐 Segurança em Produção

### Senhas

**⚠️ CRÍTICO**: Altere TODAS as senhas padrão!

1. Gere hashes de senhas fortes:
```bash
python generate_password.py
```

2. Atualize `config_auth.yaml`:
```yaml
credentials:
  usernames:
    admin:
      password: $2b$12$[HASH_GERADO]  # senha forte!
```

3. **NÃO commite senhas no Git!**
   - `config_auth.yaml` deve estar no `.gitignore`
   - Use Streamlit Secrets ou variáveis de ambiente

### Cookie Secret Key

Altere a chave do cookie em `config_auth.yaml`:
```yaml
cookie:
  key: "uma_chave_secreta_aleatoria_muito_longa"  # Gere uma nova!
```

Para gerar uma chave aleatória:
```python
import secrets
print(secrets.token_hex(32))
```

### Banco de dados

- O SQLite funciona bem para poucos usuários
- Para produção com muitos usuários, considere PostgreSQL:
  ```python
  # Modificar db_manager.py para usar PostgreSQL
  # Usar DATABASE_URL do Streamlit Secrets
  ```

---

## 🔧 Deploy alternativo: Azure App Service

Se precisar de mais controle, pode usar Azure:

### Criar App Service

```bash
# 1. Login no Azure
az login

# 2. Criar resource group
az group create --name idt-analyzer-rg --location eastus

# 3. Criar App Service plan
az appservice plan create --name idt-plan --resource-group idt-analyzer-rg --sku B1 --is-linux

# 4. Criar Web App
az webapp create --name idt-analyzer --resource-group idt-analyzer-rg --plan idt-plan --runtime "PYTHON:3.10"

# 5. Configurar startup command
az webapp config set --name idt-analyzer --resource-group idt-analyzer-rg --startup-file "streamlit run app.py --server.port 8000 --server.address 0.0.0.0"

# 6. Deploy via Git
az webapp deployment source config-local-git --name idt-analyzer --resource-group idt-analyzer-rg

# 7. Push code
git remote add azure <url-retornada>
git push azure main
```

### Configurar variáveis de ambiente no Azure

```bash
az webapp config appsettings set --name idt-analyzer --resource-group idt-analyzer-rg --settings \
  STREAMLIT_SERVER_PORT=8000 \
  STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

---

## 📊 Monitoramento

### Logs do Streamlit Cloud

- Acesse o painel do app
- Aba "Logs" mostra erros em tempo real

### Métricas

- Aba "Analytics" mostra:
  - Número de visitantes
  - Tempo de uso
  - Erros

### Alertas

Configure alertas via email:
- Settings → Notifications
- Alerta se o app ficar offline

---

## 🔄 Atualizações

Para atualizar o app em produção:

```bash
# 1. Fazer alterações localmente
git add .
git commit -m "Update: nova funcionalidade"

# 2. Push para GitHub
git push origin main

# 3. Streamlit Cloud faz re-deploy automaticamente!
```

### Rollback

Se algo der errado:
```bash
# Ver histórico
git log --oneline

# Voltar para versão anterior
git revert <commit-hash>
git push origin main
```

---

## 🐛 Troubleshooting

### Erro: "Module not found"
- Verifique se a biblioteca está em `requirements.txt`
- Versões devem ser compatíveis

### Erro: "File not found - config_auth.yaml"
- Arquivo precisa estar no repositório
- Ou configurar via Streamlit Secrets

### App muito lento
- Streamlit Cloud gratuito tem recursos limitados
- Considere upgrade para plano pago
- Ou migre para Azure/AWS com mais recursos

### Upload de arquivo falha
- Streamlit Cloud tem limite de 200MB por arquivo
- Ajuste em `.streamlit/config.toml`:
  ```toml
  [server]
  maxUploadSize = 200
  ```

### Banco de dados não persiste
- SQLite em Streamlit Cloud é efêmero
- Use PostgreSQL para produção:
  - Heroku Postgres (gratuito para 10k linhas)
  - Azure Database for PostgreSQL
  - AWS RDS

---

## 📚 Recursos

- **Streamlit Docs**: https://docs.streamlit.io/
- **Streamlit Cloud**: https://docs.streamlit.io/streamlit-community-cloud
- **Deploy Guide**: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app
- **Secrets Management**: https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management

---

## ✅ Checklist de Deploy

Antes de ir para produção, verifique:

- [ ] Senhas alteradas (não usar senhas de exemplo!)
- [ ] Cookie secret key alterada
- [ ] `.gitignore` configurado (não commitar secrets)
- [ ] `requirements.txt` atualizado
- [ ] Arquivo `Aderencia.xlsm` disponível (via LFS ou upload)
- [ ] Testes feitos localmente
- [ ] Repositório configurado como **Private**
- [ ] SSL/HTTPS habilitado (Streamlit Cloud faz automaticamente)
- [ ] Backup do banco de dados configurado
- [ ] Documentação atualizada
- [ ] Usuários de produção criados

---

**🎯 Deploy feito! A aplicação está pronta para uso em produção.**

Em caso de problemas, consulte os logs ou abra uma issue no repositório.
