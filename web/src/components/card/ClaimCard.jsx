import { strings } from '../../strings.js'
import './card.css'
import { ExplanationBlock } from './ExplanationBlock.jsx'
import { MisquoteNotice } from './MisquoteNotice.jsx'
import { PositionsList } from './PositionsList.jsx'
import { PublishedAnswer } from './PublishedAnswer.jsx'
import { ReferralBlock } from './ReferralBlock.jsx'
import { ScriptureBlock } from './ScriptureBlock.jsx'
import { StateBadge } from './StateBadge.jsx'
import { UnderstoodClaim } from './UnderstoodClaim.jsx'

// One evidence card. Scripture, generated explanation and the user's own text each sit in their own
// container with a data-role (SPEC.md §6.4, G16). `onRecheck` is set on the one-page results (U1): the card
// then offers edit and re-check in place. `recheck` is the state of a re-check of this card.
export function ClaimCard({ card, recheck = null, onRecheck }) {
  const { claim, state_label_key: labelKey, alignment } = card
  const evidenceById = Object.fromEntries(card.evidence.map((item) => [item.evidence_id, item]))
  const isDisputed = card.state === 'DISPUTED'
  const isCannotConfirm = card.state === 'CANNOT_CONFIRM'

  return (
    <article className="claim-card" aria-label={strings.stateLabels[labelKey]}>
      <StateBadge labelKey={labelKey} />

      <UnderstoodClaim claim={claim} recheck={recheck} onRecheck={onRecheck} />

      {isCannotConfirm && <p className="abstain">{strings.cannotConfirmBody}</p>}

      {isDisputed && <PositionsList positions={card.positions} evidenceById={evidenceById} />}

      {!isDisputed && alignment === 'CONTRADICTS' && (
        <p className="source-intro">{strings.sourceTextIntro}</p>
      )}
      {!isDisputed &&
        card.evidence
          // The published-answer block already shows this record's excerpt once.
          .filter((item) => !(card.published_answer && item.source_ref?.url === card.published_answer.url))
          .map((item) => <ScriptureBlock key={item.evidence_id} item={item} />)}

      {card.published_answer && <PublishedAnswer answer={card.published_answer} />}

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

      {card.glossary_link && (
        <section className="term-block glossary-link">
          <h3>{strings.glossaryHeading}</h3>
          <p>{strings.glossaryBody}</p>
          <p>
            <a href={card.glossary_link} target="_blank" rel="noopener noreferrer">
              {strings.glossaryLink}
            </a>
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
