import { strings } from '../../strings.js'
import { ExplanationBlock } from './ExplanationBlock.jsx'
import { ScriptureBlock } from './ScriptureBlock.jsx'
import { hasCompleteGrading } from './format.js'

// Shown without an alignment badge (SPEC.md §4.1). The matched text is scripture: it uses the same
// evidence block as evidence[], so its source, reference, grading and source links are visible. The note is generated.
// A notice without that provenance, or a hadith notice without complete grading, is not shown (AGENTS.md non-negotiable 1).
export function MisquoteNotice({ notice }) {
  const evidence = notice?.evidence
  if (!evidence || (evidence.domain === 'hadith' && !hasCompleteGrading(evidence.grading))) return null

  return (
    <section className="misquote-notice">
      <h3>{strings.misquoteHeading}</h3>
      <ScriptureBlock item={evidence} />
      <ExplanationBlock textAr={notice.note_ar} />
    </section>
  )
}
