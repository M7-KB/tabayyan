import { strings } from '../../strings.js'

// The label is keyed on state_label_key, never on state alone (SPEC.md §6.4). The icon and the text
// carry the meaning as well, so the badge does not depend on colour.
const icons = {
  supported_confirms: '✓',
  supported_contradicts: '✕',
  supported_same_meaning: '≈',
  disputed: '⇄',
  cannot_confirm: '?',
  answer_from_source: '✓',
  correction_from_source: '✕',
}

// A question-origin claim asserts nothing, so «يؤيده» / «لا يطابق» would read as a verdict on the
// question's premise. Such a card names what the source gives instead. Stated claims and quoted
// verses keep their labels. Wording only: the state, its key and its colour are unchanged.
const questionLabels = {
  supported_confirms: 'answer_from_source',
  supported_contradicts: 'correction_from_source',
}

export function badgeLabelKey(labelKey, origin) {
  return origin && origin !== 'stated' ? questionLabels[labelKey] ?? labelKey : labelKey
}

export function StateBadge({ labelKey, origin }) {
  const shown = badgeLabelKey(labelKey, origin)
  return (
    <p className="state-badge" data-state={labelKey} data-label={shown}>
      <span aria-hidden="true">{icons[shown]}</span>
      <span>{strings.stateLabels[shown]}</span>
    </p>
  )
}
