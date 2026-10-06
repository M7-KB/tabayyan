import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Ajv2020 from 'ajv/dist/2020.js'
import addFormats from 'ajv-formats'
import cardSchema from '../../../contracts/card.schema.json'
import { ClaimCard } from '../components/card/ClaimCard.jsx'
import { strings } from '../strings.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'
import supportedContradicts from '../../../contracts/fixtures/supported-contradicts.json'
import disputed from '../../../contracts/fixtures/disputed.json'
import cannotConfirm from '../../../contracts/fixtures/cannot-confirm.json'

// Synthetic variants built from the P-07 fixtures. Every text here is synthetic (SPEC.md §4.1 fixtures).
// Shared evidence shape (contracts/card.schema.json $defs/evidence), as used by misquote_notice.evidence.
const misquoteEvidence = {
  evidence_id: 'notice-e1',
  corpus_id: 'synthetic:notice',
  domain: 'hadith',
  source_id: 'synthetic-source',
  source_name_ar: 'مصدر تجريبي للتنبيه',
  source_url: 'https://example.invalid/notice-source',
  quote_ar: 'نص تجريبي للتنبيه',
  translation: null,
  ref: { collection: 'Synthetic notice collection', number: '7' },
  grading: {
    grade_ar: 'حكم تجريبي للتنبيه',
    grader_ar: 'جهة تجريبية',
    grading_source_url: 'https://example.invalid/notice-grading',
  },
  verbatim_verified: true,
  retrieval_score: 12.5,
}

const withMisquote = {
  ...cannotConfirm,
  misquote_notice: {
    evidence: misquoteEvidence,
    note_ar: 'شرح مولّد تجريبي للتنبيه',
  },
}

const hadithContradicts = {
  ...supportedContradicts,
  evidence: [
    {
      ...supportedContradicts.evidence[0],
      domain: 'hadith',
      ref: { section: 'synthetic-hadith' },
      grading: {
        grade_ar: 'صحيح',
        grader_ar: 'حكم تجريبي',
        grading_source_url: 'https://example.invalid/grading',
      },
    },
  ],
}

const withTranslation = {
  ...supportedContradicts,
  evidence: [
    {
      ...supportedContradicts.evidence[0],
      translation: {
        corpus_id: 'quran_translation:synthetic:1',
        text_en: 'Synthetic English translation',
        source_id: 'synthetic-translation',
        source_url: 'https://example.invalid/translation',
      },
    },
  ],
}

const timedClaim = {
  ...supportedConfirms,
  claim: { ...supportedConfirms.claim, time_span: { start_s: 41.2, end_s: 48.9 } },
}

const termCard = {
  ...cannotConfirm,
  term: { term_ar: 'مصطلح تجريبي', term_en: 'Synthetic term', glossary_corpus_id: 'synthetic:term' },
}

describe('state label rendering (SPEC.md §6.4, G26)', () => {
  it('renders the owner-given SUPPORTED + CONTRADICTS badge and intro', () => {
    const { container } = render(<ClaimCard card={supportedContradicts} />)
    expect(screen.getByText(strings.stateLabels.supported_contradicts)).toBeInTheDocument()
    expect(screen.getByText(strings.sourceTextIntro)).toBeInTheDocument()
    expect(container.querySelector('[data-state="supported_contradicts"]')).toBeInTheDocument()
  })

  it('renders the correct verbatim quote inside the scripture block', () => {
    render(<ClaimCard card={supportedContradicts} />)
    const scripture = screen.getByRole('region', { name: strings.scriptureLabel })
    expect(within(scripture).getByText(supportedContradicts.evidence[0].quote_ar)).toBeInTheDocument()
  })

  it('uses a distinct label for supported_confirms and supported_contradicts', () => {
    expect(strings.stateLabels.supported_confirms).not.toBe(strings.stateLabels.supported_contradicts)
  })

  it.each([
    ['supported_confirms', supportedConfirms],
    ['supported_contradicts', supportedContradicts],
    ['disputed', disputed],
    ['cannot_confirm', cannotConfirm],
  ])('renders the %s state from its P-07 fixture', (key, card) => {
    const { container } = render(<ClaimCard card={card} />)
    expect(container.querySelector(`[data-state="${key}"]`)).toHaveTextContent(strings.stateLabels[key])
  })
})

