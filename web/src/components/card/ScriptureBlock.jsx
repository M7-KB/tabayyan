import { strings } from '../../strings.js'
import { formatRef } from './format.js'

// Scripture and source text only. Nothing generated goes in this block (SPEC.md §4.1, non-negotiable 3).
export function ScriptureBlock({ item }) {
  return (
    <section className="scripture-block" data-role="scripture" aria-label={strings.scriptureLabel}>
      <p className="source-meta">
        <span>{item.source_name_ar}</span>
        {item.ref && <span> · {formatRef(item.ref)}</span>}
      </p>
      {item.grading && (
        <p className="grading">
          <span>{strings.gradingLabel}: </span>
          <strong>{item.grading.grade_ar}</strong>
          <span> ({item.grading.grader_ar})</span>
        </p>
      )}
      <blockquote className="quote" lang="ar" dir="rtl">
        {item.quote_ar}
      </blockquote>
      {item.translation && (
        <blockquote className="quote quote-en" lang="en" dir="ltr">
          {item.translation.text_en}
        </blockquote>
      )}
      <p className="source-link">
        <a href={item.source_url} rel="noopener noreferrer">
          {strings.sourceLink}
        </a>
      </p>
    </section>
  )
}
