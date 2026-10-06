import { describe, expect, it } from 'vitest'
import { strings } from '../strings.js'

function allValues(value) {
  if (Array.isArray(value)) return value.flatMap(allValues)
  if (value && typeof value === 'object') return Object.values(value).flatMap(allValues)
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

  it('describe text input only in the privacy notice (text first, no audio or video yet)', () => {
    const privacy = strings.privacyLines.join(' ')
    expect(privacy).not.toContain('الصوتية')
    expect(privacy).not.toContain('المرئية')
    expect(privacy).not.toContain('المقاطع')
  })

  it('keeps the owner-approved provider-retention sentence, literally (SPEC.md §8)', () => {
    expect(strings.privacyLines).toContain('لا نحفظه في خوادمنا، وقد يحتفظ مزوّد الخدمة بالبيانات مؤقتاً وفق سياسته.')
  })

  it('use the owner-approved input notice under the composer (owner update, 2026-10-06)', () => {
    expect(strings.privacySummary).toBe('يُرسل نصك إلى مزوّد ذكاء اصطناعي، ولا نحفظه في خوادمنا.')
  })

  it('use the source line from SPEC.md §0.7 on every quote', () => {
    expect(strings.quoteSourceNote).toBe('النصوص منقولة من مصادرها المعتمدة كما هي، مع الرابط للتحقق.')
  })

  it('use the exact AI disclosure text (SPEC.md §8)', () => {
    expect(strings.aiNotice).toBe('هذه أداة ذكاء اصطناعي، وليست فتوى.')
  })

  it('use the state labels from the SPEC.md §12 table', () => {
    expect(strings.stateLabels).toEqual({
      supported_confirms: 'يؤيده المصدر المعتمد',
      supported_contradicts: 'لا يطابق المصدر المعتمد',
      supported_same_meaning: 'لم نجد لفظك حرفياً؛ هذا حديث صحيح بمعنى قريب',
      disputed: 'مسألة مختلف فيها',
      cannot_confirm: 'لا يمكن التأكد من المصادر المتاحة',
    })
    expect(strings.sourceTextIntro).toBe('النص كما ورد في المصدر:')
  })
})
