// Minimal service worker so Friday can be installed as an app. It caches nothing:
// Friday always needs its server, and stale API answers would be wrong.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
