import { strings } from '../strings.js'
import { CheckProgress } from './CheckProgress.jsx'
import { ClaimCard } from './card/ClaimCard.jsx'

// Result area for the one-page flow (U1). Loading, error and empty states each give a next step (agent brief).
// `status` is 'loading' | 'error' | 'done'. Error copy is looked up by the server's error code.
// On 'done', each card can be edited and re-checked in place: `onRecheck(index, text)` resolves to true when
// that card was replaced. `recheck` names the card being re-checked and its state.
export function Results({ status, cards = [], errorCode, recheck = null, onRetry, onEdit, onCancel, onRecheck }) {
  if (status === 'loading') {
    return (
      <section className="results" aria-labelledby="results-heading">
        <h2 id="results-heading">{strings.resultsHeading}</h2>
        <CheckProgress onCancel={onCancel} />
      </section>
    )
  }

  if (status === 'error') {
    const message = strings.checkErrors[errorCode] ?? strings.checkErrors.UNKNOWN
    return (
      <section className="results" aria-labelledby="results-heading">
        <h2 id="results-heading">{strings.resultsHeading}</h2>
        <p role="alert">{message}</p>
        <div className="results-actions">
          <button type="button" onClick={onRetry}>
            {strings.resultsRetry}
          </button>
          <button type="button" onClick={onEdit}>
            {strings.resultsEditText}
          </button>
        </div>
      </section>
    )
  }

  if (cards.length === 0) {
    return (
      <section className="results" aria-labelledby="results-heading">
        <h2 id="results-heading">{strings.resultsHeading}</h2>
        <p className="hint">{strings.resultsEmpty}</p>
        <button type="button" onClick={onEdit}>
          {strings.resultsEditText}
        </button>
      </section>
    )
  }

  return (
    <section className="results" aria-labelledby="results-heading">
      <h2 id="results-heading">{strings.resultsHeading}</h2>
      {cards.map((card, index) => (
        <ClaimCard
          key={card.card_id ?? card.claim.id}
          card={card}
          recheck={recheck?.index === index ? recheck : null}
          onRecheck={onRecheck ? (text) => onRecheck(index, text) : undefined}
        />
      ))}
    </section>
  )
}
