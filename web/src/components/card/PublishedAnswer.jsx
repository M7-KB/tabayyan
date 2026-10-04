import { strings } from '../../strings.js'

// The hostname of the source link, shown as the source chip. Only the link's own host is shown, never a name we
// do not have (SPEC.md §0.8). The schema requires https, so a malformed URL is shown without a chip.
function hostOf(url) {
  try {
    return new URL(url).hostname
  } catch {
    return ''
  }
}

// A published answer from an approved site: its title and a verbatim excerpt, in a block separate from the
// generated explanation (SPEC.md §0.5, §0.8; non-negotiable 3).
export function PublishedAnswer({ answer }) {
  const host = hostOf(answer.url)
  return (
    <section className="published-answer" data-role="published-answer" aria-label={strings.publishedAnswerHeading}>
      <h3>{strings.publishedAnswerHeading}</h3>
      {host && (
        <p className="source-chip" dir="ltr">
          {host}
        </p>
      )}
      <h4 className="published-title" lang="ar" dir="rtl">
        {answer.title_ar}
      </h4>
      <blockquote className="published-excerpt" lang="ar" dir="rtl">
        {answer.excerpt_ar}
      </blockquote>
      <p className="quote-note">{strings.quoteSourceNote}</p>
      <p className="published-note">{strings.publishedAnswerNote}</p>
      <p className="source-link">
        <a href={answer.url} rel="noopener noreferrer">
          {strings.publishedAnswerLink}
        </a>
      </p>
    </section>
  )
}