describe('data-role separation (G16)', () => {
  it('puts the user claim in data-role="user-text" and the evidence in data-role="scripture"', () => {
    const { container } = render(<ClaimCard card={supportedConfirms} />)
    const claim = container.querySelector('[data-role="user-text"]')
    expect(claim).toHaveTextContent(supportedConfirms.claim.text_ar)
    const scripture = container.querySelector('[data-role="scripture"]')
    expect(scripture).toHaveTextContent(supportedConfirms.evidence[0].quote_ar)
    expect(claim.contains(scripture)).toBe(false)
  })

  it('keeps generated explanation out of the scripture block and the quote out of the explanation', () => {
    const { container } = render(<ClaimCard card={supportedConfirms} />)
    const explanation = container.querySelector('[data-role="explanation"]')
    expect(explanation).toHaveTextContent(supportedConfirms.explanation_ar)
    expect(explanation.closest('[data-role="scripture"]')).toBeNull()
    expect(explanation).not.toHaveTextContent(supportedConfirms.evidence[0].quote_ar)
    expect(within(explanation).getByText(strings.explanationHeading)).toBeInTheDocument()
  })
})

describe('evidence and grading', () => {
  it('shows hadith grading without requiring a click', () => {
    render(<ClaimCard card={hadithContradicts} />)
    expect(screen.getByText('صحيح')).toBeVisible()
    expect(screen.getByText(/حكم تجريبي/)).toBeVisible()
  })

  it('shows the source link as a plain outbound link', () => {
    const { container } = render(<ClaimCard card={supportedConfirms} />)
    const scripture = container.querySelector('[data-role="scripture"]')
    expect(within(scripture).getByRole('link', { name: strings.sourceLink })).toHaveAttribute(
      'href',
      supportedConfirms.evidence[0].source_url,
    )
  })

  it('shows the English translation with its own source link, separate from the Arabic source', () => {
    const { container } = render(<ClaimCard card={withTranslation} />)
    const translation = container.querySelector('[data-role="translation"]')
    expect(translation).toHaveTextContent('Synthetic English translation')
    expect(translation.closest('[data-role="scripture"]')).not.toBeNull()
    expect(within(translation).getByRole('link', { name: strings.translationSourceLink })).toHaveAttribute(
      'href',
      withTranslation.evidence[0].translation.source_url,
    )
    expect(screen.getByRole('link', { name: strings.sourceLink })).toHaveAttribute(
      'href',
      withTranslation.evidence[0].source_url,
    )
  })

  it('renders no translation block when the evidence has no approved translation', () => {
    const { container } = render(<ClaimCard card={supportedConfirms} />)
    expect(container.querySelector('[data-role="translation"]')).toBeNull()
    expect(screen.queryByRole('link', { name: strings.translationSourceLink })).toBeNull()
  })
})

describe('disputed cards', () => {
  it('lists positions in the order given, with their own evidence and no ranking', () => {
    render(<ClaimCard card={disputed} />)
    const items = screen.getAllByRole('listitem').filter((li) => li.querySelector('h4'))
    expect(items.map((li) => li.querySelector('h4').textContent)).toEqual(
      disputed.positions.map((p) => p.label_ar),
    )
    expect(screen.queryByText(/الأرجح|أقوى|مفضل/)).toBeNull()
  })
})

