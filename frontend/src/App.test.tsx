import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
} from 'vitest'
import App from './App'

/**
 * Absolute URLs are required because MSW (Node) intercepts at the fetch level
 * and the component-side fetch resolves against `jsdom.url` from
 * `vitest.config.ts`. Centralized here so a future url change is one edit.
 */
const ORIGIN = 'http://localhost:5173'
const CONFIG_URL = `${ORIGIN}/api/config`
const RUN_URL = `${ORIGIN}/api/simulation/run`

const sampleYaml = 'age: 30\ntrial_quantity: 2\n'

const server = setupServer()

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

beforeEach(() => {
  /**
   * Default GET handler so most tests don't have to redeclare it. Tests that
   * need a different load response override with `server.use(...)`; later
   * registrations take precedence in MSW.
   */
  server.use(
    http.get(CONFIG_URL, () => HttpResponse.json({ content: sampleYaml })),
  )
})

afterEach(() => {
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})

/** Wait for the editor to render the loaded YAML, signalling load completion. */
async function waitForLoadedEditor(): Promise<HTMLElement> {
  const textarea = await screen.findByRole('textbox', {
    name: /configuration \(yaml\)/i,
  })
  await waitFor(() => {
    expect(textarea).toHaveValue(sampleYaml)
  })
  return textarea
}

describe('App config flow — load', () => {
  it('loads configuration into the editor and shows loaded status', async () => {
    render(<App />)

    await waitForLoadedEditor()
    expect(await screen.findByText(/configuration loaded/i)).toBeInTheDocument()
  })

  it('shows an empty editor only after the blank config has loaded', async () => {
    server.use(
      http.get(CONFIG_URL, () => HttpResponse.json({ content: '' })),
    )

    render(<App />)

    /**
     * The textarea starts empty regardless of API response, so we must wait
     * for the load-status message before asserting on the value, otherwise
     * the test would pass even if the load never completed.
     */
    expect(await screen.findByText(/configuration loaded/i)).toBeInTheDocument()
    expect(
      screen.getByRole('textbox', { name: /configuration \(yaml\)/i }),
    ).toHaveValue('')
  })

  it('surfaces HTTP errors from the load API', async () => {
    server.use(
      http.get(CONFIG_URL, () =>
        HttpResponse.json(
          { error: { message: 'Server exploded' } },
          { status: 500 },
        ),
      ),
    )

    render(<App />)

    expect(await screen.findByText(/server exploded/i)).toBeInTheDocument()
  })

  it('surfaces network errors from the load API', async () => {
    server.use(http.get(CONFIG_URL, () => HttpResponse.error()))

    render(<App />)

    /**
     * `HttpResponse.error()` causes `fetch` to reject; the component's catch
     * block surfaces the resulting `Error.message` (e.g. "Failed to fetch"
     * in jsdom). We match flexibly to avoid coupling to the exact runtime.
     */
    const loadStatus = document.getElementById('load-status')
    expect(loadStatus).not.toBeNull()
    await waitFor(() => {
      expect(loadStatus).toHaveTextContent(/fail|fetch|network/i)
      expect(loadStatus).toHaveClass('status-error')
    })
  })
})

describe('App config flow — save', () => {
  it('saves the loaded configuration content via PUT', async () => {
    let savedBody: { content: string } | undefined
    server.use(
      http.put(CONFIG_URL, async ({ request }) => {
        savedBody = (await request.json()) as { content: string }
        return HttpResponse.json({ ok: true, message: 'saved' })
      }),
    )

    render(<App />)
    const user = userEvent.setup()

    await waitForLoadedEditor()
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    expect(await screen.findByText(/configuration saved/i)).toBeInTheDocument()
    expect(savedBody?.content).toBe(sampleYaml)
  })

  it('saves the textarea content as edited by the user', async () => {
    let savedBody: { content: string } | undefined
    server.use(
      http.put(CONFIG_URL, async ({ request }) => {
        savedBody = (await request.json()) as { content: string }
        return HttpResponse.json({ ok: true })
      }),
    )

    render(<App />)
    const user = userEvent.setup()

    const textarea = await waitForLoadedEditor()
    await user.clear(textarea)
    await user.type(textarea, 'age: 31{Enter}trial_quantity: 5{Enter}')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    await screen.findByText(/configuration saved/i)
    expect(savedBody?.content).toBe('age: 31\ntrial_quantity: 5\n')
  })

  it('surfaces save errors in the save-status region', async () => {
    server.use(
      http.put(CONFIG_URL, () =>
        HttpResponse.json(
          { error: { message: 'bad yaml' } },
          { status: 400 },
        ),
      ),
    )

    render(<App />)
    const user = userEvent.setup()

    await waitForLoadedEditor()
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    /**
     * Both load-status and save-status carry `role="status"`, so we anchor on
     * the save-status element by id and assert on its textContent + variant
     * class instead of using a global text query that could match either.
     */
    const saveStatus = document.getElementById('save-status')
    expect(saveStatus).not.toBeNull()
    await waitFor(() => {
      expect(saveStatus).toHaveTextContent(/bad yaml/i)
      expect(saveStatus).toHaveClass('status-error')
    })
  })
})

