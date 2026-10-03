import { describe, expect, it } from 'vitest'
import { strings } from '../strings.js'

function allValues(value) {
  if (Array.isArray(value)) return value.flatMap(allValues)
  return [value]
}

describe('product strings', () => {
  it('contain no Latin letters', () => {
    const latin = allValues(Object.values(strings)).filter((text) => /[A-Za-z]/.test(text))
    expect(latin).toEqual([])
  })

  it('use the exact owner-fixed consent text (SPEC.md §6.6)', () => {
    expect(strings.consent).toBe('أؤكد أن لدي حق مشاركة هذا المقطع لغرض التحقق')
  })

  it('do not promise image handling, since image input is P2 and not in the UI', () => {
    const privacy = strings.privacyLines.join(' ')
    expect(privacy).not.toContain('صور')
  })

  it('use the exact AI disclosure text (SPEC.md §8)', () => {
    expect(strings.aiNotice).toBe('هذه أداة ذكاء اصطناعي، وليست فتوى.')
  })
})
