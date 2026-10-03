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
