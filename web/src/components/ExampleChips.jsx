import { strings } from '../strings.js'

// Each example is { label, text }. A tap fills the composer with the approved text; it does not submit.
export function ExampleChips({ examples, onPick }) {
  return (
    <div className="example-chips" role="group" aria-label={strings.examplesLabel}>
      {examples.map((example) => (
        <button key={example.label} type="button" className="example-chip" onClick={() => onPick(example.text)}>
          {example.label}
        </button>
      ))}
    </div>
  )
}
