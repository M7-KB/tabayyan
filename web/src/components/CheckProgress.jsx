import { useEffect, useState } from 'react'
import { strings } from '../strings.js'

const STAGE_INTERVAL_MS = 6_000

// Loading state for one check (U1). /check answers once, so the stages advance on a timer and are not measured
// progress. The last stage stays up until the answer arrives. The note under the stages says so.
export function CheckProgress({ onCancel }) {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setStage((current) => Math.min(current + 1, strings.checkStages.length - 1))
    }, STAGE_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="check-progress">
      <p role="status">{strings.resultsLoading}</p>
      <ol className="check-stages" aria-label={strings.checkStagesLabel}>
        {strings.checkStages.map((label, index) => (
          <li
            key={label}
            className={index < stage ? 'done' : index === stage ? 'active' : undefined}
            aria-current={index === stage ? 'step' : undefined}
          >
            {label}
          </li>
        ))}
      </ol>
      <p className="hint">{strings.checkStagesNote}</p>
      <div className="results-actions">
        <button type="button" onClick={onCancel}>
          {strings.checkCancel}
        </button>
      </div>
    </div>
  )
}
