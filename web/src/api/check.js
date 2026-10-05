// Client for POST /api/v1/check (SPEC.md §3). The server is the authority: it reclassifies level and
// input kind and validates every card. This module sends only what the user confirmed and refuses to
// render any card that does not validate against the card contract.

import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import cardSchema from '../../../contracts/card.schema.json'
import { ApiError, postJson } from './http.js'

export const CHECK_PATH = '/api/v1/check'

// One shared API error, so a single catch handles extract and check failures.
export const CheckError = ApiError

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

// Every card is checked against contracts/card.schema.json (SPEC.md §3, A12) before it can reach the UI.
// The schema is the contract, so the client uses the same file as the server test suite. Anything that
// does not validate, including nested evidence and misquote notices, is treated as PIPELINE_DEGRADED.
const cardValidator = new Ajv2020({ allErrors: false, strict: false })
addFormats(cardValidator)
const validateCardSchema = cardValidator.compile(cardSchema)

export function isValidCard(card) {
  return validateCardSchema(card) === true
}

// The server may split one confirmed claim into children whose ids are `<claim id>:<child id>`.
// The longest matching confirmed id wins, so an exact match is always preferred.
function confirmedIdOf(claimId, confirmedIds) {
  if (confirmedIds.has(claimId)) return claimId
  let owner = null
  for (const id of confirmedIds) {
    if (claimId.startsWith(`${id}:`) && (owner === null || id.length > owner.length)) owner = id
  }
  return owner
}

// The response must cover every confirmed claim. A card for an unknown claim, or a second card for the same
// claim id, fails the whole response, so the UI never shows a partial or mixed result.
export function coversConfirmedClaims(cards, confirmedIds) {
  const confirmed = new Set(confirmedIds)
  const covered = new Set()
  const seenClaimIds = new Set()

  for (const card of cards) {
    const owner = confirmedIdOf(card.claim.id, confirmed)
    if (owner === null) return false
    if (seenClaimIds.has(card.claim.id)) return false
    seenClaimIds.add(card.claim.id)
    covered.add(owner)
  }

  return [...confirmed].every((id) => covered.has(id))
}

export function parseCheckResponse(body, confirmedIds) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.cards)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  if (!body.cards.every(isValidCard) || !coversConfirmedClaims(body.cards, confirmedIds)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  return body
}

export async function postCheck(request, { baseUrl = '', fetchImpl, signal } = {}) {
  const body = await postJson(`${baseUrl}${CHECK_PATH}`, request, { fetchImpl, signal })
  return parseCheckResponse(body, request.claims.map((claim) => claim.id))
}
