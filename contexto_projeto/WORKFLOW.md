# ⚙️ WORKFLOW OBRIGATÓRIO PARA DESENVOLVIMENTO

**Documento:** Protocolo de Desenvolvimento de Melhorias
**Projeto:** LIVRE DIA - Fase Pós-MVP
**Aplicação:** Obrigatória para todas as melhorias e novas funcionalidades

---

## ⚠️ REGRA DE OURO

**UMA MELHORIA POR VEZ** - Nunca iniciar uma nova funcionalidade sem ter concluído, testado a anterior e obtido aprovação explícita do usuário.

---

## 🚨 PROTOCOLO CRÍTICO DE BRANCHES

### ⛔ TRABALHE SEMPRE NA BRANCH `main`

**Branch `main` (Desenvolvimento):**
- ✅ TODO o desenvolvimento acontece aqui
- ✅ Cada "APROVADO" = commit milestone
- ✅ Histórico completo do trabalho
- ✅ **NUNCA** trabalhar na branch `prod`

**Branch `prod` (Produção):**
- ✅ Apenas releases filtrados para produção
- ✅ **NUNCA** usar para desenvolvimento
- ✅ **NUNCA** reverter arquivos desta branch

### 🔄 ANTES de Reverter Qualquer Arquivo

1. ⚠️ **PERGUNTAR ao usuário** o que será revertido e para qual commit
2. ⚠️ **AGUARDAR autorização explícita**
3. ⚠️ **SEMPRE** reverter da branch `main`, NUNCA da `prod`

**Ver protocolo completo em:** `contexto_projeto/GIT.md`

---

## ETAPA 0: VERIFICAÇÃO DE PROGRESSO (OBRIGATÓRIA ANTES DE INICIAR)

### 1. 📊 Consultar PROGRESSO.md e ROADMAP.md

- Ler seção "Catálogo de Melhorias Futuras" em PROGRESSO.md
- Verificar qual categoria/funcionalidade será implementada
- Consultar especificação detalhada em `contexto_projeto/ROADMAP.md`
- Verificar se há melhorias pendentes de aprovação

### 2. ✅ Confirmar com o usuário

- Perguntar: "Vou iniciar a implementação da [Categoria X - Funcionalidade Y] conforme ROADMAP.md. Correto?"
- Aguardar confirmação explícita antes de prosseguir
- **NUNCA** assumir qual funcionalidade deve ser implementada sem confirmar com o usuário

---

## ETAPA 1: PESQUISA E ANÁLISE (antes de qualquer código)

### 1. ✅ Ler especificação da funcionalidade

- Localizar categoria e funcionalidade em `contexto_projeto/ROADMAP.md`
- Entender: objetivo, requisitos técnicos, complexidade, impacto
- Identificar todos os componentes necessários (modelos, views, templates, JavaScript)

### 2. ✅ Analisar código existente relacionado

- Buscar funcionalidades similares já implementadas no projeto
- Identificar padrões de código a serem seguidos
- Verificar templates, views e modelos que podem servir de base
- Consultar exemplos de HTMX, Alpine.js, Quill.js já implementados

### 3. ✅ Consultar decisões de design e padrões estabelecidos

- Verificar `contexto_projeto/DESIGN.md`
- Aplicar paleta de cores expandida (header/footer, botões)
- Aplicar terminologia user-friendly ("tema" vs "tag", "obra" vs "texto")
- Usar sistema de navegação integrado (links inteligentes)
- Implementar avatares automáticos quando aplicável
- Aplicar padrões HTMX estabelecidos (hx-get, hx-target, hx-push-url)
- Seguir padrões de UI já estabelecidos (modais, toasts, cards, etc.)

### 4. ✅ Verificar/Planejar mudanças nos modelos

- Identificar se novos modelos serão necessários
- Verificar se modelos existentes precisam de novos campos
- Planejar relacionamentos (ForeignKey, ManyToMany)
- Verificar tipos de dados (CharField, TextField, BooleanField, etc.)
- Documentar mudanças necessárias antes de implementar

