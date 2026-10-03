import { strings } from '../../strings.js'

// The label is keyed on state_label_key, never on state alone (SPEC.md §6.4). The icon and the text
// carry the meaning as well, so the badge does not depend on colour.
const icons = {
  supported_confirms: '✓',
  supported_contradicts: '✕',
  disputed: '⇄',
  cannot_confirm: '?',
}

export function StateBadge({ labelKey }) {
  return (
    <p className="state-badge" data-state={labelKey}>
      <span aria-hidden="true">{icons[labelKey]}</span>
      <span>{strings.stateLabels[labelKey]}</span>
    </p>
  )
}
