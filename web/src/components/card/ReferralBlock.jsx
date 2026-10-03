import { strings } from '../../strings.js'

export function ReferralBlock({ referral }) {
  return (
    <section className="referral-block">
      <h3>{strings.referralHeading}</h3>
      <p>
        <a href={referral.body_url} rel="noopener noreferrer">
          {referral.body_name_ar}
        </a>
      </p>
      <p>{referral.fallback_line_ar}</p>
      <h4>{strings.readyQuestionHeading}</h4>
      <p className="ready-question">{referral.ready_to_ask_question_ar}</p>
    </section>
  )
}
