import { strings } from '../../strings.js'
import { ExplanationBlock } from './ExplanationBlock.jsx'

// Shown without an alignment badge (SPEC.md §4.1). The matched text is scripture; the note is generated.
export function MisquoteNotice({ notice }) {
  return (
    <section className="misquote-notice">
      <h3>{strings.misquoteHeading}</h3>
      <section className="scripture-block" data-role="scripture" aria-label={strings.scriptureLabel}>
        <blockquote className="quote" lang="ar" dir="rtl">
          {notice.quote_ar}
        </blockquote>
      </section>
      <ExplanationBlock textAr={notice.note_ar} />
    </section>
  )
}
