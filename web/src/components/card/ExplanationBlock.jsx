import { strings } from '../../strings.js'

// Generated prose, labelled and kept apart from scripture (SPEC.md §4.1).
export function ExplanationBlock({ textAr, textEn }) {
  return (
    <section className="explanation-block" data-role="explanation">
      <h3>{strings.explanationHeading}</h3>
      <p lang="ar" dir="rtl">
        {textAr}
      </p>
      {textEn && (
        <p lang="en" dir="ltr">
          {textEn}
        </p>
      )}
    </section>
  )
}
