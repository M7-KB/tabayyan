// Client for POST /api/v1/check (SPEC.md §3, one-pass flow). The user sends the text as typed; the server
// extracts the claims, routes them and answers with one card per claim. The server is the authority: it
// reclassifies level and input kind and validates every card. This module refuses to render any card that
// does not validate against the card contract.

import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import cardSchema from '../../../contracts/card.schema.json'
import { ApiError, postJson } from './http.js'

export const CHECK_PATH = '/api/v1/check'

// One shared API error, so a single catch handles every request.
export const CheckError = ApiError

// The text exactly as the user wrote it. Nothing is trimmed or rewritten on the client.
export function buildCheckRequest({ originalText, locale = 'ar' }) {
  return { original_text: originalText, locale }
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

// Incomplete work is operational status, never a fourth evidence-card state.
function isValidRetryableResult(result) {
  return result && typeof result === 'object' &&
    typeof result.claim_id === 'string' && result.claim_id.trim().length > 0 &&
    typeof result.text_ar === 'string' && result.text_ar.trim().length > 0 &&
    result.code === 'CHECK_INCOMPLETE' && result.retryable === true &&
    typeof result.message_ar === 'string'
}

export function parseCheckResponse(body) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.cards)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  if (!body.cards.every(isValidCard)) {
    throw new CheckError('PIPELINE_DEGRADED')
  }
  if (body.retryable_results !== undefined) {
    if (!Array.isArray(body.retryable_results) || !body.retryable_results.every(isValidRetryableResult)) {
      throw new CheckError('PIPELINE_DEGRADED')
    }
    const ids = [...body.cards.map((card) => card.claim.id), ...body.retryable_results.map((item) => item.claim_id)]
    if (new Set(ids).size !== ids.length) throw new CheckError('PIPELINE_DEGRADED')
  }
  return body
}

export async function postCheck(request, { baseUrl = '', fetchImpl, signal } = {}) {
  const body = await postJson(`${baseUrl}${CHECK_PATH}`, request, { fetchImpl, signal })
  return parseCheckResponse(body)
}