describe('misquote notice', () => {
  it('renders the notice without an alignment badge', () => {
    const { container } = render(<ClaimCard card={withMisquote} />)
    expect(screen.getByText(strings.misquoteHeading)).toBeInTheDocument()
    expect(screen.getByText(misquoteEvidence.quote_ar)).toBeInTheDocument()
    expect(container.querySelector('[data-state="supported_contradicts"]')).toBeNull()
    expect(container.querySelector('[data-state="supported_confirms"]')).toBeNull()
  })

  it('shows the notice source, reference, grading and source link from its own evidence', () => {
    const { container } = render(<ClaimCard card={withMisquote} />)
    const notice = container.querySelector('.misquote-notice')
    expect(within(notice).getByText(misquoteEvidence.source_name_ar, { exact: false })).toBeInTheDocument()
    expect(within(notice).getByText(/Synthetic notice collection/)).toBeInTheDocument()
    expect(within(notice).getByText(misquoteEvidence.grading.grade_ar)).toBeVisible()
    expect(within(notice).getByText(/جهة تجريبية/)).toBeVisible()
    expect(within(notice).getByRole('link', { name: strings.sourceLink })).toHaveAttribute(
      'href',
      misquoteEvidence.source_url,
    )
  })

  it('keeps the matched quote in the scripture block and the generated note in the explanation block', () => {
    const { container } = render(<ClaimCard card={withMisquote} />)
    const notice = container.querySelector('.misquote-notice')
    const scripture = within(notice).getByRole('region', { name: strings.scriptureLabel })
    expect(scripture).toHaveTextContent(misquoteEvidence.quote_ar)
    const explanation = within(notice).getByText(withMisquote.misquote_notice.note_ar).closest('[data-role="explanation"]')
    expect(explanation).not.toBeNull()
    expect(explanation).not.toHaveTextContent(misquoteEvidence.quote_ar)
  })

  it('does not render the legacy flat notice shape, so no unsourced quote is shown', () => {
    const legacy = {
      ...cannotConfirm,
      misquote_notice: { corpus_id: 'synthetic:legacy', quote_ar: 'نص تجريبي قديم', note_ar: 'شرح قديم' },
    }
    const { container } = render(<ClaimCard card={legacy} />)
    expect(screen.queryByText(strings.misquoteHeading)).toBeNull()
    expect(screen.queryByText('نص تجريبي قديم')).toBeNull()
    expect(container.querySelector('.misquote-notice')).toBeNull()
  })

  it('shows the grading source as its own labelled link, distinct from the collection source link', () => {
    const { container } = render(<ClaimCard card={withMisquote} />)
    const notice = container.querySelector('.misquote-notice')
    const gradingLink = within(notice).getByRole('link', { name: strings.gradingSourceLink })
    const sourceLink = within(notice).getByRole('link', { name: strings.sourceLink })
    expect(gradingLink).toHaveAttribute('href', misquoteEvidence.grading.grading_source_url)
    expect(sourceLink).toHaveAttribute('href', misquoteEvidence.source_url)
    expect(gradingLink.getAttribute('href')).not.toBe(sourceLink.getAttribute('href'))
  })

  it.each([
    ['an empty grading object', {}],
    ['a grading object missing grader_ar', { grade_ar: 'حكم تجريبي', grading_source_url: 'https://example.invalid/g' }],
    ['a grading object with an empty grade_ar', { grade_ar: '  ', grader_ar: 'جهة', grading_source_url: 'https://example.invalid/g' }],
    ['a grading source that is not https', { grade_ar: 'حكم', grader_ar: 'جهة', grading_source_url: 'http://example.invalid/g' }],
  ])('does not render a hadith notice with %s', (_label, grading) => {
    const partial = {
      ...cannotConfirm,
      misquote_notice: { evidence: { ...misquoteEvidence, grading }, note_ar: 'شرح مولّد تجريبي للتنبيه' },
    }
    const { container } = render(<ClaimCard card={partial} />)
    expect(screen.queryByText(strings.misquoteHeading)).toBeNull()
    expect(screen.queryByText(misquoteEvidence.quote_ar)).toBeNull()
    expect(container.querySelector('.misquote-notice')).toBeNull()
  })

  it('does not render a hadith notice that has no grading', () => {
    const ungraded = {
      ...cannotConfirm,
      misquote_notice: { evidence: { ...misquoteEvidence, grading: null }, note_ar: 'شرح مولّد تجريبي للتنبيه' },
    }
    const { container } = render(<ClaimCard card={ungraded} />)
    expect(screen.queryByText(strings.misquoteHeading)).toBeNull()
    expect(screen.queryByText(misquoteEvidence.quote_ar)).toBeNull()
    expect(container.querySelector('.misquote-notice')).toBeNull()
  })
})

