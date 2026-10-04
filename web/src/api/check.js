// Client for POST /api/v1/check (SPEC.md §3). The server is the authority: it reclassifies level and
// input kind and validates every card. This module only sends what the user confirmed and refuses to
// render a response that does not have the minimum card shape.

export const CHECK_PATH = '/api/v1/check'

export class CheckError extends Error {
  constructor(code, status = null) {
    super(code)
    this.name = 'CheckError'
    this.code = code
    this.status = status
  }
}

// Only the fields the user confirmed. `level`, `input_kind` and `scripture_spans` are advisory on the
// server, so they are sent only when present and the server still takes the more restrictive value.
function toWireClaim({ id, text_ar: textAr, level }) {
  return level ? { id, text_ar: textAr, level } : { id, text_ar: textAr }
}

export function buildCheckRequest({ claims, inputKind, segments, locale = 'ar' }) {
  const request = { claims: claims.map(toWireClaim), locale }
  if (inputKind) request.input_kind = inputKind
  if (segments && segments.length > 0) request.segments = segments
  return request
}

// A card must carry the fields the UI reads. Anything less is treated as a degraded pipeline (SPEC.md
// §3: never a best-effort card).
export function isRenderableCard(card) {
  return (
    card !== null &&
    typeof card === 'object' &&
    typeof card.state === 'string' &&
    typeof card.state_label_key === 'string' &&
    card.claim !== null &&
    typeof card.claim === 'object' &&
    typeof card.claim.text_original === 'string' &&
    Array.isArray(card.evidence) &&
    Array.isArray(card.how_to_verify_ar) &&
    card.how_to_verify_ar.length === 2
  )
}

export function parseCheckResponse(body) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.cards)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  if (!body.cards.every(isRenderableCard)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  return body
}

export async function postCheck(request, { baseUrl = '', fetchImpl = globalThis.fetch, signal } = {}) {
  let response
  try {
    response = await fetchImpl(`${baseUrl}${CHECK_PATH}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    })
  } catch {
    throw new CheckError('NETWORK')
  }

  if (!response.ok) {
    let code = 'UNKNOWN'
    try {
      const errorBody = await response.json()
      if (typeof errorBody?.error?.code === 'string') code = errorBody.error.code
    } catch {
      // A non-JSON error body keeps the generic code; the body is never shown to the user.
    }
    throw new CheckError(code, response.status)
  }

  let body
  try {
    body = await response.json()
  } catch {
    throw new CheckError('PIPELINE_DEGRADED', response.status)
  }
  return parseCheckResponse(body)
}
