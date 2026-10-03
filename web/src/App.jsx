import { AiNotice } from './components/AiNotice.jsx'
import { InputScreen } from './components/InputScreen.jsx'
import { strings } from './strings.js'

// No API call in this PR (T-406). The check endpoint is wired in T-504.
function handleSubmitText() {}

function handleSubmitMedia() {}

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main">
        {strings.skipToContent}
      </a>
      <p className="preview-banner">{strings.previewBanner}</p>
      <header className="app-header">
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