---

## ETAPA 2: PREPARAÇÃO DO BANCO DE DADOS (se necessário)

**SE** a funcionalidade exigir mudanças no banco de dados:

1. 🔧 Criar/modificar modelos em `models.py`
2. 📝 Executar `python manage.py makemigrations`
3. 💾 Executar `python manage.py migrate`
4. ✅ Verificar integridade do banco
5. ✅ Só então prosseguir para desenvolvimento

---

## ETAPA 3: DESENVOLVIMENTO

### 1. Implementar Backend (quando necessário)

**Views:**
- Localização: `views.py` do app apropriado
- Tipo: Class-Based View ou Function-Based View conforme contexto
- Implementar lógica de negócio
- Preparar contexto para templates
- Implementar APIs/endpoints AJAX se necessário

**URLs:**
- Localização: `urls.py`
- Definir padrões de rotas
- Nomear URLs (URL name)
- Incluir no URLconf principal se necessário

### 2. Implementar Frontend

**Templates:**
- Criar ou modificar templates existentes
- Usar templates base apropriados (base.html, base_autor.html, base_admin.html)
- Integrar com dados dinâmicos (context)
- Manter consistência visual com o resto do sistema
- Aplicar decisões de design (DESIGN.md)

**JavaScript:**
- Implementar interatividade com Alpine.js, HTMX ou JavaScript vanilla
- Seguir padrões já estabelecidos no projeto
- Adicionar validações client-side quando apropriado
- Implementar modais, toasts, confirmações conforme necessário

**CSS:**
- Usar Tailwind CSS seguindo classes já utilizadas no projeto
- Manter consistência com paleta de cores
- Aplicar responsividade mobile-first

---

## ETAPA 4: TESTE (OBRIGATÓRIO)

### ⚠️ REGRA CRÍTICA

**NUNCA** peça para o usuário testar sem antes ter testado você mesmo completamente, incluindo login e acesso à tela via navegador. Se houver erros, corrija **TODOS** antes de solicitar teste do usuário.

### 0. 🔐 TESTE MANUAL COMPLETO (OBRIGATÓRIO antes de pedir teste do usuário)

- **SEMPRE** fazer login como usuário apropriado (admin, autor ou leitor)
- **SEMPRE** acessar a tela implementada via navegador/interface
- **SEMPRE** testar todas as funcionalidades da tela (botões, formulários, links)
- **SEMPRE** verificar se não há erros 500, exceções ou páginas quebradas
- **Se houver QUALQUER erro:** corrija e repita o teste completo
- **NUNCA** solicite teste do usuário se você não testou antes
- **NUNCA** solicite teste do usuário se houver erros conhecidos

### 1. 🧪 TESTES AUTOMATIZADOS (executar ANTES de solicitar teste do usuário)

- Executar `python manage.py check` para verificar configuração
- Iniciar servidor com `python manage.py runserver` em background
- Iniciar o PostgreSQL
- Testar todas as rotas principais com `curl` (verificar código HTTP 200)
- Testar formulários (se aplicável) com dados válidos e inválidos
- Verificar integridade do banco de dados (queries do Django ORM)
- Testar funcionalidades HTMX/Alpine.js (se aplicável)
- **IMPORTANTE:** O servidor DEVE permanecer ativo após os testes

### 2. 📊 RELATÓRIO DE TESTES

- Apresentar resumo dos testes executados ao usuário
- Indicar todas as rotas testadas e seus status
- Mostrar eventuais warnings ou observações
- Informar que o servidor já está rodando em http://127.0.0.1:8000/

### 3. 🛑 PAUSA OBRIGATÓRIA - Aguardar teste manual do usuário

- **NUNCA** prosseguir automaticamente
- Aguardar feedback explícito do usuário
- Servidor já deve estar ativo (`python manage.py runserver`)

### 4. 🐛 SE HOUVER BUGS

