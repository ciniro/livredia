# 📱 ANDROID.md - Plano de Implementação do App Android

**Projeto:** LIVRE DIA - App Android via PWA + TWA
**Versão:** 1.0
**Criado em:** 05 de Dezembro de 2025
**Status:** Fase 1 CONCLUÍDA ✅ | Fase 2 Pendente

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Fase 1: PWA (Progressive Web App)](#fase-1-pwa-progressive-web-app)
3. [Fase 2: TWA (Trusted Web Activity)](#fase-2-twa-trusted-web-activity)
4. [Configurações Externas](#configurações-externas)
5. [Checklist de Implementação](#checklist-de-implementação)
6. [Referências](#referências)

---

## 🎯 Visão Geral

### Estratégia Escolhida
**PWA + TWA** - Transformar o site existente em Progressive Web App e depois empacotá-lo como Trusted Web Activity para publicação na Google Play Store.

### Benefícios
- ✅ Reutiliza 100% do código Django existente
- ✅ Uma única base de código (web + mobile)
- ✅ Atualizações instantâneas (sem precisar atualizar o app)
- ✅ Menor custo de desenvolvimento e manutenção
- ✅ Presença na Google Play Store
- ✅ Funciona offline (com Service Worker)
- ✅ Notificações push (futuro)

### Resultado Final
- **PWA:** Site instalável diretamente do navegador
- **TWA:** App na Google Play Store que carrega o site em fullscreen

---

## 🌐 Fase 1: PWA (Progressive Web App)

### 1.1 O que é PWA?
Progressive Web App é uma tecnologia que permite transformar um site em um aplicativo instalável, com funcionalidades como:
- Ícone na tela inicial do celular
- Tela de splash ao abrir
- Funciona sem barra de navegador (fullscreen)
- Cache offline
- Notificações push

### 1.2 Requisitos Técnicos
- [x] HTTPS (já implementado em livredia.com.br)
- [ ] Manifest.json (metadados do app)
- [ ] Service Worker (cache e offline)
- [ ] Ícones em múltiplos tamanhos
- [ ] Meta tags específicas

### 1.3 Implementação

#### 1.3.1 Criar Manifest.json
Arquivo: `static/manifest.json`

```json
{
  "name": "Livre Dia",
  "short_name": "Livre Dia",
  "description": "Plataforma de curadoria de textos humanos autênticos",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FDFBF6",
  "theme_color": "#e69019",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/static/img/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/img/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/static/img/screenshots/screenshot-mobile.png",
      "sizes": "1080x1920",
      "type": "image/png",
      "form_factor": "narrow"
    }
  ],
  "categories": ["books", "education", "lifestyle"],
  "lang": "pt-BR",
  "dir": "ltr"
}
```

#### 1.3.2 Criar Service Worker
Arquivo: `static/js/service-worker.js`

```javascript
const CACHE_NAME = 'livredia-v1';
const urlsToCache = [
  '/',
  '/static/css/output.css',
  '/static/img/logo.png',
  '/offline/'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

// Intercepta requisições
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Retorna do cache ou busca na rede
        return response || fetch(event.request);
      })
      .catch(() => {
        // Se offline e não em cache, mostra página offline
        if (event.request.mode === 'navigate') {
          return caches.match('/offline/');
        }
      })
  );
});

// Atualização do cache
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((cacheName) => {
          return cacheName !== CACHE_NAME;
        }).map((cacheName) => {
          return caches.delete(cacheName);
        })
      );
    })
  );
});
```

#### 1.3.3 Atualizar base.html
Adicionar no `<head>`:

```html
<!-- PWA Manifest -->
<link rel="manifest" href="{% static 'manifest.json' %}">

<!-- PWA Meta Tags -->
<meta name="theme-color" content="#e69019">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Livre Dia">

<!-- Apple Touch Icons -->
<link rel="apple-touch-icon" href="{% static 'img/icons/icon-152x152.png' %}">

<!-- Splash Screens iOS (opcional) -->
<link rel="apple-touch-startup-image" href="{% static 'img/splash/splash.png' %}">
```

Adicionar antes de `</body>`:

```html
<!-- Service Worker Registration -->
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js')
        .then((registration) => {
          console.log('SW registrado:', registration.scope);
        })
        .catch((error) => {
          console.log('SW erro:', error);
        });
    });
  }
</script>
```

#### 1.3.4 Criar Ícones do App
Tamanhos necessários (criar a partir do logo existente):
- 72x72, 96x96, 128x128, 144x144, 152x152, 192x192, 384x384, 512x512

Local: `static/img/icons/`

#### 1.3.5 Criar Página Offline
Template: `templates/core/offline.html`
URL: `/offline/`

Página simples exibida quando o usuário está offline.

#### 1.3.6 Configurar URL do Service Worker
Em `config/urls.py`, adicionar rota para servir o service worker da raiz:

```python
from django.views.generic import TemplateView

urlpatterns = [
    # ... outras URLs
    path('service-worker.js', TemplateView.as_view(
        template_name='service-worker.js',
        content_type='application/javascript'
    ), name='service-worker'),
]
```

### 1.4 Testes do PWA

#### Lighthouse (Chrome DevTools)
1. Abrir Chrome DevTools (F12)
2. Ir na aba "Lighthouse"
3. Selecionar "Progressive Web App"
4. Rodar auditoria
5. Meta: Score > 90

#### Teste de Instalação
1. Acessar livredia.com.br no Chrome mobile
2. Deve aparecer banner "Adicionar à tela inicial"
3. Ou: Menu (⋮) → "Instalar aplicativo"

---

## 📦 Fase 2: TWA (Trusted Web Activity)

### 2.1 O que é TWA?
Trusted Web Activity permite empacotar um PWA como um app Android nativo, publicável na Google Play Store. O app usa o Chrome para renderizar o site, mas em modo fullscreen (sem barra de navegação).

### 2.2 Pré-requisitos
- [x] PWA funcionando (Fase 1 completa)
- [ ] Conta Google Play Developer ($25)
- [ ] Android Studio instalado
- [ ] Java JDK 11+
- [ ] Verificação Digital Asset Links

### 2.3 Criar Conta Google Play Developer

**Passo a passo:**

1. **Acessar:** https://play.google.com/console/signup
2. **Fazer login** com conta Google pessoal ou criar nova
3. **Aceitar termos** de desenvolvedor
4. **Pagar taxa:** $25 USD (pagamento único, para sempre)
5. **Preencher perfil:**
   - Nome do desenvolvedor: "Ciniro Nametala" ou "Livre Dia"
   - Email de contato público
   - Site: https://livredia.com.br
6. **Verificar identidade** (pode levar alguns dias)

### 2.4 Configurar Digital Asset Links

#### 2.4.1 O que é?
Digital Asset Links é um arquivo JSON que prova que você é dono do site E do app. Necessário para o TWA funcionar em modo fullscreen.

#### 2.4.2 Gerar assinatura do app
Ao criar o app no Android Studio, será gerada uma keystore. Você precisará do fingerprint SHA-256.

```bash
# Após criar keystore, obter fingerprint:
keytool -list -v -keystore sua-keystore.jks -alias sua-alias
```

#### 2.4.3 Criar arquivo assetlinks.json
Local: `static/.well-known/assetlinks.json`

```json
[{
  "relation": ["delegate_permission/common.handle_all_urls"],
  "target": {
    "namespace": "android_app",
    "package_name": "com.livredia.app",
    "sha256_cert_fingerprints": [
      "XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX"
    ]
  }
}]
```

#### 2.4.4 Servir assetlinks.json
Configurar nginx ou Django para servir:
`https://livredia.com.br/.well-known/assetlinks.json`

### 2.5 Criar Projeto TWA

#### Opção A: Bubblewrap (Recomendado - mais simples)
Ferramenta oficial do Google para criar TWA.

```bash
# Instalar
npm install -g @anthropic/anthropic

# Criar projeto
bubblewrap init --manifest=https://livredia.com.br/static/manifest.json

# Responder perguntas:
# - Package name: com.livredia.app
# - App name: Livre Dia
# - Launcher name: Livre Dia
# - Theme color: #e69019
# - Background color: #FDFBF6
# - Start URL: https://livredia.com.br
# - Signing key: criar nova ou usar existente

# Gerar APK
bubblewrap build
```

#### Opção B: Android Studio (mais controle)
1. Criar novo projeto Android
2. Adicionar dependência TWA
3. Configurar manifest
4. Build APK/AAB

### 2.6 Publicar na Google Play Store

#### 2.6.1 Preparar assets
- **Ícone:** 512x512 PNG
- **Feature Graphic:** 1024x500 PNG
- **Screenshots:** Mínimo 2, recomendado 8
  - Telefone: 1080x1920 ou 1920x1080
- **Descrição curta:** Até 80 caracteres
- **Descrição completa:** Até 4000 caracteres

#### 2.6.2 Descrição sugerida

**Título:** Livre Dia - Textos Humanos Autênticos

**Descrição curta:**
Descubra textos autênticos de autores brasileiros com Selo Livre de IA.

**Descrição completa:**
Livre Dia é uma plataforma de curadoria de textos humanos autênticos — crônicas, poesias, ensaios e muito mais — escritos por autores verificados.

✨ CARACTERÍSTICAS:
• Textos 100% escritos por humanos, com Selo Livre de IA
• Autores contemporâneos e clássicos da literatura brasileira
• Leitura sem anúncios ou distrações
• Sistema de favoritos e listas de leitura
• Descubra novos autores e acompanhe seus favoritos
• Modo escuro para leitura noturna

📚 CONTEÚDO:
• Crônicas do cotidiano
• Poesias e sonetos
• Ensaios e reflexões
• Textos clássicos em domínio público
• Novos textos toda semana

🌟 PARA LEITORES:
• Crie sua conta gratuita
• Salve textos favoritos
• Siga autores preferidos
• Comente e interaja
• Personalize sua experiência

✍️ PARA AUTORES:
• Publique seus textos originais
• Alcance leitores engajados
• Receba feedback da comunidade
• Selo Livre de IA em suas obras

Livre Dia — Onde a literatura encontra autenticidade.

#### 2.6.3 Categorização
- **Categoria:** Livros e referências
- **Classificação:** Livre (ou 10+ dependendo do conteúdo)
- **Tags:** literatura, leitura, livros, poesia, textos, autores brasileiros

#### 2.6.4 Processo de submissão
1. Acessar Google Play Console
2. Criar novo app
3. Preencher ficha da loja
4. Fazer upload do AAB (Android App Bundle)
5. Preencher questionário de classificação
6. Configurar preço (Gratuito)
7. Enviar para revisão
8. Aguardar aprovação (1-7 dias)

---

## ⚙️ Configurações Externas

### Google Play Developer Account
- **URL:** https://play.google.com/console
- **Custo:** $25 USD (único)
- **Tempo para aprovação:** 24-48h após pagamento

### Ferramentas Necessárias
- **Android Studio:** https://developer.android.com/studio
- **Node.js:** Para usar Bubblewrap
- **Java JDK 11+:** Para compilar o app

### Verificações de Domínio
- Digital Asset Links configurado
- HTTPS funcionando
- manifest.json acessível

---

## ✅ Checklist de Implementação

### Fase 1: PWA ✅ CONCLUÍDA
- [x] 1.1 Criar pasta `static/img/icons/`
- [x] 1.2 Gerar ícones em todos os tamanhos (72 até 512px)
- [x] 1.3 Criar `static/manifest.json`
- [x] 1.4 Criar `templates/core/service-worker.js` (template Django)
- [x] 1.5 Criar template `templates/core/offline.html`
- [x] 1.6 Criar view e URL para página offline
- [x] 1.7 Configurar URL para service-worker.js na raiz
- [x] 1.8 Atualizar `base.html` com meta tags PWA
- [x] 1.9 Atualizar `base.html` com registro do Service Worker
- [x] 1.10 Fazer deploy e testar em produção
- [x] 1.11 Rodar Lighthouse (Acessibilidade 91, SEO 100, Práticas 100)
- [x] 1.12 Testar instalação no Android - APROVADO (05/12/2025)

### Fase 2: TWA (Em Andamento)
- [x] 2.1 Criar conta Google Play Developer ($25) - ⏳ AGUARDANDO VERIFICAÇÃO (05/12/2025)
- [ ] 2.2 Instalar Android Studio
- [ ] 2.3 Instalar Bubblewrap (npm)
- [ ] 2.4 Gerar keystore e obter fingerprint SHA-256
- [ ] 2.5 Criar `assetlinks.json` com fingerprint
- [ ] 2.6 Configurar nginx para servir `.well-known/assetlinks.json`
- [ ] 2.7 Fazer deploy do assetlinks.json
- [ ] 2.8 Gerar projeto TWA com Bubblewrap
- [ ] 2.9 Testar APK em dispositivo real
- [ ] 2.10 Preparar assets para Play Store (ícones, screenshots, descrição)
- [ ] 2.11 Criar ficha do app na Play Console
- [ ] 2.12 Fazer upload do AAB
- [ ] 2.13 Preencher questionário de classificação
- [ ] 2.14 Submeter para revisão
- [ ] 2.15 App publicado na Play Store! 🎉

---

## 📚 Referências

### Documentação Oficial
- [PWA - web.dev](https://web.dev/progressive-web-apps/)
- [TWA - Chrome Developers](https://developer.chrome.com/docs/android/trusted-web-activity/)
- [Bubblewrap](https://github.com/AntDroidSecurity/AntDroid-Bubblewrap/AntDroid-Bubblewrap)
- [Digital Asset Links](https://developers.google.com/digital-asset-links)
- [Google Play Console](https://play.google.com/console)

### Ferramentas Úteis
- [PWA Builder](https://www.pwabuilder.com/) - Gera manifest e SW automaticamente
- [Lighthouse](https://developers.google.com/web/tools/lighthouse) - Auditoria PWA
- [Maskable.app](https://maskable.app/) - Editor de ícones maskable
- [Real Favicon Generator](https://realfavicongenerator.net/) - Gera todos os tamanhos de ícone

---

## 📝 Notas de Implementação

### 05 de Dezembro de 2025 - Implementação do PWA (Fase 1)

**Arquivos criados:**
- `static/img/icons/` - 8 ícones PNG (72, 96, 128, 144, 152, 192, 384, 512px)
- `static/manifest.json` - Metadados do app PWA
- `templates/core/service-worker.js` - Service Worker como template Django
- `templates/core/offline.html` - Página offline

**Arquivos modificados:**
- `apps/core/views.py` - Adicionada `OfflineView`
- `apps/core/urls.py` - Adicionada rota `/offline/`
- `config/urls.py` - Adicionada rota `/service-worker.js` na raiz
- `templates/base.html` - Meta tags PWA e registro do SW

**Decisões técnicas:**
1. **Service Worker como template Django:** Colocado em `templates/core/` ao invés de `static/js/` para permitir uso de variáveis Django no futuro (como `{% static %}`). Servido pela raiz via `TemplateView` com content-type `application/javascript`.

2. **Estratégia de cache:** Network First com fallback para cache. Assim o usuário sempre vê a versão mais recente quando online, mas tem conteúdo disponível quando offline.

3. **Ícones gerados via rsvg-convert:** Usamos o favicon.svg (1000x1000) como fonte e o comando `rsvg-convert` (Homebrew) para gerar os 8 tamanhos necessários.

**Próximos passos:**
- Fazer deploy para produção
- Testar Lighthouse score
- Testar instalação em dispositivo Android

---

**Última atualização:** 05 de Dezembro de 2025
