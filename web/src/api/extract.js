// Client for POST /api/v1/extract (SPEC.md §3, T-501). The server segments the text into claims, classifies
// each level and detects scripture spans. The UI shows the claims for the user to confirm or edit before any
// check runs. Nothing in this response is evidence: it only names what to check.

import { ApiError, postJson } from './http.js'

export const EXTRACT_PATH = '/api/v1/extract'

export function buildExtractRequest(text) {
  return { text }
}

// A response without a usable claims array is PIPELINE_DEGRADED, never a guessed claim list.
export function parseExtractResponse(body) {
  const valid =
    body &&
    typeof body === 'object' &&
    Array.isArray(body.claims) &&
    body.claims.every((claim) => typeof claim?.id === 'string' && typeof claim?.text_ar === 'string')
  if (!valid) throw new ApiError('PIPELINE_DEGRADED')
  return body
}

export async function postExtract(text, { baseUrl = '', fetchImpl, signal } = {}) {
  const body = await postJson(`${baseUrl}${EXTRACT_PATH}`, buildExtractRequest(text), { fetchImpl, signal })
  return parseExtractResponse(body)
}
