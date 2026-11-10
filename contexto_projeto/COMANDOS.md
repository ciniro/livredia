# 🔧 COMANDOS ÚTEIS - LIVRE DIA

**Documento:** Referência Rápida de Comandos
**Projeto:** LIVRE DIA

---

## Ambiente Virtual

```bash
# Ativar ambiente
source venv/bin/activate

# Desativar
deactivate
```

---

## Django

```bash
# Verificar configuração
python manage.py check

# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Executar servidor de desenvolvimento
python manage.py runserver

# Criar superusuário (se necessário)
python manage.py createsuperuser

# Shell interativo
python manage.py shell
```

---

## Git

```bash
# Verificar status (SEMPRE antes de commitar)
git status

# Ver diferenças detalhadas
git diff
git diff --stat        # Resumo de arquivos modificados
git diff --summary     # Incluir mudanças de permissões

# Adicionar arquivos
git add -A             # Adicionar TUDO (novos, modificados, deletados)
git add .              # Adicionar apenas no diretório atual
git add arquivo.py     # Adicionar arquivo específico

# Remover arquivo do staging (se adicionou por engano)
git restore --staged arquivo.py

# Commit com mensagem simples
git commit -m "tipo: descrição curta"

# Commit com mensagem longa (RECOMENDADO para telas)
git commit -m "$(cat <<'EOF'
feat: Implementar Tela X - Nome da Tela

Descrição detalhada:
- Funcionalidade 1
- Funcionalidade 2
- Arquivos criados: views.py, urls.py, template.html

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Push para repositório remoto
git push origin main

# Pull (atualizar do remoto)
git pull origin main

# Ver histórico de commits
git log --oneline -10  # Últimos 10 commits
git log --stat         # Com detalhes de arquivos

# Ver último commit
git show HEAD

# Desfazer último commit (CUIDADO!)
git reset --soft HEAD~1  # Mantém mudanças no staging
git reset --hard HEAD~1  # APAGA mudanças (irreversível)
```

---

## PostgreSQL

```bash
# Conectar ao banco
psql -U postgres -h localhost -d db_livredia

# Listar tabelas
\dt

# Descrever tabela
\d nome_da_tabela

# Sair
\q
```

---

**📚 Documentos Relacionados:**
- `GIT.md` - Protocolo completo de versionamento
- `MUDANCA_COMPUTADOR.md` - Rotina de backup e restauração