describe('abstain, referral and verification', () => {
  it('shows the referral block on CANNOT_CONFIRM with the SPEC §9 body and a ready question', () => {
    render(<ClaimCard card={cannotConfirm} />)
    expect(screen.getByRole('link', { name: cannotConfirm.referral.body_name_ar })).toHaveAttribute(
      'href',
      cannotConfirm.referral.body_url,
    )
    expect(screen.getByText(cannotConfirm.referral.ready_to_ask_question_ar)).toBeInTheDocument()
    expect(screen.getByText(strings.cannotConfirmBody)).toBeInTheDocument()
  })

  it('renders exactly the two verify lines inside a collapsible block', () => {
    const { container } = render(<ClaimCard card={supportedConfirms} />)
    const verify = container.querySelector('details.verify')
    expect(verify.querySelector('summary')).toHaveTextContent(strings.verifyHeading)
    expect(within(verify).getAllByRole('listitem')).toHaveLength(2)
    expect(verify.open).toBe(false)
  })
})

describe('claim timestamp and term', () => {
  it('shows the claim timestamp when time_span is present', () => {
    render(<ClaimCard card={timedClaim} />)
    expect(screen.getByText(/00:41/)).toBeInTheDocument()
    expect(screen.getByText(/00:48/)).toBeInTheDocument()
  })

  it('renders the glossary term verbatim', () => {
    render(<ClaimCard card={termCard} />)
    expect(screen.getByText('مصطلح تجريبي')).toBeInTheDocument()
    expect(screen.getByText('Synthetic term')).toBeInTheDocument()
  })

  it('renders a link-only glossary fallback with no copied definition (SPEC §0.11 O2)', () => {
    const glossaryCard = {
      ...cannotConfirm,
      glossary_link: 'https://islamic-content.com/dictionary',
      term: null,
      explanation_ar: null,
      explanation_en: null,
      misquote_notice: null,
    }
    const { container } = render(<ClaimCard card={glossaryCard} />)
    const link = screen.getByRole('link', { name: strings.glossaryLink })
    expect(link).toHaveAttribute('href', 'https://islamic-content.com/dictionary')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(container.querySelector('.glossary-link')).not.toBeNull()
    expect(container.querySelector('[data-role="explanation"]')).toBeNull()
  })

  it('hides the explanation block when the server drops it (null explanation, SPEC §0.11 O3)', () => {
    const { container } = render(<ClaimCard card={{ ...cannotConfirm, explanation_ar: null, explanation_en: null, misquote_notice: null }} />)
    expect(container.querySelector('[data-role="explanation"]')).toBeNull()
  })
})

// Published answers and live source references (SPEC.md §0.8, contracts/card.schema.json). Synthetic text only.
const ajv = addFormats(new Ajv2020({ allErrors: true, strict: false }))
const validateCard = ajv.compile(cardSchema)

const syntheticAnswer = {
  source_id: 'synthetic-answers',
  title_ar: 'عنوان تجريبي للجواب',
  excerpt_ar: 'نص تجريبي للجواب من المصدر',
  url: 'https://example.invalid/answer',
}

const withAnswer = { ...supportedConfirms, published_answer: syntheticAnswer }

