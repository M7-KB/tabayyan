import { useState } from 'react'
import { strings } from '../strings.js'
import { PrivacyNotice } from './PrivacyNotice.jsx'

export function InputScreen({ onSubmitText, onSubmitMedia }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [consent, setConsent] = useState(false)

  const hasText = text.trim().length > 0
  const canUpload = file !== null && consent

  let uploadHint = null
  if (!file) {
    uploadHint = strings.uploadNoFileHint
  } else if (!consent) {
    uploadHint = strings.uploadNoConsentHint
  }

  function handleTextSubmit(event) {
    event.preventDefault()
    if (hasText) onSubmitText(text)
  }

  function handleUploadSubmit(event) {
    event.preventDefault()
    if (canUpload) onSubmitMedia(file)
  }

  return (
    <section className="input-screen" aria-labelledby="input-heading">
      <h2 id="input-heading">{strings.inputHeading}</h2>

      <form className="text-form" onSubmit={handleTextSubmit}>
        <label htmlFor="text-input">{strings.textLabel}</label>
        <textarea
          id="text-input"
          dir="auto"
          rows={6}
          placeholder={strings.textPlaceholder}
          value={text}
          onChange={(event) => setText(event.target.value)}
          aria-describedby={hasText ? undefined : 'text-empty-hint'}
        />
        {!hasText && (
          <p id="text-empty-hint" className="hint">
            {strings.textEmptyHint}
          </p>
        )}

        <PrivacyNotice />

        <button type="submit" disabled={!hasText}>
          {strings.textSubmit}
        </button>
      </form>

      <form className="upload-form" onSubmit={handleUploadSubmit}>
        <fieldset>
          <legend>{strings.uploadHeading}</legend>
          <p className="hint">{strings.uploadLimits}</p>

          <label className="file-label">
            <span>{strings.uploadChooseFile}</span>
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={(event) => setFile(event.target.files[0] ?? null)}
            />
          </label>
          {file && <p className="file-name">{file.name}</p>}

          <label className="consent-label">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>{strings.consent}</span>
          </label>

          {uploadHint && <p className="hint">{uploadHint}</p>}

          <button type="submit" disabled={!canUpload}>
            {strings.uploadSubmit}
          </button>
        </fieldset>
      </form>
    </section>
  )
}
