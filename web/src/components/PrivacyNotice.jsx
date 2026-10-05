import { strings } from '../strings.js'
import { ChevronIcon, ShieldIcon } from './Icons.jsx'

// One collapsed row. The visible line is the short privacy statement; opening it shows the full policy lines.
export function PrivacyNotice() {
  return (
    <details className="privacy-row">
      <summary>
        <ShieldIcon />
        <span>{strings.privacySummary}</span>
        <ChevronIcon />
      </summary>
      <ul>
        {strings.privacyLines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </details>
  )
}
