// Shared JSON POST for the verification endpoints. Errors carry only the server's fixed error code (SPEC.md §3):
// response bodies are never shown to the user, and a non-JSON error body keeps the generic code.

export class ApiError extends Error {
  constructor(code, status = null) {
    super(code)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

export async function postJson(url, body, { fetchImpl = globalThis.fetch, signal } = {}) {
  let response
  try {
    response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch {
    throw new ApiError('NETWORK')
  }

  if (!response.ok) {
    let code = 'UNKNOWN'
    try {
      const errorBody = await response.json()
      if (typeof errorBody?.error?.code === 'string') code = errorBody.error.code
    } catch {
      // Keep the generic code when the error body is not JSON.
    }
    throw new ApiError(code, response.status)
  }

  try {
    return await response.json()
  } catch {
    throw new ApiError('PIPELINE_DEGRADED', response.status)
  }
}
