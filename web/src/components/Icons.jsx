// Decorative icons. Each one sits beside a text label, so the SVG is hidden from assistive tech.
const common = { viewBox: '0 0 24 24', width: 20, height: 20, 'aria-hidden': true, focusable: 'false' }

export function SendIcon() {
  return (
    <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </svg>
  )
}

export function InfoIcon() {
  return (
    <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5" />
      <path d="M12 7.5v.01" />
    </svg>
  )
}

export function ShieldIcon() {
  return (
    <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round">
      <path d="M12 3 5 6v5c0 4.5 3 8.2 7 10 4-1.8 7-5.5 7-10V6l-7-3Z" />
      <path d="m9 12 2 2 4-4" strokeLinecap="round" />
    </svg>
  )
}

export function ChevronIcon() {
  return (
    <svg {...common} className="chevron" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}
