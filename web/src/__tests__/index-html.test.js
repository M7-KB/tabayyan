import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const html = readFileSync(resolve(here, '../../index.html'), 'utf8')

describe('index.html', () => {
  it('sets lang="ar" and dir="rtl" on the root element', () => {
    expect(html).toMatch(/<html[^>]*\blang="ar"/)
    expect(html).toMatch(/<html[^>]*\bdir="rtl"/)
  })
})
