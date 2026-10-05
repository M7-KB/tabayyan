// Thin arch line-art in muted gold (--c-gold). Decorative only: the page heading carries the name.
export function ArchMark() {
  return (
    <svg
      viewBox="0 0 120 68"
      width="96"
      height="54"
      fill="none"
      stroke="currentColor"
      strokeWidth="1"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M30 56V34C30 16.5 43 5 60 5S90 16.5 90 34v22" />
      <path d="M40 56V35c0-10.5 8-18 20-18s20 7.5 20 18v21" />
      <path d="M18 16l6 6-6 6-6-6Z" />
      <path d="M102 16l6 6-6 6-6-6Z" />
      <circle cx="60" cy="63" r="2" />
    </svg>
  )
}