const liveEvidence = {
  ...supportedConfirms.evidence[0],
  source_ref: { source_id: 'synthetic-source', record_ref: 'synthetic:1', url: 'https://example.invalid/record' },
}
delete liveEvidence.corpus_id
const liveCard = { ...supportedConfirms, evidence: [liveEvidence] }

describe('published answer block (SPEC.md §0.5, §0.8)', () => {
  it('uses fixtures that validate against the card contract', () => {
    expect(validateCard(withAnswer)).toBe(true)
    expect(validateCard(liveCard)).toBe(true)
  })

  it('renders the title, the verbatim excerpt and the link in their own block', () => {
    const { container } = render(<ClaimCard card={withAnswer} />)
    const block = container.querySelector('[data-role="published-answer"]')
    expect(block).not.toBeNull()
    expect(within(block).getByText(syntheticAnswer.title_ar)).toBeInTheDocument()
    expect(within(block).getByText(syntheticAnswer.excerpt_ar)).toBeInTheDocument()
    expect(within(block).getByRole('link', { name: strings.publishedAnswerLink })).toHaveAttribute(
      'href',
      syntheticAnswer.url,
    )
    expect(within(block).getByText(strings.quoteSourceNote)).toBeInTheDocument()
  })

  it('keeps the published answer out of the scripture and explanation blocks', () => {
    const { container } = render(<ClaimCard card={withAnswer} />)
    const block = container.querySelector('[data-role="published-answer"]')
    expect(block.closest('[data-role="explanation"]')).toBeNull()
    expect(block.closest('[data-role="scripture"]')).toBeNull()
  })

  it('shows the link host as the source chip, not a source name we do not have', () => {
    const { container } = render(<ClaimCard card={withAnswer} />)
    expect(container.querySelector('.source-chip')).toHaveTextContent('example.invalid')
  })

  it('renders no published-answer block when there is none', () => {
    const { container } = render(<ClaimCard card={{ ...supportedConfirms, published_answer: null }} />)
    expect(container.querySelector('[data-role="published-answer"]')).toBeNull()
  })
})

describe('live source references (SPEC.md §0.8)', () => {
  it('renders a scripture block for evidence that carries source_ref instead of corpus_id', () => {
    const { container } = render(<ClaimCard card={liveCard} />)
    const block = container.querySelector('[data-role="scripture"]')
    expect(block).not.toBeNull()
    expect(within(block).getByText(liveEvidence.quote_ar)).toBeInTheDocument()
  })
})

describe('source line on quotes (SPEC.md §0.7)', () => {
  it('shows the source line next to the source link on every scripture block', () => {
    const { container } = render(<ClaimCard card={supportedContradicts} />)
    const blocks = container.querySelectorAll('[data-role="scripture"]')
    expect(blocks.length).toBeGreaterThan(0)
    for (const block of blocks) {
      expect(within(block).getByText(strings.quoteSourceNote)).toBeInTheDocument()
    }
  })

  it('does not show the source line on a card without a quote', () => {
    render(<ClaimCard card={{ ...cannotConfirm, misquote_notice: null }} />)
    expect(screen.queryByText(strings.quoteSourceNote)).not.toBeInTheDocument()
  })
})

