import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { CHECK_DEADLINE_MS, EXTRACT_DEADLINE_MS } from '../config/api.js'
import { strings } from '../strings.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'

// Client deadline, cancel and late-response behaviour for the extract and check requests.
// Requests are controlled: a hung request only fails when the client aborts it (as fetch does), and a
// deferred request answers only when the test says so.

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
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

function cardsFor(ids) {
  return ids.map((id) => ({ ...structuredClone(supportedConfirms), claim: { ...supportedConfirms.claim, id } }))
}

function hangUntilAborted(init) {
  return new Promise((_, reject) => {
    init.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')))
  })
}

function deferred() {
  let resolve
  const promise = new Promise((done) => {
    resolve = done
  })
  return { promise, resolve }
}

function stubApi({ extract, check }) {
  const fetchMock = vi.fn(async (url, init) => {
    if (url.endsWith('/health')) return jsonResponse(200, { status: 'ok' })
    if (url.endsWith('/api/v1/extract')) return extract(init)
    if (url.endsWith('/api/v1/check')) return check(init)
    throw new Error(`unexpected request to ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function submitText(user, text = 'نص يحتوي ادعاءين') {
  await user.type(screen.getByLabelText(strings.textLabel), text)
  await user.click(screen.getByRole('button', { name: strings.textSubmit }))
}

describe('client deadlines, cancel and late responses', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  function setup() {
    return userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
  }

  it('keeps extraction waiting until the deadline, then shows the timeout with the input kept', async () => {
    const user = setup()
    stubApi({ extract: hangUntilAborted, check: vi.fn() })
    render(<App />)
    await submitText(user, 'نص الاختبار')
    expect(await screen.findByText(strings.extracting)).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(EXTRACT_DEADLINE_MS - 1)
    })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.TIMEOUT)

    await user.click(screen.getByRole('button', { name: strings.claimsBack }))
    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('نص الاختبار')
  })

  it('cancelling extraction returns to the input with the text kept', async () => {
    const user = setup()
    stubApi({ extract: hangUntilAborted, check: vi.fn() })
    render(<App />)
    await submitText(user, 'نص الاختبار')

    await user.click(await screen.findByRole('button', { name: strings.extractCancel }))

    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('نص الاختبار')
    expect(screen.queryByText(strings.extracting)).not.toBeInTheDocument()
  })

  it('drops a late extraction answer after cancel and keeps the newer attempt', async () => {
    const user = setup()
    const late = deferred()
    let attempts = 0
    stubApi({
      extract: () => {
        attempts += 1
        if (attempts === 1) return late.promise.then(() => jsonResponse(200, extraction))
        return jsonResponse(200, { ...extraction, claims: [claim('c1', 'ادعاء جديد')] })
      },
      check: vi.fn(),
    })
    render(<App />)
    await submitText(user, 'نص أول')

    await user.click(await screen.findByRole('button', { name: strings.extractCancel }))
    await user.click(screen.getByRole('button', { name: strings.textSubmit }))
    expect(await screen.findByLabelText(`${strings.claimLabel} 1`)).toHaveValue('ادعاء جديد')

    await act(async () => {
      late.resolve()
    })

    expect(screen.getByLabelText(`${strings.claimLabel} 1`)).toHaveValue('ادعاء جديد')
    expect(screen.queryByLabelText(`${strings.claimLabel} 2`)).not.toBeInTheDocument()
  })

  it('keeps the edited claims while a check is pending, and cancel returns to them', async () => {
    const user = setup()
    const checks = []
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: (init) => {
        checks.push(init)
        return hangUntilAborted(init)
      },
    })
    render(<App />)
    await submitText(user)
    const first = await screen.findByLabelText(`${strings.claimLabel} 1`)
    await user.clear(first)
    await user.type(first, 'ادعاء معدّل')
    await user.click(screen.getByRole('button', { name: strings.claimsConfirm }))
    expect(await screen.findByText(strings.resultsLoading)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: strings.resultsCancel }))

    expect(screen.getByLabelText(`${strings.claimLabel} 1`)).toHaveValue('ادعاء معدّل')
    expect(checks[0].signal.aborted).toBe(true)
  })

  it('drops a late check answer after cancel instead of showing results', async () => {
    const user = setup()
    const late = deferred()
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: () => late.promise.then(() => jsonResponse(200, { cards: cardsFor(['c1', 'c2']) })),
    })
    render(<App />)
    await submitText(user)
    await user.click(await screen.findByRole('button', { name: strings.claimsConfirm }))
    await user.click(await screen.findByRole('button', { name: strings.resultsCancel }))

    await act(async () => {
      late.resolve()
    })

    expect(screen.queryAllByRole('article')).toHaveLength(0)
    expect(screen.getByLabelText(`${strings.claimLabel} 1`)).toHaveValue('الادعاء الأول')
  })

  it('shows the timeout for a check past its deadline, with edit and retry, and keeps the edits', async () => {
    const user = setup()
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: hangUntilAborted,
    })
    render(<App />)
    await submitText(user)
    const first = await screen.findByLabelText(`${strings.claimLabel} 1`)
    await user.clear(first)
    await user.type(first, 'ادعاء معدّل')
    await user.click(screen.getByRole('button', { name: strings.claimsConfirm }))
    expect(await screen.findByText(strings.resultsLoading)).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(CHECK_DEADLINE_MS)
    })

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(strings.checkErrors.TIMEOUT)
    expect(screen.queryAllByRole('article')).toHaveLength(0)
    expect(screen.getByRole('button', { name: strings.resultsRetry })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: strings.resultsEditText }))
    expect(screen.getByLabelText(`${strings.claimLabel} 1`)).toHaveValue('ادعاء معدّل')
  })

  it('shows no partial result when a check answer leaves a confirmed claim out', async () => {
    const user = setup()
    stubApi({
      extract: () => jsonResponse(200, extraction),
      check: () => jsonResponse(200, { cards: cardsFor(['c1']) }),
    })
    render(<App />)
    await submitText(user)
    await user.click(await screen.findByRole('button', { name: strings.claimsConfirm }))

    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.PIPELINE_DEGRADED)
    expect(screen.queryAllByRole('article')).toHaveLength(0)
  })
})