- Corrigir todos os problemas identificados
- Repetir ETAPA 4 completa (testes + aprovação do usuário)

### 5. ✅ APÓS APROVAÇÃO EXPLÍCITA

Usuário deve dizer "aprovado" ou equivalente categórico.

#### a) Atualizar PROGRESSO.md e requiriments.txt

- atualizar o requirements.txt para manter ele sempre com as bibliotecas necessárias e suas versões
- Adicionar seção documentando a melhoria implementada
- Incluir: categoria, funcionalidades implementadas, arquivos modificados/criados
- Incluir: migrações aplicadas (se houver), testes realizados
- Atualizar status da categoria no catálogo de melhorias
- Adicionar data/hora da última atualização

#### b) Versionamento Git

**Ver protocolo completo em:** `contexto_projeto/GIT.md`

**Resumo:**
1. Verificar arquivos modificados (`git status`)
2. Adicionar arquivos relevantes (`git add -A`)
3. Criar commit descritivo em português
4. Fazer push para GitHub (`git push origin main`)
5. Confirmar sucesso ao usuário

#### c) Atualizar CLAUDE.md (raiz)

**OBRIGATÓRIO após cada commit com push:**

1. Obter informações do último commit:
   ```bash
   git log -1 --format="%h - %cd" --date=format:"%d de %B de %Y às %H:%M:%S"
   git log -1 --format="%s"
   ```

2. Atualizar cabeçalho do `CLAUDE.md`:
   - **Última Atualização:** data/hora atual
   - **Último Commit:** data/hora do commit, hash e mensagem resumida

**Exemplo:**
```markdown
**Última Atualização:** 27 de outubro de 2025 às 16:00:00
**Último Commit:** 27 de outubro de 2025 às 15:28:41 - `e99a0dd` (feat: Implementar Tela 20...)
```

#### d) Confirmação ao usuário

- Informar qual funcionalidade/categoria foi concluída
- Resumir mudanças implementadas
- Aguardar decisão do usuário sobre próxima melhoria a implementar

### 6. ➡️ PRÓXIMA MELHORIA

- Só após commit/push bem-sucedidos → retornar à **ETAPA 0**
- Aguardar usuário definir próxima funcionalidade do ROADMAP.md

---

## ✅ REGRAS FUNDAMENTAIS

### Desenvolvimento

- ✅ **UMA MELHORIA POR VEZ** - Nunca começar a próxima sem concluir a atual
- ✅ **SEMPRE consultar ROADMAP.md** antes de codificar
- ✅ **SEMPRE analisar código existente** para manter consistência
- ✅ **EXECUTAR TESTES PRÓPRIOS** antes de solicitar teste do usuário (ver ETAPA 4)
- ✅ **SERVIDOR ATIVO** - Manter `python manage.py runserver` rodando antes do teste do usuário
- ✅ **SEMPRE esperar aprovação categórica do usuário** ("aprovado") antes de continuar
- ✅ **APÓS APROVAÇÃO:** Atualizar PROGRESSO.md + commit + push + **atualizar CLAUDE.md com info do commit**
- ✅ **Seguir identidade visual** e padrões já estabelecidos no sistema
- ✅ **Aplicar decisões de design** (DESIGN.md) consistentemente em todas as implementações

### Código

- ❌ **NUNCA usar Django Admin** para interface de usuário
- ✅ Criar **views customizadas** seguindo os protótipos
- ✅ Usar **variáveis de ambiente** (.env) para dados sensíveis
- ✅ Manter **models.py consistentes** com protótipos
- ✅ Escrever **código limpo e comentado**

---

**📚 Documentos Relacionados:**
- `PROGRESSO.md` - Acompanhamento de melhorias concluídas e catálogo completo
- `ROADMAP.md` - Especificações detalhadas de todas as melhorias propostas
- `DESIGN.md` - Decisões de design e UX
- `GIT.md` - Protocolo completo de versionamento
- `MODELOS.md` - Resumo dos modelos do banco de dados
