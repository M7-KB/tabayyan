import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Results } from '../components/Results.jsx'
import { strings } from '../strings.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'
import cannotConfirm from '../../../contracts/fixtures/cannot-confirm.json'

describe('Results', () => {
  it('shows a status message while loading', () => {
    render(<Results status="loading" />)
    expect(screen.getByRole('status')).toHaveTextContent(strings.resultsLoading)
  })

  it('shows the message for the server error code with retry and edit actions', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    const onEdit = vi.fn()
    render(<Results status="error" errorCode="PIPELINE_DEGRADED" onRetry={onRetry} onEdit={onEdit} />)

    expect(screen.getByRole('alert')).toHaveTextContent(strings.checkErrors.PIPELINE_DEGRADED)
    await user.click(screen.getByRole('button', { name: strings.resultsRetry }))
    await user.click(screen.getByRole('button', { name: strings.resultsEditText }))
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onEdit).toHaveBeenCalledTimes(1)
  })

  it('falls back to the generic message for an unknown error code', () => {
    render(<Results status="error" errorCode="SOMETHING_NEW" onRetry={vi.fn()} onEdit={vi.fn()} />)
    expect(screen.getByRole('alert')).toHaveTextContent(strings.checkErrors.UNKNOWN)
  })

  it('shows the empty state with an edit action when the service returns no cards', () => {
    render(<Results status="done" cards={[]} onRetry={vi.fn()} onEdit={vi.fn()} />)
    expect(screen.getByText(strings.resultsEmpty)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: strings.resultsEditText })).toBeInTheDocument()
  })

  it('renders one card per claim, each with its own state label', () => {
    render(<Results status="done" cards={[supportedConfirms, cannotConfirm]} />)
    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(screen.getByRole('article', { name: strings.stateLabels.supported_confirms })).toBeInTheDocument()
    expect(screen.getByRole('article', { name: strings.stateLabels.cannot_confirm })).toBeInTheDocument()
  })
})
