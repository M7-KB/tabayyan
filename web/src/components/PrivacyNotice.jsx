import { features } from '../config/features.js'
import { strings } from '../strings.js'
import { ChevronIcon, ShieldIcon } from './Icons.jsx'

// One collapsed row. The visible line is the short privacy statement; opening it shows the full policy lines.
// With the audio flag on, the text names clips too (SPEC.md §6.6 item 5).
export function PrivacyNotice() {
  const summary = features.mediaUpload ? strings.privacySummaryMedia : strings.privacySummary
  const lines = features.mediaUpload ? strings.privacyLinesMedia : strings.privacyLines
  return (
    <details className="privacy-row">
      <summary>
        <ShieldIcon />
        <span>{summary}</span>
        <ChevronIcon />
      </summary>
      <ul>
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </details>
  )
}
