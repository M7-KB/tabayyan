import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App.jsx'
import { CHECK_DEADLINE_MS } from '../config/api.js'
import { strings } from '../strings.js'
import supportedConfirms from '../../../contracts/fixtures/supported-confirms.json'

// The one-page flow (U1): input on top, results below, no claims page. /check gets the text as typed, once.
// Each card can be edited and re-checked in place. fetch is stubbed per endpoint, so each test controls the answer.

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

// One card per claim, with its own card_id so React keys stay unique.
function card(id, text = `نص ${id}`) {
  return {
    ...structuredClone(supportedConfirms),
    card_id: `card-${id}`,
    claim: { ...supportedConfirms.claim, id, text_original: text, text_ar: text },
  }
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

function stubApi({ health = () => jsonResponse(200, { status: 'ok' }), check }) {
  const fetchMock = vi.fn(async (url, init) => {
    if (url.endsWith('/health')) return health()
    if (url.endsWith('/api/v1/check')) return check(init)
    throw new Error(`unexpected request to ${url}`)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function checkCalls(fetchMock) {
  return fetchMock.mock.calls.filter(([url]) => url.endsWith('/api/v1/check'))
}

async function submitText(user, text = 'نص يحتوي ادعاءين') {
  await user.type(screen.getByLabelText(strings.textLabel), text)
  await user.click(screen.getByRole('button', { name: strings.textSubmit }))
}

describe('one-page flow: submit and results', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the text as typed to /check once, and never calls an extract step first', async () => {
    const user = userEvent.setup()
    const text = '  هل الإسلام انتشر بالسيف؟ '
    const fetchMock = stubApi({ check: () => jsonResponse(200, { cards: [card('c1')] }) })
    render(<App />)

    await submitText(user, text)

    expect(await screen.findByRole('article')).toBeInTheDocument()
    const calls = checkCalls(fetchMock)
    expect(calls).toHaveLength(1)
    expect(JSON.parse(calls[0][1].body)).toEqual({ original_text: text, locale: 'ar' })
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/api/v1/extract'))).toBe(false)
  })

  it('keeps the input on top and shows the results below it, with no claims page', async () => {
    const user = userEvent.setup()
    stubApi({ check: () => jsonResponse(200, { cards: [card('c1')] }) })
    render(<App />)

    await submitText(user)

    const input = screen.getByLabelText(strings.textLabel)
    const article = await screen.findByRole('article')
    expect(input.compareDocumentPosition(article) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.queryByText('الادعاءات المستخرجة')).not.toBeInTheDocument()
  })

  it('starts each card with how we understood the text, and keeps the user text in its own block', async () => {
    const user = userEvent.setup()
    stubApi({ check: () => jsonResponse(200, { cards: [card('c1', 'هل القرآن من تأليف محمد؟')] }) })
    render(<App />)

    await submitText(user)

    const article = await screen.findByRole('article')
    expect(within(article).getByRole('heading', { name: strings.understoodHeading })).toBeInTheDocument()
    const block = article.querySelector('[data-role="user-text"]')
    expect(within(block).getByText('هل القرآن من تأليف محمد؟')).toBeInTheDocument()
  })

  it('shows staged progress while checking, and cancel aborts it and keeps the input text', async () => {
    const user = userEvent.setup()
    const checks = []
    stubApi({
      check: (init) => {
        checks.push(init)
        return hangUntilAborted(init)
      },
    })
    render(<App />)

    await submitText(user, 'نص للتحقق')
    expect(await screen.findByText(strings.resultsLoading)).toBeInTheDocument()
    expect(screen.getByRole('list', { name: strings.checkStagesLabel })).toBeInTheDocument()
    expect(screen.getByText(strings.checkStagesNote)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: strings.checkCancel }))

    expect(checks[0].signal.aborted).toBe(true)
    expect(screen.queryByText(strings.resultsLoading)).not.toBeInTheDocument()
    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('نص للتحقق')
  })

  it('drops a late check answer after cancel instead of showing results', async () => {
    const user = userEvent.setup()
    const late = deferred()
    stubApi({ check: () => late.promise.then(() => jsonResponse(200, { cards: [card('c1')] })) })
    render(<App />)

    await submitText(user)
    await user.click(await screen.findByRole('button', { name: strings.checkCancel }))
    await act(async () => {
      late.resolve()
    })

    expect(screen.queryAllByRole('article')).toHaveLength(0)
  })

  it('shows the empty state with a way back to the input when the service returns no cards', async () => {
    const user = userEvent.setup()
    stubApi({ check: () => jsonResponse(200, { cards: [] }) })
    render(<App />)

    await submitText(user)

    expect(await screen.findByText(strings.resultsEmpty)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: strings.resultsEditText }))
    expect(screen.getByLabelText(strings.textLabel)).toHaveFocus()
  })

  it('shows PIPELINE_DEGRADED with retry, and retry sends the same text again', async () => {
    const user = userEvent.setup()
    const answers = [
      jsonResponse(503, { error: { code: 'PIPELINE_DEGRADED' } }),
      jsonResponse(200, { cards: [card('c1')] }),
    ]
    const fetchMock = stubApi({ check: () => answers.shift() })
    render(<App />)

    await submitText(user, 'نص للإعادة')
    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.PIPELINE_DEGRADED)
    expect(screen.queryAllByRole('article')).toHaveLength(0)

    await user.click(screen.getByRole('button', { name: strings.resultsRetry }))

    expect(await screen.findByRole('article')).toBeInTheDocument()
    const bodies = checkCalls(fetchMock).map(([, init]) => JSON.parse(init.body).original_text)
    expect(bodies).toEqual(['نص للإعادة', 'نص للإعادة'])
  })

  it('shows the network message when the request cannot reach the API', async () => {
    const user = userEvent.setup()
    stubApi({
      check: () => {
        throw new TypeError('Failed to fetch')
      },
    })
    render(<App />)

    await submitText(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.NETWORK)
  })
})

