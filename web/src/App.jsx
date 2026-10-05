import { useEffect, useState } from 'react'
import { AiNotice } from './components/AiNotice.jsx'
import { ArchMark } from './components/ArchMark.jsx'
import { ClaimReview } from './components/ClaimReview.jsx'
import { InputScreen } from './components/InputScreen.jsx'
import { MediaStatus } from './components/MediaStatus.jsx'
import { Results } from './components/Results.jsx'
import { ThemeToggle } from './components/ThemeToggle.jsx'
import { TranscriptReview } from './components/TranscriptReview.jsx'
import { CardPreview } from './dev/CardPreview.jsx'
import { buildCheckRequest, postCheck } from './api/check.js'
import { postExtract } from './api/extract.js'
import { checkApiHealth } from './api/health.js'
import { ApiError } from './api/http.js'
import { MediaError, transcribeStub } from './api/transcribe.js'
import { API_BASE_URL } from './config/api.js'
import { strings } from './strings.js'

// Synthetic card preview for development only. Dead-code-eliminated from production builds.
const showCardPreview = import.meta.env.DEV && window.location.hash === '#card-preview'

function errorCodeOf(error) {
  return error instanceof ApiError ? error.code : 'UNKNOWN'
}

export default function App() {
  // idle: input screen. transcribing / error / review: the clip flow behind features.mediaUpload.
  const [media, setMedia] = useState({ status: 'idle' })
  // Text flow (SPEC.md §6.2): input → extracting → confirm claims → checking → results.
  const [flow, setFlow] = useState({ step: 'input' })
  // The preview banner stays up until GET /health answers.
  const [apiLive, setApiLive] = useState(false)

  useEffect(() => {
    let active = true
    checkApiHealth({ baseUrl: API_BASE_URL }).then((live) => {
      if (active) setApiLive(live)
    })
    return () => {
      active = false
    }
  }, [])

  if (showCardPreview) {
    return (
      <main id="main" tabIndex={-1}>
        <CardPreview />
      </main>
    )
  }

  async function handleSubmitText(inputText) {
    setFlow({ step: 'extracting', inputText })
    try {
      const extraction = await postExtract(inputText, { baseUrl: API_BASE_URL })
      setFlow({
        step: 'confirm',
        inputText,
        inputKind: extraction.input_kind,
        claims: extraction.claims,
        edits: {},
      })
    } catch (error) {
      setFlow({ step: 'extract-error', inputText, errorCode: errorCodeOf(error) })
    }
  }

  async function runCheck(state, checked) {
    setFlow({ ...state, step: 'checking', checked })
    try {
      const request = buildCheckRequest({ claims: checked, inputKind: state.inputKind })
      const result = await postCheck(request, { baseUrl: API_BASE_URL })
      setFlow({ ...state, step: 'results', checked, cards: result.cards })
    } catch (error) {
      setFlow({ ...state, step: 'check-error', checked, errorCode: errorCodeOf(error) })
    }
  }

  function handleEditClaim(id, value) {
    setFlow((prev) => ({ ...prev, edits: { ...prev.edits, [id]: value } }))
  }

  // Claims are sent only after the user confirms them. Emptied claims are dropped here.
  function handleConfirmClaims(kept) {
    runCheck(flow, kept)
  }

  function backToInput() {
    setFlow({ step: 'input', inputText: flow.inputText })
  }

  function backToClaims() {
    setFlow((prev) => ({ ...prev, step: 'confirm' }))
  }

  async function handleSubmitMedia(file) {
    setMedia({ status: 'transcribing' })
    try {
      const result = await transcribeStub(file)
      setMedia({
        status: 'review',
        transcript: result.transcript_ar,
        notice: result.notice_ar,
        stub: result.stub === true,
      })
    } catch (error) {
      setMedia({ status: 'error', errorCode: error instanceof MediaError ? error.code : 'UNKNOWN' })
    }
  }

  return (
    <>
      <a className="skip-link" href="#main">
        {strings.skipToContent}
      </a>
      {!apiLive && <p className="preview-banner">{strings.previewBanner}</p>}
      <header className="app-header">
        <div className="top-row">
          <span className="brand-small">{strings.appName}</span>
          <ThemeToggle />
        </div>
        <div className="hero">
          <ArchMark />
          <h1>{strings.appName}</h1>
          <p>{strings.tagline}</p>
          <AiNotice />
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {media.status === 'idle' && flow.step === 'input' && (
          <InputScreen
            onSubmitText={handleSubmitText}
            onSubmitMedia={handleSubmitMedia}
            initialText={flow.inputText}
          />
        )}
        {(media.status === 'transcribing' || media.status === 'error') && (
          <MediaStatus
            status={media.status}
            errorCode={media.errorCode}
            onBack={() => setMedia({ status: 'idle' })}
          />
        )}
        {media.status === 'review' && (
          <TranscriptReview
            transcript={media.transcript}
            notice={media.notice}
            stub={media.stub}
            onConfirm={handleSubmitText}
            onCancel={() => setMedia({ status: 'idle' })}
          />
        )}
        {flow.step === 'extracting' && <ClaimReview status="loading" />}
        {flow.step === 'extract-error' && (
          <ClaimReview
            status="error"
            errorCode={flow.errorCode}
            onRetry={() => handleSubmitText(flow.inputText)}
            onBack={backToInput}
          />
        )}
        {flow.step === 'confirm' && (
          <ClaimReview
            status="confirm"
            claims={flow.claims}
            edits={flow.edits}
            onEdit={handleEditClaim}
            onConfirm={handleConfirmClaims}
            onBack={backToInput}
          />
        )}
        {flow.step === 'checking' && <Results status="loading" />}
        {flow.step === 'results' && <Results status="done" cards={flow.cards} onEdit={backToClaims} />}
        {flow.step === 'check-error' && (
          <Results
            status="error"
            errorCode={flow.errorCode}
            onRetry={() => runCheck(flow, flow.checked)}
            onEdit={backToClaims}
          />
        )}
        <p className="footer-note">{strings.quoteSourceNote}</p>
      </main>
    </>
  )
}