describe('hadith and glossary presentation (live-case fixes)', () => {
  const longRef = {
    collection: 'Synthetic collection',
    number: '7',
    attribution: 'نسبة تجريبية طويلة إلى راوٍ تجريبي',
    reference: 'كتاب تجريبي أول، كتاب تجريبي ثانٍ، كتاب تجريبي ثالث',
  }
  const sameMeaning = {
    ...supportedConfirms,
    alignment: 'SAME_MEANING',
    state_label_key: 'supported_same_meaning',
    evidence: [{ ...supportedConfirms.evidence[0], ref: longRef }],
    hadith_caution_ar: 'لا تنسب لفظك إلى النبي ﷺ؛ تحقّق من نص الحديث ودرجته في المصدر.',
    referral: cannotConfirm.referral,
  }

  it('labels the same-meaning hadith card instead of an empty badge', () => {
    const { container } = render(<ClaimCard card={sameMeaning} />)
    expect(container.querySelector('[data-state="supported_same_meaning"]')).toHaveTextContent(
      strings.stateLabels.supported_same_meaning,
    )
  })

  it('keeps collection and number in the source line and collapses the long references', () => {
    const { container } = render(<ClaimCard card={sameMeaning} />)
    const meta = container.querySelector('.source-meta')
    expect(meta).toHaveTextContent('Synthetic collection، 7')
    expect(meta).not.toHaveTextContent('كتاب تجريبي أول')
    const details = container.querySelector('details.references')
    expect(details).not.toBeNull()
    expect(details.querySelector('summary')).toHaveTextContent(strings.referencesHeading)
    expect(details).toHaveTextContent('كتاب تجريبي أول، كتاب تجريبي ثانٍ، كتاب تجريبي ثالث')
    expect(details.open).toBe(false)
    // The hadith text and grade come before the collapsed references.
    const quote = container.querySelector('.quote')
    expect(quote.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('labels a glossary definition as «source: term», not by its page path', () => {
    const glossary = {
      ...supportedConfirms,
      evidence: [{
        ...supportedConfirms.evidence[0],
        domain: 'glossary',
        source_name_ar: 'الجمهرة',
        grading: null,
        ref: { label: 'مصطلح تجريبي' },
      }],
    }
    const { container } = render(<ClaimCard card={glossary} />)
    expect(container.querySelector('.source-meta')).toHaveTextContent('الجمهرة: مصطلح تجريبي')
    expect(container.querySelector('.source-meta')).not.toHaveTextContent('/dictionary')
    expect(container.querySelector('details.references')).toBeNull()
  })

  it('labels a published answer as «source: question title», not by its page path', () => {
    const faq = {
      ...supportedConfirms,
      evidence: [{
        ...liveEvidence,
        domain: 'faq',
        source_name_ar: 'بينات',
        grading: null,
        ref: { label: 'عنوان سؤال تجريبي' },
      }],
    }
    const { container } = render(<ClaimCard card={faq} />)
    expect(container.querySelector('.source-meta')).toHaveTextContent('بينات: عنوان سؤال تجريبي')
    expect(container.querySelector('.source-meta')).not.toHaveTextContent('/ar/category')
  })

  it('shows a published answer once: the evidence block of the same record is not repeated', () => {
    const answer = { ...syntheticAnswer, url: liveEvidence.source_ref.url }
    const faqEvidence = { ...liveEvidence, domain: 'faq', grading: null, ref: { label: 'عنوان' } }
    const otherEvidence = { ...supportedConfirms.evidence[0], evidence_id: 'e2' }
    const card = {
      ...supportedConfirms, evidence: [faqEvidence, otherEvidence], published_answer: answer, misquote_notice: null,
    }
    const { container } = render(<ClaimCard card={card} />)
    expect(validateCard(card)).toBe(true)
    const scripture = container.querySelectorAll('[data-role="scripture"]')
    expect(scripture).toHaveLength(1)
    expect(scripture[0]).toHaveTextContent(otherEvidence.quote_ar)
    expect(container.querySelectorAll('[data-role="published-answer"]')).toHaveLength(1)
    expect(container.textContent.split(answer.excerpt_ar)).toHaveLength(2)
  })

  it('renders no evidence block on a card that cannot confirm', () => {
    const { container } = render(<ClaimCard card={{ ...cannotConfirm, misquote_notice: null }} />)
    expect(container.querySelector('[data-role="scripture"]')).toBeNull()
    expect(container.querySelector('[data-role="published-answer"]')).toBeNull()
    expect(validateCard(cannotConfirm)).toBe(true)
  })
})
