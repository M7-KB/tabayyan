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

export function parseCheckResponse(body) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.cards)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  if (!body.cards.every(isValidCard)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  return body
}

export async function postCheck(request, { baseUrl = '', fetchImpl, signal } = {}) {
  const body = await postJson(`${baseUrl}${CHECK_PATH}`, request, { fetchImpl, signal })
  return parseCheckResponse(body)
}
