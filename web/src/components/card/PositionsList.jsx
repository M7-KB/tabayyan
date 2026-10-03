import { strings } from '../../strings.js'
import { ExplanationBlock } from './ExplanationBlock.jsx'
import { ScriptureBlock } from './ScriptureBlock.jsx'

// Positions are rendered in the order the card gives them (corpus order). No ranking, score or
// preference is shown (SPEC.md §4.1).
export function PositionsList({ positions, evidenceById }) {
  return (
    <section className="positions">
      <h3>{strings.positionsHeading}</h3>
      <ol>
        {positions.map((position) => (
          <li key={position.position_id}>
            <h4>{position.label_ar}</h4>
            <ExplanationBlock textAr={position.summary_ar} />
            {position.evidence_ids.map((id) =>
              evidenceById[id] ? <ScriptureBlock key={id} item={evidenceById[id]} /> : null,
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}
