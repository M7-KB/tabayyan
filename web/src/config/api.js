// API origin for the web build (SPEC.md §3). Set VITE_API_BASE_URL in Cloudflare Pages, without a trailing
// slash. Empty means same-origin requests, which only work when the API serves the web app.
export function normalizeBaseUrl(raw) {
  return (raw ?? '').trim().replace(/\/+$/, '')
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)
