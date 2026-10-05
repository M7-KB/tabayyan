// API origin for the web build (SPEC.md §3). Set VITE_API_BASE_URL in Cloudflare Pages, without a trailing
// slash. Empty means same-origin requests, which only work when the API serves the web app.
export function normalizeBaseUrl(raw) {
  return (raw ?? '').trim().replace(/\/+$/, '')
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)

// Client deadlines for one request. Extraction has a 30-second server timeout, so the client waits longer
// than that before it gives up and shows the timeout state.
export const EXTRACT_DEADLINE_MS = 45_000
// Owner O4 (2026-10-05): allow five seconds beyond the 35-second server deadline.
export const CHECK_DEADLINE_MS = 40_000
