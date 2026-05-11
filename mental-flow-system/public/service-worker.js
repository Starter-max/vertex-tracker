const CACHE='mental-flow-v1';
self.addEventListener('install', e=>{ e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/','/review','/buckets','/settings','/manifest.json']))); self.skipWaiting(); });
self.addEventListener('activate', e=>{ e.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', e=>{ if (e.request.method !== 'GET') return; e.respondWith(caches.match(e.request).then(r=>r || fetch(e.request).catch(()=>caches.match('/')))); });
