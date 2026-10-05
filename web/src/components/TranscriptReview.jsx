import { useEffect, useRef, useState } from 'react'
import { strings } from '../strings.js'

// Transcript review (SPEC.md §6.6, §0.9). The transcript is always shown and editable, and nothing
// runs after it until the user confirms it. `stub` marks sample text, which the screen says aloud.
export function TranscriptReview({ transcript, stub = false, onConfirm, onCancel }) {
  const [text, setText] = useState(transcript)
  const headingRef = useRef(null)
  const hasText = text.trim().length > 0

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  function handleSubmit(event) {
    event.preventDefault()
    if (hasText) onConfirm(text)
  }

  return (
    <section className="transcript-review" aria-labelledby="transcript-heading">
      <h2 id="transcript-heading" ref={headingRef} tabIndex={-1}>
        {strings.transcriptHeading}
      </h2>
      <p className="hint">{strings.transcriptHint}</p>
      {stub && <p className="hint">{strings.transcriptStubNote}</p>}

      <form onSubmit={handleSubmit}>
        <label htmlFor="transcript-input" className="transcript-label">
          {strings.transcriptLabel}
        </label>
        <textarea
          id="transcript-input"
          dir="auto"
          rows={8}
          value={text}
          onChange={(event) => setText(event.target.value)}
          aria-describedby={hasText ? undefined : 'transcript-empty-hint'}
        />
        {!hasText && (
          <p id="transcript-empty-hint" className="hint">
            {strings.transcriptEmpty}
          </p>
        )}

        <div className="review-actions">
          <button type="submit" disabled={!hasText}>
            {strings.transcriptConfirm}
          </button>
          <button type="button" onClick={onCancel}>
            {strings.transcriptDiscard}
          </button>
        </div>
      </form>
    </section>
  )
}
