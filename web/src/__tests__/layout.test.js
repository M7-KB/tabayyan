import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const styles = readFileSync(resolve(here, '../styles.css'), 'utf8')
const cardStyles = readFileSync(resolve(here, '../components/card/card.css'), 'utf8')

// Static guard only: it checks the breakpoints exist and the mobile baseline has no fixed-width
// containers. The 375px overflow measurement (scrollWidth) was run in a real browser, not in this suite.
describe('responsive layout', () => {
  it('has a compact mobile breakpoint and a desktop breakpoint in the page styles', () => {
    expect(styles).toMatch(/@media \(max-width: 23\.4375rem\)/)
    expect(styles).toMatch(/@media \(min-width: 48rem\)/)
  })

  it('has matching breakpoints for the card styles', () => {
    expect(cardStyles).toMatch(/@media \(max-width: 23\.4375rem\)/)
    expect(cardStyles).toMatch(/@media \(min-width: 48rem\)/)
  })

  it('sets no fixed pixel width on the card or the page container', () => {
    expect(cardStyles).not.toMatch(/\.claim-card\s*\{[^}]*\bwidth:\s*\d+px/)
    expect(styles).not.toMatch(/main\s*\{[^}]*\bwidth:\s*\d+px/)
  })
})
