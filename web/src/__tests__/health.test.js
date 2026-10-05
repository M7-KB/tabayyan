import { describe, expect, it, vi } from 'vitest'
import { checkApiHealth } from '../api/health.js'
import { API_BASE_URL, normalizeBaseUrl } from '../config/api.js'

describe('checkApiHealth', () => {
  it('reports the API as live when /health answers 200 with a status', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ status: 'degraded' }) }))
    await expect(checkApiHealth({ baseUrl: 'https://api.example', fetchImpl })).resolves.toBe(true)
    expect(fetchImpl).toHaveBeenCalledWith('https://api.example/health')
  })

  it('keeps the banner up on a non-200 answer', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: false, status: 503, json: async () => ({}) }))
    await expect(checkApiHealth({ fetchImpl })).resolves.toBe(false)
  })

  it('keeps the banner up when the body has no status field', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ corpus_items: 1 }) }))
    await expect(checkApiHealth({ fetchImpl })).resolves.toBe(false)
  })

  it('keeps the banner up on a network failure', async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(checkApiHealth({ fetchImpl })).resolves.toBe(false)
  })
})

describe('normalizeBaseUrl', () => {
  it('strips trailing slashes and surrounding whitespace', () => {
    expect(normalizeBaseUrl(' https://api.example/// ')).toBe('https://api.example')
  })

  it('returns an empty string when the variable is unset', () => {
    expect(normalizeBaseUrl(undefined)).toBe('')
    expect(normalizeBaseUrl('')).toBe('')
  })

  it('is empty in the test build, which has no VITE_API_BASE_URL', () => {
    expect(API_BASE_URL).toBe('')
  })
})
