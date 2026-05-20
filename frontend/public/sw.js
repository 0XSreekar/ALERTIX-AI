const CACHE_NAME = "alertix-offline-v1";
const STATIC_ASSETS = ["/", "/index.html", "/favicon.svg"];
const ALERT_CACHE = "alertix-alert-api-v1";

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/alerts")) {
    event.respondWith(
      fetch(event.request)
        .then(async (response) => {
          const cache = await caches.open(ALERT_CACHE);
          cache.put(event.request, response.clone());
          return response;
        })
        .catch(async () => {
          const cache = await caches.open(ALERT_CACHE);
          return (await cache.match(event.request)) || Response.json({ alerts: [] });
        }),
    );
    return;
  }

  if (event.request.method === "GET") {
    event.respondWith(
      fetch(event.request).catch(async () => {
        const cached = await caches.match(event.request);
        return cached || caches.match("/");
      }),
    );
  }
});
