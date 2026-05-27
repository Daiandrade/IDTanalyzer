# 🚀 Guia de Verificação de Deploy em Produção

## ✅ Status Atual

**Última atualização**: Deploy da base de aderência enviado para produção  
**Commit**: `5647330` - "Add: Base de aderencia para producao"  
**Repositório**: https://github.com/Daiandrade/IDTanalyzer

---

## ⏱️ Timeline do Deploy

| Etapa | Tempo | Status |
|-------|-------|--------|
| 1. Push para GitHub | Imediato | ✅ Concluído |
| 2. GitHub sincroniza | ~10s | ✅ Concluído |
| 3. Streamlit detecta mudança | ~30s | ⏳ Em andamento |
| 4. Streamlit inicia build | ~1min | ⏳ Aguardando |
| 5. Build completo | ~3-5min | ⏳ Aguardando |
| 6. App disponível | ~5min total | ⏳ Aguardando |

---

## 🔍 Como Verificar o Status

### 1️⃣ Verificar GitHub

**Link direto**: https://github.com/Daiandrade/IDTanalyzer/commits/main

✅ **O que procurar**:
- Último commit deve ser: "Add: Base de aderencia para producao"
- Data/hora: hoje, há poucos minutos
- Arquivos alterados: 2 files changed
  - `.gitignore` (modificado)
  - `config/Aderencia.xlsm` (novo - 3.9 MB)

📂 **Verificar arquivo**:
- https://github.com/Daiandrade/IDTanalyzer/tree/main/config
- Deve aparecer `Aderencia.xlsm` (3.9 MB)

---

### 2️⃣ Verificar Streamlit Cloud

**Link**: https://share.streamlit.io/

1. Faça login na sua conta Streamlit
2. Localize o app "IDTanalyzer" na lista
3. Verifique o status:

| Status | Significado |
|--------|-------------|
| 🟢 **Running** | App rodando normalmente |
| 🔵 **Building** | Fazendo rebuild (normal após push) |
| 🔴 **Error** | Erro no build - verificar logs |
| ⚪ **Sleeping** | Inativo - será acordado ao acessar |

---

### 3️⃣ Verificar Logs (se necessário)

Se o app mostrar erro ou não atualizar:

1. Streamlit Dashboard → Seu app
2. Clique no **menu ⋮** (três pontos)
3. Selecione **"Logs"**
4. Procure por:

✅ **Mensagens de sucesso**:
```
Successfully built
Streamlit app is running
```

❌ **Erros comuns**:
```
FileNotFoundError: config/Aderencia.xlsm
ModuleNotFoundError: No module named 'xyz'
PermissionError: ...
```

---

### 4️⃣ Testar o App em Produção

**Após o build terminar** (luz verde 🟢):

1. **Abrir o app** (URL do Streamlit Cloud)
2. **Login como admin**:
   - Usuário: `admin`
   - Senha: (a senha configurada)
3. **Ir para Configurações** (menu lateral)
4. **Verificar seção "Gerenciar Base de Aderência"**

✅ **Deve mostrar**:
```
✅ Base de aderência configurada

Arquivo atual:
- Nome: Aderencia.xlsm
- Tamanho: ~4000 KB
- Última modificação: [data]
```

❌ **Se mostrar**:
```
⚠️ Base de aderência NÃO configurada
```
→ Significa que o arquivo não foi carregado corretamente

---

## 🐛 Troubleshooting

### Problema 1: "Base não configurada" após 10 minutos

**Possíveis causas**:

1. **Arquivo não foi para o GitHub**
   - Verificar: https://github.com/Daiandrade/IDTanalyzer/tree/main/config
   - Solução: Executar `ATUALIZAR_PRODUCAO.bat` novamente

2. **Streamlit não atualizou**
   - Verificar: Dashboard → Status do app
   - Solução: Reboot manual do app

3. **Erro no build**
   - Verificar: Logs do Streamlit
   - Solução: Depende do erro (ver logs)

---

### Problema 2: App mostra erro ao carregar

**Verificar logs** para ver o erro específico.

**Erros comuns**:

```python
# Erro: Arquivo não encontrado
FileNotFoundError: [Errno 2] No such file or directory: 'config/Aderencia.xlsm'
```
→ **Solução**: Verificar se arquivo está no GitHub no caminho correto

```python
# Erro: Falta biblioteca
ModuleNotFoundError: No module named 'openpyxl'
```
→ **Solução**: Adicionar `openpyxl` no `requirements.txt`

```python
# Erro: Permissão negada
PermissionError: [Errno 13] Permission denied: 'config/Aderencia.xlsm'
```
→ **Solução**: Problema de permissões no Streamlit (raro)

---

### Problema 3: Build demora muito (>10 minutos)

**Ações**:

1. **Reboot forçado**:
   - Dashboard → App → Menu ⋮ → Reboot app

2. **Verificar tamanho**:
   - Streamlit Cloud gratuito tem limites
   - Arquivo de 4 MB deve funcionar normalmente

3. **Verificar dependências**:
   - `requirements.txt` pode ter bibliotecas pesadas
   - Remover bibliotecas desnecessárias

---

## 🔧 Comandos Úteis

### Forçar rebuild no Streamlit Cloud

Via interface:
1. Dashboard → Seu app
2. Menu ⋮ → Reboot app

### Verificar status local vs GitHub

```bash
cd "Projeto Daiane"
git status
git log --oneline -5
git ls-files | grep -i ader
```

### Verificar arquivo no GitHub (via API)

```bash
curl -s https://api.github.com/repos/Daiandrade/IDTanalyzer/contents/config/Aderencia.xlsm | grep "size"
```

Deve retornar:
```json
"size": 4085489
```

---

## 📞 Suporte

Se após 15 minutos o problema persistir:

1. ✅ Verificar todos os itens deste guia
2. 📸 Capturar screenshot do erro
3. 📋 Copiar logs completos do Streamlit
4. 🔍 Verificar se arquivo está no GitHub
5. 📧 Reportar com todas as informações acima

---

## ✅ Checklist Final

Use este checklist para validação:

### GitHub
- [ ] Commit aparece em: https://github.com/Daiandrade/IDTanalyzer/commits/main
- [ ] Arquivo existe em: https://github.com/Daiandrade/IDTanalyzer/tree/main/config
- [ ] Tamanho do arquivo: ~4 MB (4085489 bytes)

### Streamlit Cloud
- [ ] App está com status 🟢 Running
- [ ] Não há erros nos logs
- [ ] Build completou em < 10 minutos

### Aplicação
- [ ] App carrega sem erros
- [ ] Login funciona
- [ ] Configurações mostra "✅ Base configurada"
- [ ] Nova análise NÃO pede upload de base
- [ ] Análise funciona corretamente

---

**🎯 Se todos os itens estão marcados: Deploy concluído com sucesso!**

---

**Última atualização**: 2024-04-27  
**Versão**: IDT Analyzer v2.0  
**Responsável**: Daiane Andrade
