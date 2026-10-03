import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { InputScreen } from '../components/InputScreen.jsx'
import { strings } from '../strings.js'

describe('App shell', () => {
  it('shows the AI-not-a-fatwa notice on every render', () => {
    render(<App />)
    expect(screen.getByRole('note')).toHaveTextContent(strings.aiNotice)
  })

  it('shows the privacy notice before the text submit button', () => {
    render(<App />)
    const privacy = screen.getByRole('region', { name: strings.privacyHeading })
    const submit = screen.getByRole('button', { name: strings.textSubmit })
    expect(privacy.compareDocumentPosition(submit) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    for (const line of strings.privacyLines) {
      expect(within(privacy).getByText(line)).toBeInTheDocument()
    }
  })
})

describe('text input', () => {
  it('keeps submit disabled while the text is blank', async () => {
    const user = userEvent.setup()
    render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    const submit = screen.getByRole('button', { name: strings.textSubmit })
    expect(submit).toBeDisabled()
    await user.type(screen.getByLabelText(strings.textLabel), '   ')
    expect(submit).toBeDisabled()
    expect(screen.getByText(strings.textEmptyHint)).toBeInTheDocument()
  })

  it('submits the trimmed text', async () => {
    const user = userEvent.setup()
    const onSubmitText = vi.fn()
    render(<InputScreen onSubmitText={onSubmitText} onSubmitMedia={vi.fn()} />)
    await user.type(screen.getByLabelText(strings.textLabel), '  نص تجريبي  ')
    await user.click(screen.getByRole('button', { name: strings.textSubmit }))
    expect(onSubmitText).toHaveBeenCalledWith('نص تجريبي')
  })
})

describe('upload consent gate (G22)', () => {
  function makeFile() {
    return new File(['audio'], 'clip.mp3', { type: 'audio/mpeg' })
  }

  it('renders the consent checkbox with the exact Arabic label, unticked', () => {
    render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    const checkbox = screen.getByRole('checkbox', { name: strings.consent })
    expect(checkbox).not.toBeChecked()
  })

  it('keeps upload disabled until both a file is chosen and consent is ticked', async () => {
    const user = userEvent.setup()
    const onSubmitMedia = vi.fn()
    render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={onSubmitMedia} />)
    const upload = screen.getByRole('button', { name: strings.uploadSubmit })
    const file = makeFile()

    expect(upload).toBeDisabled()
    expect(screen.getByText(strings.uploadNoFileHint)).toBeInTheDocument()

    await user.upload(screen.getByLabelText(strings.uploadChooseFile), file)
    expect(upload).toBeDisabled()
    expect(screen.getByText(strings.uploadNoConsentHint)).toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: strings.consent }))
    expect(upload).toBeEnabled()

    await user.click(upload)
    expect(onSubmitMedia).toHaveBeenCalledWith(file)
  })

  it('stays disabled when consent is ticked but no file is chosen', async () => {
    const user = userEvent.setup()
    render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    await user.click(screen.getByRole('checkbox', { name: strings.consent }))
    expect(screen.getByRole('button', { name: strings.uploadSubmit })).toBeDisabled()
  })
})
