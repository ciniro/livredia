# 🎨 DECISÕES DE DESIGN E MELHORIAS IMPLEMENTADAS - LIVRE DIA

**Documento:** Decisões de Design e UX Implementadas
**Projeto:** LIVRE DIA

---

## ⚠️ REGRA IMPORTANTE

Durante o desenvolvimento, foram implementadas melhorias de design e UX que **diferem dos protótipos originais**. Estas decisões devem **PREVALECER** sobre os protótipos em telas futuras, pois representam refinamentos testados e aprovados.

---

## 1. Paleta de Cores Expandida

**Cores adicionais implementadas (além dos protótipos):**
```css
--header-bg: #e8ebe6/95      /* Background header (tom terroso claro) */
--footer-bg: #dde0db/95      /* Background footer (tom terroso médio) */
--verde-floresta-hover: #2d3d2d  /* Hover state do verde floresta */
```

**Uso estratégico:**
- Verde Floresta (`#3A4D39`): botões primários, borders, elementos de destaque
- Laranja (`#e69019`): botões secundários, destaques importantes
- Tons terrosos: header/footer para criar hierarquia visual sutil

---

## 2. Terminologia User-Friendly

**Backend vs Frontend (vocabulário diferenciado):**

| Backend (Código) | Frontend (Interface) | Contexto |
|------------------|---------------------|----------|
| `tag` | Tema | Categorização de textos |
| `texto` / `resultados` | Obra(s) | Referência aos textos literários |
| `per_page` | Quantidade de obras exibidas | Configuração de paginação |

**Justificativa:** "Tag" é termo técnico em inglês; "tema" é mais acessível ao público brasileiro. "Obra" eleva o status do conteúdo (vs. "texto/resultado" genérico).

---

## 3. Sistema de Hierarquia Visual de Tags

**Implementação baseada em frequência de uso:**

```
> 10 textos: 2xl, alternando preto (#1A1A1A) e verde floresta (#3A4D39)
> 7 textos:  xl, laranja (#e69019)
> 5 textos:  lg, alternando verde floresta e cinza escuro
> 3 textos:  base, cinza médio
≤ 3 textos:  sm, cinza claro
```

**Quantidade:** 40 tags exibidas (vs. 10 no protótipo original)
**Objetivo:** Criar nuvem visual rica e hierarquizada, facilitando descoberta de conteúdo

---

## 4. Sistema de Navegação Integrado

**Links inteligentes não presentes nos protótipos:**

1. **Tags clicáveis → Acervo filtrado**
   - Home: cada tag na seção "Temáticas" leva ao `/acervo/?tag=slug`

2. **Autores clicáveis → Acervo filtrado**
   - Home: cards de "Autores Mais Lidos" levam ao `/acervo/?autor=id`

3. **Múltiplos pontos de entrada para o acervo:**
   - Hero (home): botão "Acesse nosso acervo"
   - Navbar: link "Acervo"
   - Footer: link "Acervo de Textos"

**Objetivo:** Reduzir fricção na descoberta de conteúdo, criar jornadas fluidas

---

## 5. Sistema de Avatares Automáticos

**Implementação:** Integração com ui-avatars.com

**Funcionamento:**
- Se usuário tem foto: exibe foto de perfil
- Se não tem foto: gera avatar com iniciais automaticamente
- Parâmetros: background=#3A4D39, color=fff, size=128

**Método:** `User.get_avatar_url()` (backend)

**Benefício:** Elimina avatares genéricos/vazios, todos usuários têm representação visual única

---

## 6. HTMX: Uso Extensivo e Estratégico

**Áreas de aplicação (além dos protótipos):**

1. **Filtros do Acervo:**
   - Dropdowns com `hx-get` + `hx-include="#filtros-form"`
   - Atualização assíncrona da lista de textos
   - Preservação de estado na URL (`hx-push-url="true"`)

2. **Paginação dinâmica:**
   - Links com `hx-target="#lista-textos"`
   - Preservação de todos os filtros ativos
   - Loading indicator (`hx-indicator`)

3. **Comentários (Tela 8):**
   - Publicação assíncrona de comentários
   - Exclusão em cascata sem reload
   - Respostas aninhadas recursivas

**Objetivo:** Experiência SPA-like mantendo SSR e SEO

---

## 7. Melhorias de Contraste Visual

**Ajustes implementados:**

1. **Header vs Footer:**
   - Header: `#e8ebe6/95` (tom mais claro)
   - Footer: `#dde0db/95` (tom mais escuro)
   - Resultado: hierarquia visual clara, footer "ancora" a página

2. **Botões:**
   - Ação principal: Verde Floresta (`#3A4D39`)
   - Ação secundária: Laranja (`#e69019`)
   - Ação neutra: Cinza (`#e5e7eb`)

---

## 8. Estrutura de Grid Responsivo

