import { strings } from '../strings.js'

export function PrivacyNotice() {
  return (
    <section className="privacy-notice" aria-labelledby="privacy-heading">
      <h2 id="privacy-heading">{strings.privacyHeading}</h2>
      <ul>
        {strings.privacyLines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </section>
  )
}
