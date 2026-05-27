# 🔐 Como Configurar Secrets no Streamlit Cloud

## ⚡ Passo a Passo Rápido

### 1. Acessar Streamlit Cloud

Abra: https://share.streamlit.io/

### 2. Localizar seu app

- Se o app **"IDTanalyzer"** já existe: clique nele
- Se NÃO existe: clique em **"New app"** e configure:
  - Repository: `Daiandrade/IDTanalyzer`
  - Branch: `main`
  - Main file: `app.py`
  - Depois clique em **"Deploy"** e aguarde

### 3. Abrir Settings

1. No card do app, clique no **menu ⋮** (três pontos)
2. Selecione **"Settings"**

### 4. Configurar Secrets

1. Na tela de Settings, clique na aba **"Secrets"**
2. **Cole EXATAMENTE este texto** na caixa:

```toml
DATABASE_URL = "postgresql://postgres:Day93127712@db.orgsuhxoanolrkcicwuf.supabase.co:5432/postgres"
```

3. Clique em **"Save"**

### 5. Reiniciar o App

1. Volte para o dashboard
2. Clique no menu ⋮ novamente
3. Selecione **"Reboot app"**
4. Aguarde 2-3 minutos para o app reiniciar

---

## ✅ Como Verificar se Funcionou

### No Streamlit Cloud Dashboard

- Status do app deve ficar **🟢 Running** (não 🔴 Error)
- Se ficar vermelho, clique em **"Logs"** para ver o erro

### No App em Produção

1. Abra a URL do app
2. Faça login como **admin**
3. Vá em **"Histórico"**
4. Se carregar (mesmo vazio), está funcionando!
5. Faça uma análise de teste
6. Volte ao Histórico
7. A análise deve aparecer! ✅

---

## 🐛 Troubleshooting

### Erro: "DATABASE_URL not found"

- Verifique se copiou o texto EXATAMENTE como está
- Não pode ter espaços extras antes ou depois
- Deve ter as aspas `"` em volta da URL

### Erro: "Connection failed"

- Verifique se a senha está correta: `Day93127712`
- Verifique se o host é: `db.orgsuhxoanolrkcicwuf.supabase.co`
- Tente rebootar o app novamente

### App não reinicia

- Aguarde até 5 minutos
- Se continuar travado, clique em "Clear cache" e "Reboot app"

---

## 📊 Comportamento Esperado

### Local (sua máquina)

- Continua usando SQLite (`idt_history.db`)
- Histórico antigo permanece funcionando
- Você pode trabalhar normalmente offline

### Produção (Streamlit Cloud)

- Usa PostgreSQL (Supabase)
- Histórico novo será salvo lá
- Disponível para todos que acessarem
- Dados persistem entre deploys

---

## 🔒 Segurança

- ✅ Secrets NÃO vão para o Git
- ✅ Apenas você vê os secrets no dashboard
- ✅ Usuários do app NÃO veem a senha
- ⚠️ Não compartilhe sua URL de DATABASE_URL publicamente

---

**🎉 Pronto! Seu app agora tem banco de dados profissional em produção!**
