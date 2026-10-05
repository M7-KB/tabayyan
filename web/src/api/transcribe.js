// Client-side checks and the transcription stand-in for POST /api/v1/transcribe (SPEC.md §3, §6.6).
// The real endpoint is not called yet. transcribeStub is used until Vegapunk's transcription contract
// lands; then it is replaced by a request that sends `media` and `consent=true` as multipart/form-data.

import { strings } from '../strings.js'

export const MAX_MEDIA_BYTES = 25 * 1024 * 1024

export class MediaError extends Error {
  constructor(code) {
    super(code)
    this.name = 'MediaError'
    this.code = code
  }
}

// Refuses a file before any request is made. An empty MIME type is allowed through, because some
// platforms leave it blank for valid audio; the server stays the authority on the format.
export function validateMediaFile(file) {
  if (file.type && !file.type.startsWith('audio/') && !file.type.startsWith('video/')) {
    throw new MediaError('UNSUPPORTED_MEDIA')
  }
  if (file.size > MAX_MEDIA_BYTES) {
    throw new MediaError('MEDIA_TOO_LARGE')
  }
}

// Returns sample text only. It never reads the file, and the result is flagged `stub: true` so the
// review screen says the text is not from the clip.
export async function transcribeStub(file) {
  validateMediaFile(file)
  return { transcript_ar: strings.transcriptStubText, segments: [], stub: true }
}
