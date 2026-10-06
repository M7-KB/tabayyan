import { describe, expect, it, vi } from 'vitest'
import { checkDeadlineMs } from '../config/api.js'

describe('check deadline configuration', () => {
  it.each([undefined, '', 'bad', 'NaN', 'Infinity', '0', '-1'])('uses 65 seconds for invalid %s', (raw) => {
    expect(checkDeadlineMs(raw)).toBe(65_000)
  })

  it('accepts a positive millisecond override', () => {
    expect(checkDeadlineMs('72000')).toBe(72_000)
  })

  it('reads the build environment override', async () => {
    vi.stubEnv('VITE_CHECK_DEADLINE_MS', '75000')
    vi.resetModules()
    try {
      const config = await import('../config/api.js')
      expect(config.CHECK_DEADLINE_MS).toBe(75_000)
    } finally {
      vi.unstubAllEnvs()
      vi.resetModules()
    }
  })
})
