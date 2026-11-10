# 📘 CLAUDE.md - Guia do Projeto LIVRE DIA

**Última Atualização:** 05/12/2025 às 20:40
**Último Commit:** `9d1ff0c` (docs: Resumir CLAUDE.md e adicionar regras críticas)

> 🌐 **WEB:** https://livredia.com.br (100% completo)
> 📱 **APP:** Fase 2 (TWA) em andamento

---

## 🚨 REGRAS CRÍTICAS

### 1. Atualizar Documentação
Ao concluir cada tarefa/etapa:
- ✅ Marcar como concluída em **PROGRESSO.md**
- ✅ Marcar como concluída em **ANDROID.md** (se relacionado ao app)
- ✅ Atualizar "Último Commit" neste arquivo

### 2. Comunicação
- Português do Brasil (pt-BR)
- Guiar passo a passo
- Uma tarefa por vez
- Aguardar aprovação explícita

---

## 📱 APP ANDROID - STATUS

| Fase | Status |
|------|--------|
| **Fase 1: PWA** | ✅ CONCLUÍDA (05/12/2025) |
| **Fase 2: TWA** | 🔄 EM ANDAMENTO |

### Fase 2 - Checklist
- [x] Criar conta Google Play Developer ($25) - ⏳ AGUARDANDO VERIFICAÇÃO
- [ ] Configurar Digital Asset Links (assetlinks.json)
- [ ] Gerar APK com Bubblewrap
- [ ] Preparar assets (screenshots, descrição)
- [ ] Publicar na Play Store

> 📋 **Detalhes:** [ANDROID.md](contexto_projeto/ANDROID.md)
> 📊 **Progresso:** [PROGRESSO.md](contexto_projeto/PROGRESSO.md)

---

## 📚 DOCUMENTAÇÃO

| Arquivo | Descrição |
|---------|-----------|
| [ANDROID.md](contexto_projeto/ANDROID.md) | Plano do app (PWA + TWA) |
| [PROGRESSO.md](contexto_projeto/PROGRESSO.md) | Status geral |
| [DESIGN.md](contexto_projeto/DESIGN.md) | Paleta, tipografia |

---

## 🛠️ STACK

- **Backend:** Python 3.13, Django 5.2.7, PostgreSQL 17.4
- **Frontend:** Tailwind CSS, Alpine.js, HTMX
- **Produção:** Hostinger VPS (Ubuntu 25.04)
- **Branches:** `main` (dev) / `prod` (produção)

---

## 🚀 INÍCIO RÁPIDO

```bash
source venv/bin/activate
python manage.py runserver
# http://127.0.0.1:8000/
```

