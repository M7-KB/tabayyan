import { describe, expect, it, vi } from 'vitest'
import { EXTRACT_PATH, buildExtractRequest, parseExtractResponse, postExtract } from '../api/extract.js'
import { ApiError } from '../api/http.js'

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

const extraction = {
  detected_lang: 'ar',
  input_kind: 'claim',
  claims: [{ id: 'c1', text_ar: 'نص الادعاء', span: { start: 0, end: 9 }, level: 'B' }],
  dropped_count: 0,
  no_checkable_claim: false,
}

describe('buildExtractRequest', () => {
  it('sends the text as the only field', () => {
    expect(buildExtractRequest('نص')).toEqual({ text: 'نص' })
  })
})

describe('parseExtractResponse', () => {
  it('accepts a body with a claims array of id and text pairs', () => {
    expect(parseExtractResponse(extraction)).toBe(extraction)
  })

  it('accepts an empty claims list, which the screen shows as its own state', () => {
    expect(parseExtractResponse({ ...extraction, claims: [] }).claims).toEqual([])
  })

  it('rejects a body without a claims array as PIPELINE_DEGRADED', () => {
    expect(() => parseExtractResponse({})).toThrow(ApiError)
    expect(() => parseExtractResponse(null)).toThrow(ApiError)
    expect(() => parseExtractResponse({ claims: 'nope' })).toThrow(ApiError)
    expect(() => parseExtractResponse({ claims: 'nope' })).toThrow(/PIPELINE_DEGRADED/)
  })

  it('rejects a claim without a string id or text_ar', () => {
    expect(() => parseExtractResponse({ claims: [{ id: 'c1' }] })).toThrow(ApiError)
    expect(() => parseExtractResponse({ claims: [{ text_ar: 'نص' }] })).toThrow(ApiError)
  })
})

describe('postExtract', () => {
  it('posts the text to the extract path under the base URL and returns the parsed body', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(200, extraction))
    const result = await postExtract('نص', { baseUrl: 'https://api.example', fetchImpl })

    expect(result).toEqual(extraction)
    const [url, init] = fetchImpl.mock.calls[0]
    expect(url).toBe(`https://api.example${EXTRACT_PATH}`)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ text: 'نص' })
  })

  it('maps the server error code and status without showing the body', async () => {
    const fetchImpl = vi.fn(async () =>
      jsonResponse(422, { error: { code: 'TEXT_NOT_SUPPORTED_LANG', message_en: 'raw detail' } }),
    )
    await expect(postExtract('نص', { fetchImpl })).rejects.toMatchObject({
      code: 'TEXT_NOT_SUPPORTED_LANG',
      status: 422,
    })
  })

  it('keeps the generic code when the error body is not JSON', async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: false,
      status: 502,
      json: async () => {
        throw new SyntaxError('not json')
      },
    }))
    await expect(postExtract('نص', { fetchImpl })).rejects.toMatchObject({ code: 'UNKNOWN', status: 502 })
  })

  it('reports NETWORK when the request never completes', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(postExtract('نص', { fetchImpl })).rejects.toMatchObject({ code: 'NETWORK' })
  })

  it('reports PIPELINE_DEGRADED when a 200 body is not the extract shape', async () => {
    const fetchImpl = vi.fn(async () => jsonResponse(200, { unexpected: true }))
    await expect(postExtract('نص', { fetchImpl })).rejects.toMatchObject({ code: 'PIPELINE_DEGRADED' })
  })
})
