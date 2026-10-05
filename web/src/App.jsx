import { useEffect, useRef, useState } from 'react'
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
import { API_BASE_URL, CHECK_DEADLINE_MS, EXTRACT_DEADLINE_MS } from './config/api.js'
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

  // One extract or check request is in flight at a time. Each has a client deadline, and a cancel that aborts
  // it. Only the latest attempt may update the flow, so a cancelled, timed-out or superseded response is dropped.
  const attemptRef = useRef(null)

  function beginAttempt(deadlineMs) {
    attemptRef.current?.cancel()
    const controller = new AbortController()
    const attempt = {
      signal: controller.signal,
      timedOut: false,
      timer: setTimeout(() => {
        attempt.timedOut = true
        controller.abort()
      }, deadlineMs),
      cancel() {
        clearTimeout(attempt.timer)
        controller.abort()
      },
    }
    attemptRef.current = attempt
    return attempt
  }

  function cancelPending() {
    attemptRef.current?.cancel()
    attemptRef.current = null
  }

  function failureCodeOf(attempt, error) {
    return attempt.timedOut ? 'TIMEOUT' : errorCodeOf(error)
  }

  async function handleSubmitText(inputText) {
    setFlow({ step: 'extracting', inputText })
    const attempt = beginAttempt(EXTRACT_DEADLINE_MS)
    try {
      const extraction = await postExtract(inputText, { baseUrl: API_BASE_URL, signal: attempt.signal })
      if (attemptRef.current === attempt) {
        setFlow({
          step: 'confirm',
          inputText,
          inputKind: extraction.input_kind,
          claims: extraction.claims,
          edits: {},
        })
      }
    } catch (error) {
      if (attemptRef.current === attempt) {
        setFlow({ step: 'extract-error', inputText, errorCode: failureCodeOf(attempt, error) })
      }
    } finally {
      clearTimeout(attempt.timer)
    }
  }

  async function runCheck(state, checked) {
    setFlow({ ...state, step: 'checking', checked })
    const attempt = beginAttempt(CHECK_DEADLINE_MS)
    try {
      const request = buildCheckRequest({ claims: checked, inputKind: state.inputKind })
      const result = await postCheck(request, { baseUrl: API_BASE_URL, signal: attempt.signal })
      if (attemptRef.current === attempt) {
        setFlow({ ...state, step: 'results', checked, cards: result.cards })
      }
    } catch (error) {
      if (attemptRef.current === attempt) {
        setFlow({ ...state, step: 'check-error', checked, errorCode: failureCodeOf(attempt, error) })
      }
    } finally {
      clearTimeout(attempt.timer)
    }
  }

  function handleEditClaim(id, value) {
    setFlow((prev) => ({ ...prev, edits: { ...prev.edits, [id]: value } }))
  }

  // Claims are sent only after the user confirms them. Emptied claims are dropped here.
  function handleConfirmClaims(kept) {
    runCheck(flow, kept)
  }

  // Going back cancels any pending request. The input text, claims and edits stay in the flow state.
  function backToInput() {
    cancelPending()
    setFlow({ step: 'input', inputText: flow.inputText })
  }

  function backToClaims() {
    cancelPending()
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
        {flow.step === 'extracting' && <ClaimReview status="loading" onCancel={backToInput} />}
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
        {flow.step === 'checking' && <Results status="loading" onCancel={backToClaims} />}
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
