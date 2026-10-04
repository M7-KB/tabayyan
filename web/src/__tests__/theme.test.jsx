import { act, render, screen, fireEvent } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeToggle } from '../components/ThemeToggle.jsx'
import { STORAGE_KEY, currentTheme, resetPageChoice } from '../theme.js'
import { strings } from '../strings.js'

// Fake matchMedia for the system setting. `dark` decides what '(prefers-color-scheme: dark)' reports.
function mockSystemDark(dark) {
  const listeners = new Set()
  const query = {
    matches: dark,
    addEventListener: (_type, fn) => listeners.add(fn),
    removeEventListener: (_type, fn) => listeners.delete(fn),
  }
  window.matchMedia = vi.fn(() => query)
  return {
    change(next) {
      query.matches = next
      listeners.forEach((fn) => fn({ matches: next }))
    },
  }
}

beforeEach(() => {
  window.localStorage.clear()
  resetPageChoice()
  delete document.documentElement.dataset.theme
})

afterEach(() => {
  vi.restoreAllMocks()
  delete document.documentElement.dataset.theme
})

describe('theme choice', () => {
  it('follows the system setting when nothing is saved', () => {
    mockSystemDark(true)
    expect(currentTheme()).toBe('dark')
    mockSystemDark(false)
    expect(currentTheme()).toBe('light')
  })

  it('uses a saved choice over the system setting', () => {
    mockSystemDark(true)
    window.localStorage.setItem(STORAGE_KEY, 'light')
    expect(currentTheme()).toBe('light')
  })

  it('ignores an unknown saved value', () => {
    mockSystemDark(false)
    window.localStorage.setItem(STORAGE_KEY, 'sepia')
    expect(currentTheme()).toBe('light')
  })
})

describe('ThemeToggle', () => {
  it('starts from the system setting and names the action it performs', () => {
    mockSystemDark(false)
    render(<ThemeToggle />)
    expect(screen.getByRole('button', { name: strings.themeToDark })).toBeInTheDocument()
  })

  it('switches the page theme and saves the choice in localStorage only', () => {
    mockSystemDark(false)
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: strings.themeToDark }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('dark')
    expect(screen.getByRole('button', { name: strings.themeToLight })).toBeInTheDocument()
  })

  it('follows a system change while no choice is saved', () => {
    const system = mockSystemDark(false)
    render(<ThemeToggle />)
    act(() => system.change(true))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('ignores a system change once the user has chosen', () => {
    const system = mockSystemDark(false)
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: strings.themeToDark }))
    act(() => system.change(false))
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('keeps the explicit choice when storage is blocked and the system changes', () => {
    const system = mockSystemDark(false)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage blocked')
    })
    render(<ThemeToggle />)
    fireEvent.click(screen.getByRole('button', { name: strings.themeToDark }))
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull()
    act(() => system.change(true))
    act(() => system.change(false))
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(screen.getByRole('button', { name: strings.themeToLight })).toBeInTheDocument()
  })
})
