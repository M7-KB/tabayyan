import { strings } from '../strings.js'
import { ClaimCard } from './card/ClaimCard.jsx'

// Result area for one check. Loading, error and empty states each give a next step (agent brief).
// `status` is 'loading' | 'error' | 'done'. Error copy is looked up by the server's error code.
export function Results({ status, cards = [], errorCode, onRetry, onEdit }) {
  if (status === 'loading') {
    return (
      <section className="results" aria-labelledby="results-heading">
        <h2 id="results-heading">{strings.resultsHeading}</h2>
        <p role="status">{strings.resultsLoading}</p>
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
      {cards.map((card) => (
        <ClaimCard key={card.card_id ?? card.claim.id} card={card} />
      ))}
      {onEdit && (
        <div className="results-actions">
          <button type="button" onClick={onEdit}>
            {strings.resultsEditClaims}
          </button>
        </div>
      )}
    </section>
  )
}
