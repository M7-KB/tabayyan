import { useId, useState } from 'react'
import { strings } from '../../strings.js'
import { formatSeconds } from './format.js'

// The first line of every card: how we understood the user's text (U1). The user can edit it and re-check only
// this card, in place. The text is the user's own, so it sits in data-role="user-text" (SPEC.md §6.4, G16).
// `onRecheck(text)` resolves to true when the card was replaced, so the form closes only on success and keeps
// the draft on error.
export function UnderstoodClaim({ claim, recheck = null, onRecheck }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const inputId = useId()
  const checking = recheck?.status === 'loading'

  function startEdit() {
    setDraft(claim.text_ar)
    setEditing(true)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (draft.trim().length === 0 || checking) return
    const replaced = await onRecheck(draft)
    if (replaced) setEditing(false)
  }

  return (
    <section className="claim-block" data-role="user-text" aria-label={strings.understoodHeading}>
      <div className="claim-heading">
        <h3>{strings.understoodHeading}</h3>
        {!editing && onRecheck && (
          <button type="button" className="edit-claim-button" onClick={startEdit} disabled={checking}>
            {strings.understoodEdit}
          </button>
        )}
      </div>

      {!editing && (
        <>
          <blockquote lang="ar" dir="rtl">
            {claim.text_ar}
          </blockquote>
          {claim.time_span && (
            <p className="timestamp">
              {strings.timestampFrom} {formatSeconds(claim.time_span.start_s)} {strings.timestampTo}{' '}
              {formatSeconds(claim.time_span.end_s)}
            </p>
          )}
        </>
      )}

      {editing && (
        <form className="understood-edit" onSubmit={handleSubmit}>
          <label htmlFor={inputId} className="transcript-label">
            {strings.understoodEditLabel}
          </label>
          <textarea id={inputId} dir="auto" rows={3} value={draft} onChange={(event) => setDraft(event.target.value)} />
          {draft.trim().length === 0 && <p className="hint">{strings.understoodEmpty}</p>}
          <div className="review-actions">
            <button type="submit" disabled={draft.trim().length === 0 || checking}>
              {strings.understoodRecheck}
            </button>
            <button type="button" onClick={() => setEditing(false)} disabled={checking}>
              {strings.understoodCancel}
            </button>
          </div>
        </form>
      )}

      {checking && <p role="status">{strings.recheckLoading}</p>}
      {recheck?.status === 'error' && (
        <p role="alert">{strings.checkErrors[recheck.errorCode] ?? strings.checkErrors.UNKNOWN}</p>
      )}
    </section>
  )
}