**Home: Layout 2+3 colunas (lg screens):**
- Coluna 1-2 (40%): Autores Mais Lidos (sidebar)
- Coluna 3-5 (60%): Bloco Hero com propósito

**Últimos Textos: Grid 3 colunas (md+), 1 coluna (mobile)**

**Acervo: Filtros em grid 3+4 colunas:**
- Linha 1: Autor, Título, Tema (3 colunas)
- Linha 2: Data Início, Data Fim, Ordenação, Quantidade (4 colunas)

---

## 9. Decisões de UX para Painel Administrativo (FASE 3)

**Implementadas durante planejamento da FASE 3 - Outubro/2025**

### 9.1 Sistema de Convite e Ativação de Autores

**Fluxo de Onboarding:**
1. Admin cadastra novo autor (Tela 11) sem senha
2. Sistema gera token único de ativação (expirável)
3. Link de ativação é **exibido na tela** para admin copiar
4. Admin envia link manualmente ao autor (WhatsApp, email pessoal, etc.)
5. Autor acessa link e visualiza **Página de Boas-Vindas** customizável
6. Autor clica em "Meus Dados de Autor" e define sua senha
7. Status muda de PENDENTE → ATIVO

**Justificativa:** Sem servidor SMTP configurado, sistema permite ativação manual mas mantém segurança e UX profissional.

**Campos opcionais no cadastro:**
- **Pseudônimo:** Se vazio, autor só pode publicar com nome real
- **E-mail de Contato:** Se vazio, ícone de contato não aparece na Galeria de Autores

### 9.2 Sidebar Recolhível para Painéis

**Implementação:**
- Sidebar lateral fixa em **TODAS** as telas de painel (admin + autor)
- Estados: **colapsada** (só ícones) ou **expandida** (ícones + texto)
- Cada opção acompanhada de ícone Heroicon discreto
- Aplicável a: Dashboard, Gestão de Autores, Leitores, Moderação, Gestão de Páginas

**Objetivo:** Navegação consistente e profissional, maximiza espaço útil da tela.

### 9.3 Mensagem de Boas-Vindas Customizável

**Página de Boas-Vindas ao Autor (Tela 11.5):**
- Rota: `/convite/<token>/`
- Conteúdo editável pelo admin via Gestão de Páginas (nova entrada)
- Campos dinâmicos: `{nome}`, `{email}`, `{pseudonimo}`, `{data_cadastro}`
- Inclui manual de instruções do painel_autor
- Link para "Meus Dados de Autor" (primeira edição de perfil + senha)

**Benefício:** Experiência acolhedora e personalizada para novos autores.

### 9.4 Hierarquia de Permissões Administrativas

**Poderes do Admin:**
- ✅ Cadastrar/editar/desativar autores e leitores
- ✅ Excluir ou transformar textos em rascunho (qualquer autor)
- ✅ Excluir comentários (ignorando moderação do autor)
- ✅ Moderar apenas comentários **PENDENTES** (decisão do autor é final)
- ✅ Editar páginas estáticas via Gestão de Páginas
- ✅ Suspender contas de leitores

**Diferença Autores vs Leitores:**
- **Autores:** podem ser "desativados" (perdem acesso ao painel)
- **Leitores:** podem ser "suspensos" (perdem login)

### 9.5 Padronização de Cores nos Protótipos

**Decisão:** Ignorar variações de cores dos protótipos da FASE 3.

**Cores oficiais a usar:**
- Primary: `#e69019` (laranja)
- Verde Floresta: `#3A4D39` (botões primários, borders)
- Background: `#FDFBF6` (pergaminho)
- Sépia: `#4F4A45`

**Protótipos com cores incorretas (verde-oliva):**
- ❌ Tela 12: `#5A663C` → corrigir para `#e69019`
- ❌ Tela 13: `#556B2F` → corrigir para `#e69019`
- ❌ Tela 16: `#556B2F` → corrigir para `#e69019`

### 9.6 Sistema de Exclusão vs Suspensão de Contas

**❌ EXCLUSÃO (Direito ao Esquecimento - LGPD/GDPR):**

**Quem pode excluir:**
- Leitor exclui própria conta (área de configurações)
- Autor exclui própria conta (área de configurações)
- Admin exclui conta de leitor/autor (área administrativa)

**Efeito da exclusão (CASCADE DELETE):**
- 🗑️ Textos do autor → APAGADOS permanentemente
- 🗑️ Comentários do usuário → APAGADOS permanentemente
- 🗑️ Dados pessoais → APAGADOS permanentemente
- 🗑️ Visualizações → APAGADAS permanentemente
- 🗑️ **TUDO relacionado ao usuário é DESTRUÍDO**

**🚫 SUSPENSÃO (Apenas Admin):**

