import { strings } from '../../strings.js'
import { formatRef, hasCompleteGrading } from './format.js'

// Hadith references: collection and number stay in the source line; the long attribution and book
// reference list is collapsed behind «المراجع» so the hadith text and grade come first.
const SHORT_HADITH_REF = ['collection', 'number']

function splitHadithRef(ref) {
  const short = Object.fromEntries(Object.entries(ref).filter(([key]) => SHORT_HADITH_REF.includes(key)))
  const long = Object.entries(ref).filter(([key, value]) => !SHORT_HADITH_REF.includes(key) && value)
  return { short, long }
}

// Scripture and source text only. Nothing generated goes in this block (SPEC.md §4.1, non-negotiable 3).
export function ScriptureBlock({ item }) {
  const showGrading = hasCompleteGrading(item.grading)
  const hadithRef = item.domain === 'hadith' && item.ref ? splitHadithRef(item.ref) : null
  // A glossary record is labelled «source: term» and a published answer «source: title»;
  // other records «source · reference».
  const sourceMeta = ['glossary', 'faq'].includes(item.domain) && item.ref?.label
    ? `${item.source_name_ar}: ${item.ref.label}`
    : hadithRef
      ? `${item.source_name_ar}${Object.keys(hadithRef.short).length ? ` · ${formatRef(hadithRef.short)}` : ''}`
      : `${item.source_name_ar}${item.ref ? ` · ${formatRef(item.ref)}` : ''}`
  return (
    <section className="scripture-block" data-role="scripture" aria-label={strings.scriptureLabel}>
      <p className="source-meta">{sourceMeta}</p>
      {showGrading && (
        <p className="grading">
          <span>{strings.gradingLabel}: </span>
          <strong>{item.grading.grade_ar}</strong>
          <span> ({item.grading.grader_ar})</span>
          <span> · </span>
          <a href={item.grading.grading_source_url} rel="noopener noreferrer">
            {strings.gradingSourceLink}
          </a>
        </p>
      )}
      <blockquote className="quote" lang="ar" dir="rtl">
        {item.quote_ar}
      </blockquote>
      <p className="source-link">
        <a href={item.source_url} rel="noopener noreferrer">
          {strings.sourceLink}
        </a>
      </p>
      {hadithRef && hadithRef.long.length > 0 && (
        <details className="references">
          <summary>{strings.referencesHeading}</summary>
          <ul>
            {hadithRef.long.map(([key, value]) => (
              <li key={key} lang="ar" dir="rtl">
                {String(value)}
              </li>
            ))}
          </ul>
        </details>
      )}
      <p className="quote-note">{strings.quoteSourceNote}</p>
      {item.translation && (
        <section className="translation-block" data-role="translation" aria-label={strings.translationLabel}>
          <blockquote className="quote quote-en" lang="en" dir="ltr">
            {item.translation.text_en}
          </blockquote>
          <p className="source-link">
            <a href={item.translation.source_url} rel="noopener noreferrer">
              {strings.translationSourceLink}
            </a>
          </p>
        </section>
      )}
    </section>
  )
}
