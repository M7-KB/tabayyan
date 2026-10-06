import { useEffect, useRef, useState } from 'react'
import { AiNotice } from './components/AiNotice.jsx'
import { ArchMark } from './components/ArchMark.jsx'
import { InputScreen } from './components/InputScreen.jsx'
import { MediaStatus } from './components/MediaStatus.jsx'
import { Results } from './components/Results.jsx'
import { ThemeToggle } from './components/ThemeToggle.jsx'
import { TranscriptReview } from './components/TranscriptReview.jsx'
import { CardPreview } from './dev/CardPreview.jsx'
import { buildCheckRequest, postCheck } from './api/check.js'
import { checkApiHealth } from './api/health.js'
import { ApiError } from './api/http.js'
import { MediaError, transcribeStub } from './api/transcribe.js'
import { API_BASE_URL, CHECK_DEADLINE_MS } from './config/api.js'
import { strings } from './strings.js'

// Synthetic card preview for development only. Dead-code-eliminated from production builds.
const showCardPreview = import.meta.env.DEV && window.location.hash === '#card-preview'

function errorCodeOf(error) {
  return error instanceof ApiError ? error.code : 'UNKNOWN'
}

// Replaces one card with the cards the server returned for its re-check. The rest of the list is untouched.
function replaceCard(cards, index, replacement) {
  return [...cards.slice(0, index), ...replacement, ...cards.slice(index + 1)]
}

export default function App() {
  // idle: input screen. transcribing / error / review: the clip flow behind features.mediaUpload.
  const [media, setMedia] = useState({ status: 'idle' })
  // One-page flow (U1): the input stays on top and the results sit below it. `check` is null until the first
  // submit. `recheck` names the one card being re-checked in place, and its state.
  const [check, setCheck] = useState(null)
  const [recheck, setRecheck] = useState(null)
  // The preview banner stays up until GET /health answers.
  const [apiLive, setApiLive] = useState(false)
  // One request is in flight at a time. Each has a client deadline and a cancel that aborts it. Only the latest
  // attempt may update the screen, so a cancelled, timed-out or superseded response is dropped.
  const attemptRef = useRef(null)

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

  function beginAttempt(deadlineMs, onTimeout) {
    attemptRef.current?.cancel()
    const controller = new AbortController()
    const attempt = {
      signal: controller.signal,
      timedOut: false,
      timer: setTimeout(() => {
        attempt.timedOut = true
        controller.abort()
        if (attemptRef.current === attempt) {
          attemptRef.current = null
          onTimeout()
        }
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

  // Sends the text as the user wrote it. The server extracts the claims and answers with one card per claim.
  async function runCheck(originalText, { retainResults = false } = {}) {
    cancelPending()
    setRecheck(null)
    const retained = retainResults ? {
      cards: check?.cards, retryableResults: check?.retryableResults,
    } : {}
    setCheck({ ...retained, status: 'loading', submittedText: originalText })
    // A fresh submission (retainResults false) replaces everything: no earlier question's
    // cards survive loading or an error. Only a retry of the same text keeps its cards.
    const attempt = beginAttempt(CHECK_DEADLINE_MS, () => {
      setCheck({ ...retained, status: 'error', submittedText: originalText, errorCode: 'TIMEOUT' })
    })
    try {
      const request = buildCheckRequest({ originalText })
      const result = await postCheck(request, { baseUrl: API_BASE_URL, signal: attempt.signal })
      if (attemptRef.current === attempt) {
        setCheck({
          status: 'done', submittedText: originalText, cards: result.cards,
          retryableResults: result.retryable_results ?? [],
        })
      }
    } catch (error) {
      if (attemptRef.current === attempt) {
        setCheck({ ...retained, status: 'error', submittedText: originalText, errorCode: failureCodeOf(attempt, error) })
      }
    } finally {
      clearTimeout(attempt.timer)
    }
  }

  // Re-checks one card with the text the user edited on it. Resolves to true only when the card was replaced, so
  // the card's edit form closes on success and keeps the draft on error. A card is never blanked by a re-check.
  async function recheckCard(index, text) {
    if (check?.status !== 'done' || text.trim().length === 0) return false
    cancelPending()
    setRecheck({ index, status: 'loading' })
    const attempt = beginAttempt(CHECK_DEADLINE_MS, () => {
      setRecheck({ index, status: 'error', errorCode: 'TIMEOUT' })
    })
    try {
      const request = buildCheckRequest({ originalText: text })
      const result = await postCheck(request, { baseUrl: API_BASE_URL, signal: attempt.signal })
      // A partial result still carries finished cards; only an empty result is an error.
      if (result.cards.length === 0) {
        throw new ApiError(result.retryable_results?.length ? 'CHECK_INCOMPLETE' : 'PIPELINE_DEGRADED')
      }
      if (attemptRef.current !== attempt) return false
      setCheck((prev) => ({ ...prev, cards: replaceCard(prev.cards, index, result.cards) }))
      setRecheck(null)
      return true
    } catch (error) {
      if (attemptRef.current === attempt) {
        setRecheck({ index, status: 'error', errorCode: failureCodeOf(attempt, error) })
      }
      return false
    } finally {
      clearTimeout(attempt.timer)
    }
  }

  // Cancel keeps the input text, since the input stays on the page. The check is dropped.
  function cancelCheck() {
    cancelPending()
    setRecheck(null)
    setCheck((prev) => prev?.cards || prev?.retryableResults
      ? { ...prev, status: 'done', errorCode: undefined }
      : null)
  }

  function focusInput() {
    document.getElementById('text-input')?.focus()
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

  // A confirmed transcript is checked like typed text. The clip flow stays behind features.mediaUpload.
  function handleConfirmTranscript(transcript) {
    setMedia({ status: 'idle' })
    runCheck(transcript)
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
        {media.status === 'idle' && <InputScreen onSubmitText={runCheck} onSubmitMedia={handleSubmitMedia} />}
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
            onConfirm={handleConfirmTranscript}
            onCancel={() => setMedia({ status: 'idle' })}
          />
        )}
        {check && (
          <Results
            status={check.status}
            cards={check.cards}
            retryableResults={check.retryableResults}
            errorCode={check.errorCode}
            recheck={recheck}
            onRecheck={recheckCard}
            onRetry={() => runCheck(check.submittedText, { retainResults: true })}
            onEdit={focusInput}
            onCancel={cancelCheck}
          />
        )}
        <p className="footer-note">{strings.quoteSourceNote}</p>
      </main>
    </>
  )
}
