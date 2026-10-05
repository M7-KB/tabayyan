import { strings } from '../strings.js'
import { CheckProgress } from './CheckProgress.jsx'
import { ClaimCard } from './card/ClaimCard.jsx'

// Result area for the one-page flow (U1). Loading, error and empty states each give a next step (agent brief).
// `status` is 'loading' | 'error' | 'done'. Error copy is looked up by the server's error code.
// On 'done', each card can be edited and re-checked in place: `onRecheck(index, text)` resolves to true when
// that card was replaced. `recheck` names the card being re-checked and its state.
export function Results({ status, cards = [], retryableResults = [], errorCode, recheck = null, onRetry, onEdit, onCancel, onRecheck }) {
  // Keep the card list at the same tree position during retry, so local edits survive.
  return (
    <section className="results" aria-labelledby="results-heading">
      <h2 id="results-heading">{strings.resultsHeading}</h2>
      {status === 'loading' && <CheckProgress onCancel={onCancel} />}
      {status === 'error' && (
        <div>
          <p role="alert">{strings.checkErrors[errorCode] ?? strings.checkErrors.UNKNOWN}</p>
          <div className="results-actions">
            <button type="button" onClick={onRetry}>{strings.resultsRetry}</button>
            <button type="button" onClick={onEdit}>{strings.resultsEditText}</button>
          </div>
        </div>
      )}
      {status === 'done' && cards.length === 0 && retryableResults.length === 0 && (
        <div>
          <p className="hint">{strings.resultsEmpty}</p>
          <button type="button" onClick={onEdit}>{strings.resultsEditText}</button>
        </div>
      )}
      {retryableResults.length > 0 && (
        <div className="retryable-results">
          {status === 'done' && <p role="status">{strings.checkErrors.CHECK_INCOMPLETE}</p>}
          <ul data-role="user-text" dir="auto">
            {retryableResults.map((result) => <li key={result.claim_id}>{result.text_ar}</li>)}
          </ul>
          {status === 'done' && <div className="results-actions">
            <button type="button" onClick={onRetry}>{strings.resultsRetry}</button>
            <button type="button" onClick={onEdit}>{strings.resultsEditText}</button>
          </div>}
        </div>
      )}
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
