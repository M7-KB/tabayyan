import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import App from '../App.jsx'
import { features } from '../config/features.js'
import { MAX_MEDIA_BYTES } from '../api/transcribe.js'
import { strings } from '../strings.js'

function clipFile(size = 1024) {
  const file = new File(['audio'], 'clip.mp3', { type: 'audio/mpeg' })
  if (size !== file.size) Object.defineProperty(file, 'size', { value: size })
  return file
}

async function uploadClip(user, file) {
  await user.upload(screen.getByLabelText(strings.uploadChooseFile), file)
  await user.click(screen.getByRole('checkbox', { name: strings.consent }))
  await user.click(screen.getByRole('button', { name: strings.uploadSubmit }))
}

// The audio flow sits behind features.mediaUpload. Each case turns it on and restores it after.
describe('audio flow (features.mediaUpload on)', () => {
  beforeEach(() => {
    features.mediaUpload = true
  })

  afterEach(() => {
    features.mediaUpload = false
  })

  it('shows the transcript for review, labelled as sample text, and nothing else yet', async () => {
    const user = userEvent.setup()
    render(<App />)
    await uploadClip(user, clipFile())

    expect(await screen.findByRole('heading', { name: strings.transcriptHeading })).toHaveFocus()
    expect(screen.getByLabelText(strings.transcriptLabel)).toHaveValue(strings.transcriptStubText)
    expect(screen.getByText(strings.transcriptStubNote)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: strings.transcriptConfirm })).toBeEnabled()
    expect(screen.queryByLabelText(strings.textLabel)).not.toBeInTheDocument()
  })

  it('lets the user edit the transcript and blocks confirmation while it is empty', async () => {
    const user = userEvent.setup()
    render(<App />)
    await uploadClip(user, clipFile())

    const transcript = await screen.findByLabelText(strings.transcriptLabel)
    await user.clear(transcript)
    expect(screen.getByRole('button', { name: strings.transcriptConfirm })).toBeDisabled()
    expect(screen.getByText(strings.transcriptEmpty)).toBeInTheDocument()

    await user.type(transcript, 'نص معدّل')
    expect(screen.getByRole('button', { name: strings.transcriptConfirm })).toBeEnabled()
  })

  it('returns to the input screen when the user cancels the review', async () => {
    const user = userEvent.setup()
    render(<App />)
    await uploadClip(user, clipFile())

    await user.click(await screen.findByRole('button', { name: strings.transcriptDiscard }))
    expect(screen.getByLabelText(strings.textLabel)).toBeInTheDocument()
    expect(screen.queryByLabelText(strings.transcriptLabel)).not.toBeInTheDocument()
  })

  it('refuses a clip over the size limit with a next step, before any transcription', async () => {
    const user = userEvent.setup()
    render(<App />)
    await uploadClip(user, clipFile(MAX_MEDIA_BYTES + 1))

    expect(await screen.findByRole('alert')).toHaveTextContent(strings.transcribeErrors.MEDIA_TOO_LARGE)
    expect(screen.queryByLabelText(strings.transcriptLabel)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: strings.mediaErrorBack }))
    expect(screen.getByLabelText(strings.textLabel)).toBeInTheDocument()
  })

  it('states on the privacy row that clips are sent to the provider and not stored', () => {
    render(<App />)
    expect(screen.getByText(strings.privacySummaryMedia)).toBeInTheDocument()
  })
})

describe('audio flow off (default)', () => {
  it('keeps the text-only privacy line when the flag is off', () => {
    render(<App />)
    expect(screen.getByText(strings.privacySummary)).toBeInTheDocument()
    expect(screen.queryByText(strings.privacySummaryMedia)).not.toBeInTheDocument()
  })
})
