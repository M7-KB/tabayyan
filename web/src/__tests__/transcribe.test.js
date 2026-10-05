import { describe, expect, it } from 'vitest'
import { MAX_MEDIA_BYTES, MediaError, transcribeStub, validateMediaFile } from '../api/transcribe.js'
import { strings } from '../strings.js'

function fileOf(type, size = 1024) {
  const file = new File(['x'], 'clip', { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

function codeOf(fn) {
  try {
    fn()
  } catch (error) {
    return error instanceof MediaError ? error.code : 'OTHER'
  }
  return null
}

describe('validateMediaFile', () => {
  it('accepts audio and video, and a blank MIME type left to the server', () => {
    expect(codeOf(() => validateMediaFile(fileOf('audio/mpeg')))).toBeNull()
    expect(codeOf(() => validateMediaFile(fileOf('video/mp4')))).toBeNull()
    expect(codeOf(() => validateMediaFile(fileOf('')))).toBeNull()
  })

  it('refuses a non-media MIME type', () => {
    expect(codeOf(() => validateMediaFile(fileOf('text/plain')))).toBe('UNSUPPORTED_MEDIA')
    expect(codeOf(() => validateMediaFile(fileOf('image/png')))).toBe('UNSUPPORTED_MEDIA')
  })

  it('refuses a file over 25 MB and accepts one at the limit', () => {
    expect(MAX_MEDIA_BYTES).toBe(25 * 1024 * 1024)
    expect(codeOf(() => validateMediaFile(fileOf('audio/mpeg', MAX_MEDIA_BYTES)))).toBeNull()
    expect(codeOf(() => validateMediaFile(fileOf('audio/mpeg', MAX_MEDIA_BYTES + 1)))).toBe('MEDIA_TOO_LARGE')
  })
})

describe('transcribeStub', () => {
  it('returns labelled sample text with no segments and never reads the file', async () => {
    const result = await transcribeStub(fileOf('audio/mpeg'))
    expect(result).toEqual({ transcript_ar: strings.transcriptStubText, segments: [], stub: true })
  })

  it('rejects an invalid file before returning anything', async () => {
    await expect(transcribeStub(fileOf('text/plain'))).rejects.toMatchObject({ code: 'UNSUPPORTED_MEDIA' })
  })
})

describe('transcribe error copy', () => {
  it('has a next step for every code the client can raise', () => {
    for (const code of ['CONSENT_REQUIRED', 'MEDIA_TOO_LONG', 'MEDIA_TOO_LARGE', 'UNSUPPORTED_MEDIA', 'TRANSCRIBE_UNAVAILABLE', 'NETWORK', 'UNKNOWN']) {
      expect(strings.transcribeErrors[code]).toBeTruthy()
    }
  })
})
