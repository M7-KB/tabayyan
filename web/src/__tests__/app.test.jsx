import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { InputScreen } from '../components/InputScreen.jsx'
import { features } from '../config/features.js'
import { strings } from '../strings.js'

describe('App shell', () => {
  it('shows the AI-not-a-fatwa notice on every render', () => {
    render(<App />)
    expect(screen.getByRole('note')).toHaveTextContent(strings.aiNotice)
  })

  it('shows the development-preview banner', () => {
    render(<App />)
    expect(screen.getByText(strings.previewBanner)).toBeInTheDocument()
  })

  it('shows the privacy row under the composer with its short line visible', () => {
    render(<App />)
    const submit = screen.getByRole('button', { name: strings.textSubmit })
    const privacy = screen.getByText(strings.privacySummary).closest('details')
    expect(submit.compareDocumentPosition(privacy) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByText(strings.privacySummary)).toBeVisible()
  })

  it('keeps the full privacy lines in the collapsed row until it is opened', async () => {
    const user = userEvent.setup()
    render(<App />)
    const privacy = screen.getByText(strings.privacySummary).closest('details')
    const line = strings.privacyLines[2]
    expect(privacy.open).toBe(false)
    expect(within(privacy).getByText(line)).not.toBeVisible()

    await user.click(screen.getByText(strings.privacySummary))
    expect(privacy.open).toBe(true)
    for (const expanded of strings.privacyLines) {
      expect(within(privacy).getByText(expanded)).toBeVisible()
    }
  })

  it('shows the source line in the footer, not as a note', () => {
    render(<App />)
    expect(screen.getByText(strings.quoteSourceNote)).toBeInTheDocument()
    expect(screen.getAllByRole('note')).toHaveLength(1)
  })

  it('shows the tagline and the small and large app name', () => {
    render(<App />)
    expect(screen.getByText(strings.tagline)).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: strings.appName })).toBeInTheDocument()
  })
})

describe('composer', () => {
  it('uses the approved placeholder and a visibly labelled send button with an icon', () => {
    render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    expect(screen.getByPlaceholderText('اكتب الادعاء أو السؤال هنا…')).toBeInTheDocument()
    const send = screen.getByRole('button', { name: strings.textSubmit })
    expect(send).toHaveClass('send-button')
    expect(send).toHaveTextContent(strings.textSubmit)
    expect(send.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })

  it('has no microphone or attach control', () => {
    const { container } = render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    expect(container.querySelector('input[type="file"]')).toBeNull()
    expect(screen.queryByRole('button', { name: /ميكروفون|إرفاق|إضافة/ })).not.toBeInTheDocument()
  })

  it('shows no chip row while the approved example list is empty', () => {
    const { container } = render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    expect(container.querySelector('.example-chips')).toBeNull()
  })
})

describe('example chips', () => {
  const example = { label: 'مثال تجريبي', text: 'نص معتمد للتجربة' }

  // The approved list is empty and the flag is off in the build, so each case sets both and restores them.
  beforeEach(() => {
    strings.exampleChips.push(example)
    features.exampleChips = true
  })

  afterEach(() => {
    strings.exampleChips.length = 0
    features.exampleChips = false
  })

  it('renders no chips while the exampleChips flag is off, even with approved entries', () => {
    features.exampleChips = false
    const { container } = render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    expect(container.querySelector('.example-chips')).toBeNull()
  })

  it('fill the composer with the approved text, focus it, and do not submit', async () => {
    const user = userEvent.setup()
    const onSubmitText = vi.fn()
    render(<InputScreen onSubmitText={onSubmitText} onSubmitMedia={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: example.label }))
    const composer = screen.getByLabelText(strings.textLabel)
    expect(composer).toHaveValue(example.text)
    expect(composer).toHaveFocus()
    expect(onSubmitText).not.toHaveBeenCalled()
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

  it('submits the original text, untrimmed', async () => {
    const user = userEvent.setup()
    const onSubmitText = vi.fn()
    render(<InputScreen onSubmitText={onSubmitText} onSubmitMedia={vi.fn()} />)
    await user.type(screen.getByLabelText(strings.textLabel), '  نص تجريبي  ')
    await user.click(screen.getByRole('button', { name: strings.textSubmit }))
    expect(onSubmitText).toHaveBeenCalledWith('  نص تجريبي  ')
  })
})

describe('media upload is off in the text-first build', () => {
  it('renders no upload form, file input or consent checkbox by default', () => {
    const { container } = render(<InputScreen onSubmitText={vi.fn()} onSubmitMedia={vi.fn()} />)
    expect(container.querySelector('.upload-form')).toBeNull()
    expect(screen.queryByLabelText(strings.uploadChooseFile)).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox', { name: strings.consent })).not.toBeInTheDocument()
  })
})

describe('upload consent gate (G22)', () => {
  function makeFile() {
    return new File(['audio'], 'clip.mp3', { type: 'audio/mpeg' })
  }

  // The upload form is behind features.mediaUpload (off by default). These tests keep covering it.
  beforeEach(() => {
    features.mediaUpload = true
  })

  afterEach(() => {
    features.mediaUpload = false
  })

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
