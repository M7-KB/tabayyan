import { AiNotice } from './components/AiNotice.jsx'
import { InputScreen } from './components/InputScreen.jsx'
import { ThemeToggle } from './components/ThemeToggle.jsx'
import { CardPreview } from './dev/CardPreview.jsx'
import { strings } from './strings.js'

// No API call in this PR (T-406). The check endpoint is wired in T-504.
function handleSubmitText() {}

function handleSubmitMedia() {}

// Synthetic card preview for development only. Dead-code-eliminated from production builds.
const showCardPreview = import.meta.env.DEV && window.location.hash === '#card-preview'

export default function App() {
  if (showCardPreview) {
    return (
      <main id="main" tabIndex={-1}>
        <CardPreview />
      </main>
    )
  }

  return (
    <>
      <a className="skip-link" href="#main">
        {strings.skipToContent}
      </a>
      <p className="preview-banner">{strings.previewBanner}</p>
      <header className="app-header">
        <div className="theme-bar">
          <ThemeToggle />
        </div>
        <h1>{strings.appName}</h1>
        <p>{strings.tagline}</p>
        <AiNotice />
      </header>
      <main id="main" tabIndex={-1}>
        <InputScreen onSubmitText={handleSubmitText} onSubmitMedia={handleSubmitMedia} />
      </main>
    </>
  )
}
