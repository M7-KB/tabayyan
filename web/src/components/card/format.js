export function formatRef(ref) {
  if (!ref) return ''
  if (ref.surah && ref.ayah) return `سورة ${ref.surah}، الآية ${ref.ayah}`
  return Object.values(ref).join('، ')
}

export function formatSeconds(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.floor(totalSeconds % 60)
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

// A hadith grading is shown only when all three fields are present, non-empty, and the grading link is https
// (contracts/card.schema.json $defs/grading). Partial or empty grading is never displayed as a grade.
const GRADING_FIELDS = ['grade_ar', 'grader_ar', 'grading_source_url']

export function hasCompleteGrading(grading) {
  if (!grading) return false
  const complete = GRADING_FIELDS.every((field) => typeof grading[field] === 'string' && grading[field].trim() !== '')
  return complete && /^https:\/\/\S+$/.test(grading.grading_source_url)
}
