// Light or dark theme. With no saved choice the page follows the system setting. A choice made with the
// header toggle is kept in localStorage only: no account, no server, no cookie (AGENTS.md non-negotiable 4).
export const STORAGE_KEY = 'tabayyan-theme'
const DARK_QUERY = '(prefers-color-scheme: dark)'

// The choice made on this page view. It keeps the choice even when localStorage is blocked.
let pageChoice = null

function readChoice() {
  if (pageChoice) return pageChoice
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : null
  } catch {
    return null
  }
}

export function systemTheme() {
  return window.matchMedia?.(DARK_QUERY).matches ? 'dark' : 'light'
}

export function currentTheme() {
  return document.documentElement.dataset.theme || readChoice() || systemTheme()
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
}

export function saveChoice(theme) {
  pageChoice = theme
  try {
    window.localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // Storage is blocked: the choice lasts for this page view only.
  }
}

// Clears the page-view choice. Used by tests to start each case from no choice.
export function resetPageChoice() {
  pageChoice = null
}

// Follows the system setting while the user has not chosen a theme.
export function subscribeToSystem(onChange) {
  const query = window.matchMedia?.(DARK_QUERY)
  if (!query) return () => {}
  const handler = () => {
    if (readChoice() !== null) return
    const theme = systemTheme()
    applyTheme(theme)
    onChange(theme)
  }
  query.addEventListener('change', handler)
  return () => query.removeEventListener('change', handler)
}
