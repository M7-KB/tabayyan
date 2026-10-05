import { useEffect, useRef } from 'react'
import { strings } from '../strings.js'

// Claim review (SPEC.md §6.2). The extracted claims are shown as editable text, and nothing is checked until the
// user confirms. Emptying a claim's text drops it. `status` is 'loading' | 'confirm' | 'error'.
// `edits` maps claim id to the user's text, so the screen can switch states without losing what the user typed.
export function ClaimReview({ status, claims = [], edits = {}, errorCode, onEdit, onConfirm, onBack, onRetry, onCancel }) {
  const headingRef = useRef(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [status])

  if (status === 'loading') {
    return (
      <section className="transcript-review claim-review" aria-labelledby="claims-heading">
        <h2 id="claims-heading" ref={headingRef} tabIndex={-1}>
          {strings.extractingHeading}
        </h2>
        <p role="status">{strings.extracting}</p>
        <div className="review-actions">
          <button type="button" onClick={onCancel}>
            {strings.extractCancel}
          </button>
        </div>
      </section>
    )
  }

  if (status === 'error') {
    const message = strings.checkErrors[errorCode] ?? strings.checkErrors.UNKNOWN
    return (
      <section className="transcript-review claim-review" aria-labelledby="claims-heading">
        <h2 id="claims-heading" ref={headingRef} tabIndex={-1}>
          {strings.extractErrorHeading}
        </h2>
        <p role="alert">{message}</p>
        <div className="review-actions">
          <button type="button" onClick={onRetry}>
            {strings.extractRetry}
          </button>
          <button type="button" onClick={onBack}>
            {strings.claimsBack}
          </button>
        </div>
      </section>
    )
  }

  const textOf = (claim) => edits[claim.id] ?? claim.text_ar
  const kept = claims
    .map((claim) => ({ ...claim, text_ar: textOf(claim).trim() }))
    .filter((claim) => claim.text_ar.length > 0)

  function handleSubmit(event) {
    event.preventDefault()
    if (kept.length > 0) onConfirm(kept)
  }

  if (claims.length === 0) {
    return (
      <section className="transcript-review claim-review" aria-labelledby="claims-heading">
        <h2 id="claims-heading" ref={headingRef} tabIndex={-1}>
          {strings.claimsHeading}
        </h2>
        <p className="hint">{strings.claimsEmpty}</p>
        <div className="review-actions">
          <button type="button" onClick={onBack}>
            {strings.claimsBack}
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="transcript-review claim-review" aria-labelledby="claims-heading">
      <h2 id="claims-heading" ref={headingRef} tabIndex={-1}>
        {strings.claimsHeading}
      </h2>
      <p className="hint">{strings.claimsHint}</p>

      <form onSubmit={handleSubmit}>
        {claims.map((claim, index) => (
          <div className="claim-edit" key={claim.id}>
            <label htmlFor={`claim-input-${index}`} className="transcript-label">
              {`${strings.claimLabel} ${index + 1}`}
            </label>
            <textarea
              id={`claim-input-${index}`}
              dir="auto"
              rows={3}
              value={textOf(claim)}
              onChange={(event) => onEdit(claim.id, event.target.value)}
            />
          </div>
        ))}

        {kept.length === 0 && (
          <p className="hint">{strings.claimsNoneLeft}</p>
        )}

        <div className="review-actions">
          <button type="submit" disabled={kept.length === 0}>
            {strings.claimsConfirm}
          </button>
          <button type="button" onClick={onBack}>
            {strings.claimsBack}
          </button>
        </div>
      </form>
    </section>
  )
}
