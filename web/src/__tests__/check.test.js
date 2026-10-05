import { describe, expect, it, vi } from 'vitest'
import { CHECK_PATH, CheckError, buildCheckRequest, parseCheckResponse, postCheck } from '../api/check.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'
import cannotConfirm from '../../../contracts/fixtures/cannot-confirm.json'

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

describe('buildCheckRequest (one-pass)', () => {
  it('sends the text as the user wrote it, with the locale and no claims', () => {
    const originalText = '  هل القرآن من تأليف محمد؟\n'
    expect(buildCheckRequest({ originalText })).toEqual({ original_text: originalText, locale: 'ar' })
  })

  it('sends no claim list, level or input kind; the server extracts them', () => {
    const request = buildCheckRequest({ originalText: 'نص' })
    expect(request).not.toHaveProperty('claims')
    expect(request).not.toHaveProperty('input_kind')
    expect(request).not.toHaveProperty('level')
  })
})

describe('parseCheckResponse', () => {
  const incomplete = { claim_id: 'pending', text_ar: 'نص تجريبي', code: 'CHECK_INCOMPLETE', retryable: true, message_ar: 'not displayed' }

  it('accepts completed cards alongside unfinished claims without inventing a card state', () => {
    const body = { cards: [supportedConfirms], retryable_results: [incomplete] }
    expect(parseCheckResponse(body)).toBe(body)
    expect(parseCheckResponse({ cards: [], retryable_results: [incomplete] }).cards).toEqual([])
  })

  it.each([
    null,
    {},
    [null],
    [{ ...incomplete, code: 'CANNOT_CONFIRM' }],
    [{ ...incomplete, retryable: false }],
    [{ ...incomplete, text_ar: '' }],
    [{ ...incomplete, claim_id: '' }],
    [{ ...incomplete, message_ar: {} }],
    [incomplete, incomplete],
    [{ ...incomplete, claim_id: supportedConfirms.claim.id }],
  ])('rejects malformed or duplicate unfinished results: %j', (retryable_results) => {
    expect(() => parseCheckResponse({ cards: [supportedConfirms], retryable_results })).toThrow(CheckError)
  })

  it('accepts a body whose cards carry the fields the UI reads', () => {
    const body = { cards: [supportedConfirms] }
    expect(parseCheckResponse(body, ['c1'])).toBe(body)
  })

  it('rejects a body without a cards array', () => {
    expect(() => parseCheckResponse({}, ['c1'])).toThrow(CheckError)
    expect(() => parseCheckResponse(null, ['c1'])).toThrow(CheckError)
  })

  it('rejects a card with the wrong number of verify lines (never a best-effort card)', () => {
    const broken = { ...supportedConfirms, how_to_verify_ar: ['سطر واحد فقط'] }
    try {
      parseCheckResponse({ cards: [broken] }, ['c1'])
      expect.unreachable('parseCheckResponse should have thrown')
    } catch (error) {
      expect(error).toBeInstanceOf(CheckError)
      expect(error.code).toBe('PIPELINE_DEGRADED')
    }
  })
})

function cloneCard(card) {
  return structuredClone(card)
}

async function checkWithCard(card) {
  const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { cards: [card] }))
  return postCheck(buildCheckRequest({ originalText: 'نص' }), { fetchImpl })
}

describe('card contract validation (SPEC.md §3, A12)', () => {
  it('accepts a nested correction notice whose evidence is verbatim-verified', async () => {
    const result = await checkWithCard(cannotConfirm)
    expect(result.cards[0].misquote_notice.evidence.verbatim_verified).toBe(true)
  })

  it('rejects a nested correction notice whose evidence is not verbatim-verified', async () => {
    const card = cloneCard(cannotConfirm)
    card.misquote_notice.evidence.verbatim_verified = false
    await expect(checkWithCard(card)).rejects.toMatchObject({ code: 'PIPELINE_DEGRADED' })
  })

  it('rejects null evidence on a card', async () => {
    const card = cloneCard(supportedConfirms)
    card.evidence = [null]
    await expect(checkWithCard(card)).rejects.toMatchObject({ code: 'PIPELINE_DEGRADED' })
  })

  it('rejects an object where a verify line string belongs', async () => {
    const card = cloneCard(supportedConfirms)
    card.how_to_verify_ar = [{ text: 'سطر' }, 'سطر ثانٍ']
    await expect(checkWithCard(card)).rejects.toMatchObject({ code: 'PIPELINE_DEGRADED' })
  })

  it('rejects evidence whose verbatim_verified is false, even on a top-level card', async () => {
    const card = cloneCard(supportedConfirms)
    card.evidence[0].verbatim_verified = false
    await expect(checkWithCard(card)).rejects.toMatchObject({ code: 'PIPELINE_DEGRADED' })
  })
})

describe('postCheck', () => {
  it('POSTs JSON to the check path and returns the parsed cards', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { cards: [supportedConfirms] }))
    const request = buildCheckRequest({ originalText: 'نص' })

    const result = await postCheck(request, { baseUrl: 'https://api.example.invalid', fetchImpl })

    expect(fetchImpl).toHaveBeenCalledWith(
      `https://api.example.invalid${CHECK_PATH}`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      }),
    )
    expect(result.cards).toHaveLength(1)
  })

  it('maps the server error code from the error envelope', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(503, { error: { code: 'PIPELINE_DEGRADED', message_ar: '…', message_en: '…' } }),
      )
    await expect(postCheck(buildCheckRequest({ originalText: 'نص' }), { fetchImpl })).rejects.toMatchObject({
      code: 'PIPELINE_DEGRADED',
      status: 503,
    })
  })

  it('falls back to UNKNOWN when the error body is not JSON', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('not json')
      },
    })
    await expect(postCheck(buildCheckRequest({ originalText: 'نص' }), { fetchImpl })).rejects.toMatchObject({
      code: 'UNKNOWN',
      status: 502,
    })
  })

  it('reports a network failure as NETWORK', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(postCheck(buildCheckRequest({ originalText: 'نص' }), { fetchImpl })).rejects.toMatchObject({
      code: 'NETWORK',
    })
  })

  it('treats a 200 with an unrenderable card as PIPELINE_DEGRADED', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { cards: [{ state: 'SUPPORTED' }] }))
    await expect(postCheck(buildCheckRequest({ originalText: 'نص' }), { fetchImpl })).rejects.toMatchObject({
      code: 'PIPELINE_DEGRADED',
    })
  })
})
