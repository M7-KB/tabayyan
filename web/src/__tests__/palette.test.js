import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const styles = readFileSync(resolve(here, '../styles.css'), 'utf8')
const cardStyles = readFileSync(resolve(here, '../components/card/card.css'), 'utf8')
const allStyles = styles + cardStyles

// Reads the --c-* tokens from a rule block, e.g. ':root {' or ':root[data-theme='dark'] {'.
function tokensIn(selector) {
  const start = allStyles.indexOf(`${selector} {`)
  if (start === -1) throw new Error(`missing rule ${selector}`)
  const block = allStyles.slice(start, allStyles.indexOf('}', start))
  const tokens = {}
  for (const [, name, hex] of block.matchAll(/--(c-[\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) {
    tokens[name] = hex.toLowerCase()
  }
  return tokens
}

const light = tokensIn(':root')
const dark = { ...light, ...tokensIn(":root[data-theme='dark']") }

// WCAG 2.x relative luminance and contrast ratio.
function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const lin = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}

function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

// Text pairs need 4.5:1 (WCAG 1.4.3). Non-text pairs (focus, control edges, rules) need 3:1 (WCAG 1.4.11).
const textPairs = [
  ['c-text', 'c-bg'],
  ['c-text', 'c-surface'],
  ['c-muted', 'c-bg'],
  ['c-muted', 'c-surface'],
  ['c-on-primary', 'c-primary'],
  ['c-disabled-text', 'c-disabled-bg'],
  ['c-link', 'c-bg'],
  ['c-link-visited', 'c-bg'],
  ['c-preview-text', 'c-preview-bg'],
  ['c-warn-text', 'c-warn-bg'],
  ['c-text', 'c-warn-block-bg'],
  ['c-text', 'c-claim-bg'],
  ['c-text', 'c-scripture-bg'],
  ['c-text', 'c-info-bg'],
  ['c-note-text', 'c-info-bg'],
  ['c-text', 'c-chip-bg'],
  ['c-state-ok-text', 'c-state-ok-bg'],
  ['c-state-no-text', 'c-state-no-bg'],
  ['c-state-dis-text', 'c-state-dis-bg'],
  ['c-state-cc-text', 'c-state-cc-bg'],
  ['c-state-ok-text', 'c-surface'],
  ['c-state-no-text', 'c-surface'],
  ['c-state-dis-text', 'c-surface'],
  ['c-state-cc-text', 'c-surface'],
]

const nonTextPairs = [
  ['c-focus', 'c-bg'],
  ['c-focus', 'c-surface'],
  ['c-primary', 'c-bg'],
  ['c-border-strong', 'c-surface'],
  ['c-rule', 'c-bg'],
]

describe.each([
  ['light', light],
  ['dark', dark],
])('%s theme palette (SPEC.md §6.4 and WCAG AA)', (_name, t) => {
  it.each(textPairs)('text pair %s on %s is at least 4.5:1', (fg, bg) => {
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(4.5)
  })

  it.each(nonTextPairs)('non-text pair %s on %s is at least 3:1', (fg, bg) => {
    expect(contrast(t[fg], t[bg])).toBeGreaterThanOrEqual(3)
  })
})

describe('dark palette values from the owner brief (2026-10-05)', () => {
  it('uses the specified background, surface, border, primary, accent, text and muted colours', () => {
    expect(dark['c-bg']).toBe('#0d1033')
    expect(dark['c-surface']).toBe('#161b4a')
    expect(dark['c-border']).toBe('#2a3170')
    expect(dark['c-primary']).toBe('#6a5ae0')
    expect(dark['c-focus']).toBe('#38c8e8')
    expect(dark['c-text']).toBe('#ffffff')
    expect(dark['c-muted']).toBe('#b7bce3')
  })
})
