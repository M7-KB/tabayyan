import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { strings } from '../strings.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'
import cannotConfirm from '../../../contracts/fixtures/cannot-confirm.json'

// The text path end to end (SPEC.md §6.2): submit, extract, confirm or edit claims, check, cards.
// fetch is stubbed per endpoint, so each test controls exactly what the API answers.

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

// One card per confirmed claim id, as the server answers when every claim is checked.
function cardsFor(ids) {
  return ids.map((id) => ({ ...structuredClone(supportedConfirms), claim: { ...supportedConfirms.claim, id } }))
}

function claim(id, text) {
  return { id, text_ar: text, span: { start: 0, end: text.length }, origin: 'stated', level: 'B' }
}

const extraction = {
  detected_lang: 'ar',
  input_kind: 'claim',
  claims: [claim('c1', 'الادعاء الأول'), claim('c2', 'الادعاء الثاني')],
  dropped_count: 0,
  no_checkable_claim: false,
}

function stubApi(handlers) {
  const fetchMock = vi.fn(async (url, init) => {
    if (url.endsWith('/health')) return handlers.health?.() ?? jsonResponse(200, { status: 'degraded' })
    if (url.endsWith('/api/v1/extract')) return handlers.extract(init)
    if (url.endsWith('/api/v1/check')) return handlers.check(init)
    throw new Error(`unexpected request to ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function submitText(user, text = 'نص يحتوي ادعاءين') {
  await user.type(screen.getByLabelText(strings.textLabel), text)
  await user.click(screen.getByRole('button', { name: strings.textSubmit }))
}

describe('text path: extract, confirm, check', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the extracted claims as editable text before any check runs', async () => {
    const user = userEvent.setup()
    const fetchMock = stubApi({ extract: () => jsonResponse(200, extraction), check: vi.fn() })
    render(<App />)

    await submitText(user)

    expect(await screen.findByLabelText(`${strings.claimLabel} 1`)).toHaveValue('الادعاء الأول')
    expect(screen.getByLabelText(`${strings.claimLabel} 2`)).toHaveValue('الادعاء الثاني')
    expect(screen.getByRole('heading', { name: strings.claimsHeading })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/api/v1/check'))).toBe(false)
  })

  it('checks only the confirmed claims, with the user edits and without the emptied one', async () => {
    const user = userEvent.setup()
    const checkBodies = []
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: (init) => {
        checkBodies.push(JSON.parse(init.body))
        return jsonResponse(200, { cards: cardsFor(['c1']) })
      },
    })
    render(<App />)
    await submitText(user)

    const first = await screen.findByLabelText(`${strings.claimLabel} 1`)
    await user.clear(first)
    await user.type(first, 'ادعاء معدّل')
    await user.clear(screen.getByLabelText(`${strings.claimLabel} 2`))
    await user.click(screen.getByRole('button', { name: strings.claimsConfirm }))

    await waitFor(() => expect(checkBodies).toHaveLength(1))
    expect(checkBodies[0].claims).toEqual([{ id: 'c1', text_ar: 'ادعاء معدّل', level: 'B' }])
    expect(checkBodies[0].input_kind).toBe('claim')
    expect(checkBodies[0].locale).toBe('ar')
  })

  it('renders one card per claim and keeps the AI-not-a-fatwa notice on the result view', async () => {
    const user = userEvent.setup()
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: () =>
        jsonResponse(200, {
          cards: [...cardsFor(['c1']), { ...cannotConfirm, claim: { ...cannotConfirm.claim, id: 'c2' } }],
        }),
    })
    render(<App />)
    await submitText(user)
    await user.click(await screen.findByRole('button', { name: strings.claimsConfirm }))

    expect(await screen.findAllByRole('article')).toHaveLength(2)
    expect(screen.getByRole('note')).toHaveTextContent(strings.aiNotice)
  })

  it('shows the claims again with the edited text after the user goes back from results', async () => {
    const user = userEvent.setup()
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: () => jsonResponse(200, { cards: cardsFor(['c1', 'c2']) }),
    })
    render(<App />)
    await submitText(user)
    const first = await screen.findByLabelText(`${strings.claimLabel} 1`)
    await user.clear(first)
    await user.type(first, 'ادعاء معدّل')
    await user.click(screen.getByRole('button', { name: strings.claimsConfirm }))
    await screen.findAllByRole('article')

    await user.click(screen.getByRole('button', { name: strings.resultsEditClaims }))

    expect(screen.getByLabelText(`${strings.claimLabel} 1`)).toHaveValue('ادعاء معدّل')
  })

  it('keeps confirm disabled until at least one claim has text', async () => {
    const user = userEvent.setup()
    stubApi({ extract: () => jsonResponse(200, extraction), check: vi.fn() })
    render(<App />)
    await submitText(user)

    await user.clear(await screen.findByLabelText(`${strings.claimLabel} 1`))
    await user.clear(screen.getByLabelText(`${strings.claimLabel} 2`))

    expect(screen.getByRole('button', { name: strings.claimsConfirm })).toBeDisabled()
    expect(screen.getByText(strings.claimsNoneLeft)).toBeInTheDocument()
  })

  it('shows the empty state with a way back when extraction finds no claims', async () => {
    const user = userEvent.setup()
    stubApi({ extract: () => jsonResponse(200, { ...extraction, claims: [] }), check: vi.fn() })
    render(<App />)
    await submitText(user)

    expect(await screen.findByText(strings.claimsEmpty)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: strings.claimsBack }))
    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('نص يحتوي ادعاءين')
  })

  it('shows PIPELINE_DEGRADED during extraction with retry, and retry succeeds', async () => {
    const user = userEvent.setup()
    let attempts = 0
    stubApi({
      extract: () => {
        attempts += 1
        return attempts === 1
          ? jsonResponse(503, { error: { code: 'PIPELINE_DEGRADED' } })
          : jsonResponse(200, extraction)
      },
      check: vi.fn(),
    })
    render(<App />)
    await submitText(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.PIPELINE_DEGRADED)
    await user.click(screen.getByRole('button', { name: strings.extractRetry }))
    expect(await screen.findByLabelText(`${strings.claimLabel} 1`)).toBeInTheDocument()
  })

  it('shows PIPELINE_DEGRADED from check with retry and edit actions, never a partial result', async () => {
    const user = userEvent.setup()
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: () => jsonResponse(503, { error: { code: 'PIPELINE_DEGRADED' } }),
    })
    render(<App />)
    await submitText(user)
    await user.click(await screen.findByRole('button', { name: strings.claimsConfirm }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(strings.checkErrors.PIPELINE_DEGRADED)
    expect(screen.queryAllByRole('article')).toHaveLength(0)
    expect(within(alert.parentElement).getByRole('button', { name: strings.resultsRetry })).toBeInTheDocument()
    expect(within(alert.parentElement).getByRole('button', { name: strings.resultsEditText })).toBeInTheDocument()
  })

  it('shows the network message when the request cannot reach the API', async () => {
    const user = userEvent.setup()
    stubApi({
      extract: () => {
        throw new TypeError('Failed to fetch')
      },
      check: vi.fn(),
    })
    render(<App />)
    await submitText(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.NETWORK)
  })
})

describe('preview banner', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('hides once /health answers', async () => {
    stubApi({ extract: vi.fn(), check: vi.fn() })
    render(<App />)
    await waitFor(() => expect(screen.queryByText(strings.previewBanner)).not.toBeInTheDocument())
  })

  it('stays up while /health fails', async () => {
    const fetchMock = stubApi({ health: () => jsonResponse(503, {}), extract: vi.fn(), check: vi.fn() })
    render(<App />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(screen.getByText(strings.previewBanner)).toBeInTheDocument()
  })
})
