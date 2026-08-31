// Tauri doesn't have a Node.js server to do proper SSR
// so we use adapter-static with a fallback to index.html to put the site in SPA mode.
// Prerender `/` so asset paths are relative (required for Tauri production webview).
export const ssr = false;
export const prerender = true;
