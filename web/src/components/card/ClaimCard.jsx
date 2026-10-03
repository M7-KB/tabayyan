import { strings } from '../../strings.js'
import './card.css'
import { ExplanationBlock } from './ExplanationBlock.jsx'
import { MisquoteNotice } from './MisquoteNotice.jsx'
import { PositionsList } from './PositionsList.jsx'
import { ReferralBlock } from './ReferralBlock.jsx'
import { ScriptureBlock } from './ScriptureBlock.jsx'
import { StateBadge } from './StateBadge.jsx'
import { formatSeconds } from './format.js'

// One evidence card. Scripture, generated explanation and the user's own text each sit in their own
// container with a data-role (SPEC.md §6.4, G16).
export function ClaimCard({ card }) {
  const { claim, state_label_key: labelKey, alignment } = card
  const evidenceById = Object.fromEntries(card.evidence.map((item) => [item.evidence_id, item]))
  const isDisputed = card.state === 'DISPUTED'
  const isCannotConfirm = card.state === 'CANNOT_CONFIRM'

  return (
    <article className="claim-card" aria-label={strings.stateLabels[labelKey]}>
      <StateBadge labelKey={labelKey} />

      <section className="claim-block" data-role="user-text" aria-label={strings.claimHeading}>
        <h3>{strings.claimHeading}</h3>
        <blockquote lang={claim.lang} dir="auto">
          {claim.text_original}
        </blockquote>
        {claim.time_span && (
          <p className="timestamp">
            {strings.timestampFrom} {formatSeconds(claim.time_span.start_s)} {strings.timestampTo}{' '}
            {formatSeconds(claim.time_span.end_s)}
          </p>
        )}
      </section>

      {isCannotConfirm && <p className="abstain">{strings.cannotConfirmBody}</p>}

      {isDisputed && <PositionsList positions={card.positions} evidenceById={evidenceById} />}

      {!isDisputed && alignment === 'CONTRADICTS' && (
        <p className="source-intro">{strings.sourceTextIntro}</p>
      )}
      {!isDisputed &&
        card.evidence.map((item) => <ScriptureBlock key={item.evidence_id} item={item} />)}

      {card.explanation_ar && (
        <ExplanationBlock textAr={card.explanation_ar} textEn={card.explanation_en} />
      )}

      {card.misquote_notice && <MisquoteNotice notice={card.misquote_notice} />}

      {card.term && (
        <section className="term-block">
          <h3>{strings.termHeading}</h3>
          <p lang="ar" dir="rtl">
            {card.term.term_ar}
          </p>
          <p lang="en" dir="ltr">
            {card.term.term_en}
          </p>
        </section>
      )}

      {card.referral && <ReferralBlock referral={card.referral} />}

      <details className="verify">
        <summary>{strings.verifyHeading}</summary>
        <ol>
          {card.how_to_verify_ar.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      </details>
    </article>
  )
}
