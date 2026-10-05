import { strings } from '../strings.js'
import { InfoIcon } from './Icons.jsx'

export function AiNotice() {
  return (
    <p className="ai-notice" role="note">
      <InfoIcon />
      <span>{strings.aiNotice}</span>
    </p>
  )
}