**Efeito da suspensão:**
- Login bloqueado: mensagem "Sua conta foi suspensa. Entre em contato via Fale Conosco"
- Conteúdo ocultado (mas NÃO excluído):
  - Textos do autor suspenso somem das listagens (Home, Acervo, Galeria)
  - Comentários do usuário suspenso somem dos textos
  - URL direta de texto retorna 404 ou "Conteúdo indisponível"
- Dados preservados: tudo permanece no banco, admin pode reativar

**Implementação técnica:**
- Campo `is_active=False` para suspensão (já existe no AbstractUser)
- Filtros: `.filter(autor__is_active=True)` em queries públicas
- CASCADE DELETE configurado em ForeignKeys relacionadas ao User

**🎯 EXCLUSÃO GRANULAR (Apenas Admin):**
- Excluir comentário específico (sem afetar conta)
- Excluir texto específico (sem afetar conta)
- Exclusão pontual, não afeta outros conteúdos

### 9.7 Visibilidade na Área Administrativa

**Listagem mostra TODOS os usuários:**
- Autores ativos + autores suspensos (mesma lista)
- Leitores ativos + leitores suspensos (mesma lista)
- Badge visual diferencia: "Ativo" (verde) vs "Suspenso" (vermelho/laranja)
- Admin pode reativar com um clique → conteúdo volta a aparecer automaticamente

### 9.8 Ações de Suspensão/Reativação

**Botões condicionais na coluna "Ações":**
- **Se usuário ATIVO:** mostra ícone "Suspender" (visibility_off ou toggle_off)
- **Se usuário SUSPENSO:** mostra ícone "Reativar" (visibility_on ou toggle_on)
- Apenas um botão visível por vez (template condicional)
- Ação via HTMX (atualização assíncrona da linha da tabela)

### 9.9 Confirmação de Ações Destrutivas

**Suspender/Reativar:**
- ❌ Sem confirmação (ação imediata via HTMX)
- Justificativa: reversível, não causa perda de dados

**Excluir Leitor:**
- ✅ Modal simples (Alpine.js)
- Botões "Cancelar" e "Confirmar"

**Excluir Autor:**
- ✅ Confirmação FORTE (como em "Minha Conta" de leitores)
- Modal com campo de texto
- Usuário deve digitar **"EXCLUIR"** (em maiúsculas) para confirmar
- Botão "Confirmar" só habilitado se digitou corretamente
- Justificativa: apaga todos os textos (conteúdo crítico da plataforma)

### 9.10 Reenvio de Convite e Reset de Senha

**Botão "Reenviar Convite" (Gestão de Autores):**
- Sempre gera **NOVO token** (invalida tokens anteriores)
- Exibe link copiável na tela (modal ou notificação)
- Admin copia e envia manualmente ao autor

**Dupla função do sistema:**
1. **Primeira ativação:** Autor pendente (nunca definiu senha)
2. **Reset de senha:** Autor ativo que perdeu senha

**Página `/convite/<token>/`:**
- Valida token (existência, expiração, status do autor)
- Se PENDENTE: "Bem-vindo! Defina sua senha"
- Se ATIVO: "Redefina sua senha"
- Ambos levam ao formulário de definição de senha

### 9.11 Edição de Dados pelo Admin

**Formulário de edição de autor (Tela 13):**
- Admin pode editar **TODOS os campos:**
  - Nome, email, telefone, cidade, país
  - Foto, bio
  - Pseudônimo, email de contato
- Formulário = mesmo usado no cadastro (reutilizar)
- Admin NÃO edita senha diretamente (usa "Reenviar Convite" para gerar link de reset)

### 9.12 Exclusão de Conta pelo Próprio Usuário

**Para Leitores (já implementado):**
1. **Minha Conta** (`/contas/minha-conta/`)
   - Grid: Editar Perfil + Sidebar (Alterar Senha + Zona de Perigo)
   - Botão vermelho "Excluir Minha Conta" → tela de confirmação

2. **Excluir Conta** (`/contas/excluir-conta/`)
   - Aviso forte com lista do que será deletado
   - Campo: digitar "EXCLUIR" em maiúsculas
   - Botões: "Cancelar" e "Confirmar Exclusão"
   - `user.delete()` → CASCADE apaga tudo

**Para Autores (criar na FASE 4):**
- Nova tela: "Configurações da Conta" no painel_autor
- Rota: `/autor/configuracoes/`
- Mesmo padrão dos leitores (grid, zona de perigo, confirmação "EXCLUIR")
- Reutilizar template `excluir_conta.html` (já é condicional para autores)

---

**📚 Documentos Relacionados:**
- Roadmap de melhorias pós-MVP em `ROADMAP.md`
- Catálogo de progresso em `PROGRESSO.md`
- Workflow de implementação em `WORKFLOW.md`

**Arquivos Históricos (Fase MVP):**
- Protótipos originais em `prototipos_telas/`
- Especificações das telas em `GUIDELINES.md`
