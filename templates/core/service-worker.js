// Service Worker para Livre Dia PWA
// Versão: 1.0.0

const CACHE_NAME = 'livredia-v1';
const OFFLINE_URL = '/offline/';

// Recursos essenciais para cache inicial
const PRECACHE_URLS = [
  '/',
  '/offline/',
  '/static/css/output.css',
  '/static/img/favicon.svg',
  '/static/img/icons/icon-192x192.png',
  '/static/img/icons/icon-512x512.png',
  '/static/manifest.json'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Cache aberto, adicionando recursos...');
        return cache.addAll(PRECACHE_URLS);
      })
      .then(() => {
        console.log('[SW] Recursos em cache!');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Erro ao fazer cache:', error);
      })
  );
});

// Ativação do Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Ativando Service Worker...');
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => cacheName !== CACHE_NAME)
            .map((cacheName) => {
              console.log('[SW] Removendo cache antigo:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service Worker ativado!');
        return self.clients.claim();
      })
  );
});

// Intercepta requisições (estratégia: Network First, fallback para Cache)
self.addEventListener('fetch', (event) => {
  // Ignora requisições não-GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Ignora requisições para outros domínios
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Ignora requisições para admin, api, etc.
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/admin/') ||
      url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/__debug__/')) {
    return;
  }

  event.respondWith(
    // Tenta buscar da rede primeiro
    fetch(event.request)
      .then((response) => {
        // Se a resposta for válida, salva no cache
        if (response && response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME)
            .then((cache) => {
              cache.put(event.request, responseToCache);
            });
        }
        return response;
      })
      .catch(() => {
        // Se a rede falhar, tenta o cache
        return caches.match(event.request)
          .then((cachedResponse) => {
            if (cachedResponse) {
              return cachedResponse;
            }
            // Se não estiver no cache e for uma navegação, mostra página offline
            if (event.request.mode === 'navigate') {
              return caches.match(OFFLINE_URL);
            }
            // Para outros recursos, retorna erro
            return new Response('Recurso não disponível offline', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
      })
  );
});

// Listener para mensagens (útil para atualizações futuras)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
