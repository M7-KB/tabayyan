import { useState } from 'react'
import { AiNotice } from './components/AiNotice.jsx'
import { ArchMark } from './components/ArchMark.jsx'
import { InputScreen } from './components/InputScreen.jsx'
import { MediaStatus } from './components/MediaStatus.jsx'
import { ThemeToggle } from './components/ThemeToggle.jsx'
import { TranscriptReview } from './components/TranscriptReview.jsx'
import { CardPreview } from './dev/CardPreview.jsx'
import { MediaError, transcribeStub } from './api/transcribe.js'
import { strings } from './strings.js'

// No API call in this PR (T-406). The check endpoint is wired in T-504.
function handleSubmitText() {}

// Synthetic card preview for development only. Dead-code-eliminated from production builds.
const showCardPreview = import.meta.env.DEV && window.location.hash === '#card-preview'

export default function App() {
  // idle: input screen. transcribing / error / review: the clip flow behind features.mediaUpload.
  const [media, setMedia] = useState({ status: 'idle' })

  if (showCardPreview) {
    return (
      <main id="main" tabIndex={-1}>
        <CardPreview />
      </main>
    )
  }

  async function handleSubmitMedia(file) {
    setMedia({ status: 'transcribing' })
    try {
      const result = await transcribeStub(file)
      setMedia({ status: 'review', transcript: result.transcript_ar, stub: result.stub === true })
    } catch (error) {
      setMedia({ status: 'error', errorCode: error instanceof MediaError ? error.code : 'UNKNOWN' })
    }
  }

  return (
    <>
      <a className="skip-link" href="#main">
        {strings.skipToContent}
      </a>
      <p className="preview-banner">{strings.previewBanner}</p>
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
        {media.status === 'idle' && (
          <InputScreen onSubmitText={handleSubmitText} onSubmitMedia={handleSubmitMedia} />
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
            stub={media.stub}
            onConfirm={handleSubmitText}
            onCancel={() => setMedia({ status: 'idle' })}
          />
        )}
        <p className="footer-note">{strings.quoteSourceNote}</p>
      </main>
    </>
  )
}
