import { strings } from '../../strings.js'
import { InfoIcon } from '../Icons.jsx'

// Generated prose, labelled and kept apart from scripture (SPEC.md §4.1).
export function ExplanationBlock({ textAr, textEn }) {
  if (textAr === strings.noGeneratedExplanation) {
    return (
      <section className="explanation-note" data-role="explanation" role="note">
        <InfoIcon />
        <div>
          <p lang="ar" dir="rtl">{textAr}</p>
          {textEn && <p lang="en" dir="ltr">{textEn}</p>}
        </div>
      </section>
    )
  }

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
