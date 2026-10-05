import { useRef, useState } from 'react'
import { strings } from '../strings.js'
import { features } from '../config/features.js'
import { ExampleChips } from './ExampleChips.jsx'
import { PrivacyNotice } from './PrivacyNotice.jsx'
import { SendIcon } from './Icons.jsx'

export function InputScreen({ onSubmitText, onSubmitMedia }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [consent, setConsent] = useState(false)
  const textareaRef = useRef(null)

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

  // A chip fills the composer and moves focus there. It never submits.
  function handleExamplePick(exampleText) {
    setText(exampleText)
    textareaRef.current?.focus()
  }

  return (
    <section className="input-screen" aria-labelledby="input-heading">
      <h2 id="input-heading" className="sr-only">
        {strings.inputHeading}
      </h2>

      <form className="text-form" onSubmit={handleTextSubmit}>
        <div className="composer">
          <label htmlFor="text-input" className="sr-only">
            {strings.textLabel}
          </label>
          <textarea
            id="text-input"
            ref={textareaRef}
            dir="auto"
            rows={4}
            placeholder={strings.textPlaceholder}
            value={text}
            onChange={(event) => setText(event.target.value)}
            aria-describedby={hasText ? undefined : 'text-empty-hint'}
          />
          <div className="composer-bar">
            <button type="submit" className="send-button" disabled={!hasText} aria-label={strings.textSubmit}>
              <SendIcon />
            </button>
          </div>
        </div>
        {!hasText && (
          <p id="text-empty-hint" className="hint">
            {strings.textEmptyHint}
          </p>
        )}
      </form>

      {features.exampleChips && strings.exampleChips.length > 0 && (
        <ExampleChips examples={strings.exampleChips} onPick={handleExamplePick} />
      )}

      <PrivacyNotice />

      {features.mediaUpload && (
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
      )}
    </section>
  )
}