describe('one-page flow: edit and re-check a card in place', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function setupTwoCards(user, check) {
    const fetchMock = stubApi({
      check: (init) => {
        const body = JSON.parse(init.body)
        if (body.original_text === 'نص للتحقق') {
          return jsonResponse(200, { cards: [card('c1', 'الادعاء الأول'), card('c2', 'الادعاء الثاني')] })
        }
        return check(init)
      },
    })
    render(<App />)
    await submitText(user, 'نص للتحقق')
    await screen.findAllByRole('article')
    return fetchMock
  }

  it('opens the card editor with the understood text, and re-checks only that card with the edited text', async () => {
    const user = userEvent.setup()
    const fetchMock = await setupTwoCards(user, () =>
      jsonResponse(200, { cards: [card('c1b', 'الادعاء الأول المعدّل')] }),
    )
    const [first] = screen.getAllByRole('article')

    await user.click(within(first).getByRole('button', { name: strings.understoodEdit }))
    const editor = within(first).getByLabelText(strings.understoodEditLabel)
    expect(editor).toHaveValue('الادعاء الأول')
    await user.clear(editor)
    await user.type(editor, 'الادعاء الأول المعدّل')
    await user.click(within(first).getByRole('button', { name: strings.understoodRecheck }))

    expect(await screen.findByText('الادعاء الأول المعدّل')).toBeInTheDocument()
    const rechecks = checkCalls(fetchMock).slice(1)
    expect(rechecks).toHaveLength(1)
    expect(JSON.parse(rechecks[0][1].body)).toEqual({ original_text: 'الادعاء الأول المعدّل', locale: 'ar' })
    // The other card is untouched and the list stays two cards long.
    expect(screen.getAllByRole('article')).toHaveLength(2)
    expect(screen.getByText('الادعاء الثاني')).toBeInTheDocument()
  })

  it.each(['PIPELINE_DEGRADED', 'CHECK_INCOMPLETE'])('keeps the card and the draft when the re-check fails with %s', async (code) => {
    const user = userEvent.setup()
    await setupTwoCards(user, () => code === 'CHECK_INCOMPLETE'
      ? jsonResponse(200, { cards: [], retryable_results: [{ claim_id: 'pending', text_ar: 'نص تجريبي', code, retryable: true, message_ar: 'ignored' }] })
      : jsonResponse(503, { error: { code } }))
    const [first] = screen.getAllByRole('article')

    await user.click(within(first).getByRole('button', { name: strings.understoodEdit }))
    const editor = within(first).getByLabelText(strings.understoodEditLabel)
    await user.clear(editor)
    await user.type(editor, 'صياغة جديدة')
    await user.click(within(first).getByRole('button', { name: strings.understoodRecheck }))

    expect(await within(first).findByRole('alert')).toHaveTextContent(strings.checkErrors[code])
    expect(within(first).getByLabelText(strings.understoodEditLabel)).toHaveValue('صياغة جديدة')
    expect(screen.getByText('الادعاء الثاني')).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(2)
  })

  it('does not submit an empty edit', async () => {
    const user = userEvent.setup()
    const fetchMock = await setupTwoCards(user, () => jsonResponse(200, { cards: [] }))
    const [first] = screen.getAllByRole('article')

    await user.click(within(first).getByRole('button', { name: strings.understoodEdit }))
    await user.clear(within(first).getByLabelText(strings.understoodEditLabel))

    expect(within(first).getByRole('button', { name: strings.understoodRecheck })).toBeDisabled()
    expect(within(first).getByText(strings.understoodEmpty)).toBeInTheDocument()
    expect(checkCalls(fetchMock)).toHaveLength(1)
  })
})