describe('App save and run', () => {
  it('calls PUT then POST and renders simulation results', async () => {
    const calls: string[] = []
    server.use(
      http.put(CONFIG_URL, async () => {
        calls.push('PUT')
        return HttpResponse.json({ ok: true })
      }),
      http.post(RUN_URL, async () => {
        calls.push('POST')
        return HttpResponse.json({
          success_percentage: '55.5',
          first_result: {
            columns: ['a', 'b'],
            data: [
              [1, 'x'],
              [2, 'y'],
            ],
          },
        })
      }),
    )

    render(<App />)
    const user = userEvent.setup()

    await waitForLoadedEditor()
    await user.click(screen.getByRole('button', { name: /save & run/i }))

    await waitFor(() => {
      expect(calls).toEqual(['PUT', 'POST'])
    })

    expect(await screen.findByText(/55\.5%/)).toBeInTheDocument()

    const table = screen.getByRole('table')
    expect(within(table).getByRole('columnheader', { name: 'a' })).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'b' })).toBeInTheDocument()
    expect(within(table).getByRole('cell', { name: 'x' })).toBeInTheDocument()
    expect(within(table).getByRole('cell', { name: 'y' })).toBeInTheDocument()
  })

  it('exposes only Save and Save & run controls (no separate Run button)', async () => {
    render(<App />)

    await waitForLoadedEditor()

    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /save & run/i }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /^run$/i }),
    ).not.toBeInTheDocument()
  })

  it('does not POST when PUT fails', async () => {
    let postCount = 0
    server.use(
      http.put(CONFIG_URL, () =>
        HttpResponse.json({ error: { message: 'invalid' } }, { status: 400 }),
      ),
      http.post(RUN_URL, () => {
        postCount += 1
        return HttpResponse.json({
          success_percentage: '0',
          first_result: { columns: [], data: [] },
        })
      }),
    )

    render(<App />)
    const user = userEvent.setup()

    await waitForLoadedEditor()
    await user.click(screen.getByRole('button', { name: /save & run/i }))

    expect(await screen.findByText(/invalid/i)).toBeInTheDocument()
    expect(postCount).toBe(0)
  })

  it('disables the Save & run button while save+run is in flight', async () => {
    /**
     * Use deferred promises rather than real `setTimeout` so this test is
     * deterministic and instant regardless of host scheduler latency.
     */
    let resolvePut: (() => void) | undefined
    let resolveRun: (() => void) | undefined
    const putReady = new Promise<void>((resolve) => {
      resolvePut = resolve
    })
    const runReady = new Promise<void>((resolve) => {
      resolveRun = resolve
    })

    server.use(
      http.put(CONFIG_URL, async () => {
        await putReady
        return HttpResponse.json({ ok: true })
      }),
      http.post(RUN_URL, async () => {
        await runReady
        return HttpResponse.json({
          success_percentage: '10',
          first_result: { columns: ['c'], data: [[0]] },
        })
      }),
    )

    render(<App />)
    const user = userEvent.setup()

    await waitForLoadedEditor()
    const runButton = screen.getByRole('button', { name: /save & run/i })
    await user.click(runButton)

    expect(runButton).toBeDisabled()

    resolvePut?.()
    resolveRun?.()

    await waitFor(() => {
      expect(runButton).not.toBeDisabled()
    })
  })

  it('shows placeholder before first simulation run', async () => {
    render(<App />)

    expect(
      await screen.findByText(/run a simulation to see results/i),
    ).toBeInTheDocument()
  })
})
