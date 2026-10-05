// Probe for GET /health. The preview banner hides only when the API answers 200 with a status field.
// Any failure, including a network error, keeps the banner up.
export async function checkApiHealth({ baseUrl = '', fetchImpl = globalThis.fetch } = {}) {
  try {
    const response = await fetchImpl(`${baseUrl}/health`)
    if (!response.ok) return false
    const body = await response.json()
    return typeof body?.status === 'string'
  } catch {
    return false
  }
}