describe('one-page flow: client deadline', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('shows the timeout past the deadline, keeps the input text, and offers retry', async () => {
    expect(CHECK_DEADLINE_MS).toBe(65_000)
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
    stubApi({ check: hangUntilAborted })
    render(<App />)

    await submitText(user, 'نص طويل')
    expect(await screen.findByText(strings.resultsLoading)).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(CHECK_DEADLINE_MS)
    })

    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.TIMEOUT)
    expect(screen.getByRole('button', { name: strings.resultsRetry })).toBeInTheDocument()
    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('نص طويل')
  })

  it.each(['failure', 'timeout', 'cancel'])('retains completed cards and open drafts through a partial retry: %s', async (outcome) => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
    const retry = deferred()
    let calls = 0
    stubApi({ check: () => ++calls === 1
      ? jsonResponse(200, { cards: [card('c1')], retryable_results: [
        { claim_id: 'c2', text_ar: 'نص تجريبي', code: 'CHECK_INCOMPLETE', retryable: true, message_ar: 'ignored' },
      ] })
      : retry.promise })
    render(<App />)
    await submitText(user, 'النص الأصلي')
    const completed = await screen.findByRole('article')
    await user.click(within(completed).getByRole('button', { name: strings.understoodEdit }))
    const editor = within(completed).getByLabelText(strings.understoodEditLabel)
    await user.clear(editor)
    await user.type(editor, 'صياغة جديدة')
    await user.click(screen.getByRole('button', { name: strings.resultsRetry }))
    expect(screen.getByRole('article')).toBe(completed)
    expect(editor).toHaveValue('صياغة جديدة')
    expect(screen.getByText('نص تجريبي')).toBeInTheDocument()

    if (outcome === 'failure') {
      await act(async () => retry.resolve(jsonResponse(503, { error: { code: 'CHECK_INCOMPLETE' } })))
    } else if (outcome === 'timeout') {
      await act(async () => { vi.advanceTimersByTime(CHECK_DEADLINE_MS) })
    } else {
      await user.click(screen.getByRole('button', { name: strings.checkCancel }))
    }
    expect(screen.getByRole('article')).toBe(completed)
    expect(screen.getByLabelText(strings.understoodEditLabel)).toBe(editor)
    expect(editor).toHaveValue('صياغة جديدة')
    expect(screen.getByRole('button', { name: strings.resultsRetry })).toBeInTheDocument()
    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('النص الأصلي')
    if (outcome !== 'failure') {
      await act(async () => retry.resolve(jsonResponse(200, { cards: [card('replacement')] })))
      expect(screen.getByRole('article')).toBe(completed)
      expect(editor).toHaveValue('صياغة جديدة')
    }
  })

  it('retries the original text after a partial response and keeps completed cards visible', async () => {
    const user = userEvent.setup()
    const answers = [
      jsonResponse(200, { cards: [card('c1')], retryable_results: [
        { claim_id: 'c2', text_ar: 'نص تجريبي', code: 'CHECK_INCOMPLETE', retryable: true, message_ar: 'ignored' },
      ] }),
      jsonResponse(200, { cards: [card('c1'), card('c2')] }),
    ]
    const fetchMock = stubApi({ check: () => answers.shift() })
    render(<App />)
    await submitText(user, 'النص الأصلي')
    expect(await screen.findByRole('status')).toHaveTextContent(strings.checkErrors.CHECK_INCOMPLETE)
    expect(screen.getAllByRole('article')).toHaveLength(1)
    await user.click(screen.getByRole('button', { name: strings.resultsRetry }))
    await waitFor(() => expect(screen.getAllByRole('article')).toHaveLength(2))
    expect(checkCalls(fetchMock).map(([, init]) => JSON.parse(init.body).original_text)).toEqual(['النص الأصلي', 'النص الأصلي'])
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('shows routing timeout as incomplete verification without an evidence card', async () => {
    const user = userEvent.setup()
    stubApi({ check: () => jsonResponse(503, { error: { code: 'CHECK_INCOMPLETE' } }) })
    render(<App />)
    await submitText(user, 'النص الأصلي')
    expect(await screen.findByRole('alert')).toHaveTextContent(strings.checkErrors.CHECK_INCOMPLETE)
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: strings.resultsRetry })).toBeInTheDocument()
  })

  it('ends loading at 40 seconds even if fetch ignores abort, and drops its late response', async () => {
    const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
    const late = deferred()
    stubApi({ check: () => late.promise.then(() => jsonResponse(200, { cards: [card('c1')] })) })
    render(<App />)
    await submitText(user, 'نص طويل')
    await act(async () => { vi.advanceTimersByTime(CHECK_DEADLINE_MS) })
    expect(screen.getByRole('alert')).toHaveTextContent('لم يكتمل التحقق، حاول مرة أخرى')
    await act(async () => { late.resolve() })
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
    expect(screen.getByLabelText(strings.textLabel)).toHaveValue('نص طويل')
  })
})

describe('preview banner', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('hides once /health answers', async () => {
    stubApi({ check: vi.fn() })
    render(<App />)
    await waitFor(() => expect(screen.queryByText(strings.previewBanner)).not.toBeInTheDocument())
  })

  it('stays up while /health fails', async () => {
    const fetchMock = stubApi({ health: () => jsonResponse(503, {}), check: vi.fn() })
    render(<App />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(screen.getByText(strings.previewBanner)).toBeInTheDocument()
  })
})
