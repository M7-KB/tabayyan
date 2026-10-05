import { strings } from '../strings.js'

// Loading and error states for a clip before its transcript is ready. Each gives a next step.
export function MediaStatus({ status, errorCode, onBack }) {
  if (status === 'transcribing') {
    return (
      <section className="transcript-review" aria-labelledby="media-heading">
        <h2 id="media-heading">{strings.transcribingHeading}</h2>
        <p role="status">{strings.transcribing}</p>
      </section>
    )
  }

  const message = strings.transcribeErrors[errorCode] ?? strings.transcribeErrors.UNKNOWN
  return (
    <section className="transcript-review" aria-labelledby="media-heading">
      <h2 id="media-heading">{strings.mediaErrorHeading}</h2>
      <p role="alert">{message}</p>
      <div className="review-actions">
        <button type="button" onClick={onBack}>
          {strings.mediaErrorBack}
        </button>
      </div>
    </section>
  )
}
