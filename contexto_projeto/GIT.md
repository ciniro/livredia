# 📦 PROTOCOLO GIT - LIVRE DIA

**Documento:** Protocolo de Versionamento e Controle de Versão
**Repositório:** https://github.com/ciniro/livredia
**Branch Principal:** `main`

---

## 🚨 PROTOCOLO CRÍTICO DE BRANCHES

### ⛔ REGRAS ABSOLUTAS

**Branch `main` (Desenvolvimento):**
- ✅ TODO o trabalho de desenvolvimento acontece aqui
- ✅ Contém TODA a documentação (contexto_projeto/, CLAUDE.md, DEPLOY.md, etc.)
- ✅ Cada "APROVADO" do usuário = Ponto de Marco (milestone/commit)
- ✅ Histórico completo e incremental de todo o trabalho
- ✅ **SEMPRE** trabalhar nesta branch
- ✅ **SEMPRE** reverter a partir desta branch

**Branch `prod` (Releases Estáveis):**
- ✅ Contém APENAS releases estáveis prontas para produção
- ✅ Snapshot FILTRADO sem arquivos de contexto (contexto_projeto/, CLAUDE.md, data/, etc.)
- ✅ **NUNCA** usar para desenvolvimento
- ✅ **NUNCA** reverter arquivos desta branch
- ✅ Pode estar DESATUALIZADA em relação à main
- ✅ É apenas um espelho do que está/vai estar em produção

### 🔄 PROTOCOLO DE REVERSÃO

**ANTES de fazer QUALQUER reversão:**

1. ⚠️ **PERGUNTAR ao usuário:** Explicar EXATAMENTE o que será revertido e para qual commit
2. ⚠️ **AGUARDAR autorização explícita** do usuário
3. ⚠️ **NUNCA** reverter sem autorização prévia

**Quando autorizado a reverter:**

```bash
# ✅ CORRETO - Sempre da branch main
git checkout main
git log --oneline -20  # Ver commits disponíveis
git reset --hard <commit_hash_da_main>

# ❌ ERRADO - NUNCA fazer isso
git checkout prod
git checkout prod -- arquivo.html
git reset --hard <commit_da_prod>
```

### 📦 DEPLOY (main → prod)

**Arquivos que NÃO são copiados para prod:**
- contexto_projeto/ (toda pasta)
- CLAUDE.md
- DEPLOY.md
- data/ (backups PostgreSQL)
- Arquivos de teste
- .claude/ (settings locais)

**Ver protocolo completo em:** `contexto_projeto/DEPLOY.md`

---

## Workflow de Commits

- ✅ **Commits descritivos e em português** - Usar formato convencional (feat, fix, docs, chore, etc.)
- ✅ **Testar antes de commitar** - Testes automatizados + aprovação do usuário
- ✅ **OBRIGATÓRIO:** Commit + push após cada tela aprovada pelo usuário
- ✅ **Branch:** Sempre usar `main` para desenvolvimento

---

## Tipos de Commits

### 1. Implementação de Telas (feat)

```bash
git add -A
git status  # Verificar arquivos que serão commitados
git commit -m "$(cat <<'EOF'
feat: Implementar Tela X - Nome da Tela

[Descrição detalhada da tela, funcionalidades, arquivos criados]

Arquivos criados/modificados:
- apps/[app]/views.py: [descrição]
- apps/[app]/urls.py: [descrição]
- templates/[caminho].html: [descrição]
- contexto_projeto/PROGRESSO.md: Atualização de progresso

Funcionalidades:
- [Lista de funcionalidades implementadas]

Testes realizados:
- [Lista de testes executados]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push origin main
```

### 2. Correções de Bugs (fix)

```bash
git add -A
git commit -m "fix: Corrigir [descrição do bug]"
git push origin main
```

### 3. Documentação (docs)

```bash
git add contexto_projeto/  # Adicionar arquivos de documentação
git commit -m "docs: Atualizar [descrição]"
git push origin main
```

### 4. Manutenção (chore)

Exemplos: correção de permissões, atualização de dependências, etc.

```bash
git add -A
git commit -m "chore: [descrição da manutenção]"
git push origin main
```

---

## Situações Especiais

### Mudanças de Permissões (OneDrive)

- Quando arquivos vêm do OneDrive com permissões incorretas (755 vs 644)
- Git detecta mudança de modo mesmo sem alteração de conteúdo
- **Ação:** Commitar normalmente com tipo `chore`

```bash
git add -A
git commit -m "chore: Corrigir permissões de arquivos (755 → 644)"
git push origin main
```

### Verificação Antes de Commit

```bash
# SEMPRE verificar o que será commitado
git status

# Ver detalhes das mudanças (opcional)
git diff
git diff --stat  # Resumo das mudanças

# Ver mudanças de permissões
git diff --summary
```

---

## Arquivos a NUNCA Commitar

### Já configurados no .gitignore

- ❌ `.env` (credenciais sensíveis)
- ❌ `venv/` (ambiente virtual - caminhos específicos de cada Mac)
- ❌ `__pycache__/` (cache Python)
- ❌ `*.pyc` (bytecode compilado)
- ❌ `db.sqlite3` (banco SQLite - se usar)
- ❌ `media/` (uploads de usuários)
- ❌ `.DS_Store` (metadados macOS)
- ❌ `data/*.backup` (backups PostgreSQL - sincronizados via OneDrive)

### Por que backups não vão para o Git

- Arquivos grandes (podem ter 100MB+)
- Dados pessoais/sensíveis
- Sincronizados via OneDrive (melhor método para este caso)
- Git não é ferramenta de backup de dados

### Sempre verificar antes de commitar

```bash
git status  # Ver o que será commitado
# Se aparecer algo que NÃO deveria estar (ex: .env, venv/):
git restore --staged arquivo-indesejado
```

---

## Protocolo Pós-Commit

- ✅ Verificar push bem-sucedido
- ✅ Atualizar `contexto_projeto/PROGRESSO.md` (se for tela nova)
- ✅ **ATUALIZAR CLAUDE.md com informações do commit:**
  - Obter hash e data do commit: `git log -1 --format="%h - %cd" --date=format:"%d de %B de %Y às %H:%M:%S"`
  - Obter mensagem do commit: `git log -1 --format="%s"`
  - Atualizar cabeçalho do `CLAUDE.md` com:
    - **Última Atualização:** data/hora atual
    - **Último Commit:** data/hora do commit, hash e mensagem resumida
- ✅ Informar ao usuário: commit hash, arquivos alterados, próxima tela

---

**📚 Documentos Relacionados:**
- `WORKFLOW.md` - Protocolo completo de desenvolvimento
- `PROGRESSO.md` - Acompanhamento de telas concluídas
