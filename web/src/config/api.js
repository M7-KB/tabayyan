// API origin for the web build (SPEC.md §3). Set VITE_API_BASE_URL in Cloudflare Pages, without a trailing
// slash. Empty means same-origin requests, which only work when the API serves the web app.
export function normalizeBaseUrl(raw) {
  return (raw ?? '').trim().replace(/\/+$/, '')
}

export const API_BASE_URL = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL)

// Client deadlines for one request. Extraction has a 30-second server timeout, so the client waits longer
// than that before it gives up and shows the timeout state.
export const EXTRACT_DEADLINE_MS = 45_000
// Build-time override in milliseconds; keep it above CHECK_DEADLINE_SECONDS on the server.
export function checkDeadlineMs(raw) {
  const value = Number(raw)
  return Number.isFinite(value) && value > 0 ? value : 65_000
}

export const CHECK_DEADLINE_MS = checkDeadlineMs(import.meta.env.VITE_CHECK_DEADLINE_MS)
