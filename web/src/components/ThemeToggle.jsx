import { useEffect, useState } from 'react'
import { strings } from '../strings.js'
import { applyTheme, currentTheme, saveChoice, subscribeToSystem } from '../theme.js'

// The button names the action it performs. The icon is decorative; the label carries the meaning.
export function ThemeToggle() {
  const [theme, setTheme] = useState(currentTheme)

  useEffect(() => subscribeToSystem(setTheme), [])

  function handleToggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    applyTheme(next)
    saveChoice(next)
    setTheme(next)
  }

  const isDark = theme === 'dark'
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={handleToggle}
      aria-label={isDark ? strings.themeToLight : strings.themeToDark}
    >
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
        {isDark ? (
          <path
            fill="currentColor"
            d="M12 4.5a1 1 0 0 1 1 1V7a1 1 0 1 1-2 0V5.5a1 1 0 0 1 1-1Zm0 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm8-4.5a1 1 0 0 1-1 1h-1.5a1 1 0 1 1 0-2H19a1 1 0 0 1 1 1ZM6.5 12a1 1 0 0 1-1 1H4a1 1 0 1 1 0-2h1.5a1 1 0 0 1 1 1Zm9.4 4.9a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0ZM8.5 6.5a1 1 0 0 1-1.4 0l-1-1A1 1 0 1 1 7.5 4.1l1 1a1 1 0 0 1 0 1.4Zm9.9-1.4a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0ZM8.5 17.5a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0ZM12 19a1 1 0 0 1 1 1v1.5a1 1 0 1 1-2 0V20a1 1 0 0 1 1-1Z"
          />
        ) : (
          <path
            fill="currentColor"
            d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"
          />
        )}
      </svg>
    </button>
  )
}
