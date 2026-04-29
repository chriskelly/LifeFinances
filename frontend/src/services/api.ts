import type {
  ConfigDocument,
  ConfigSaveResponse,
  ErrorBody,
  SimulationResult,
} from '../types/api'

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const data: unknown = await response.json()
  if (!response.ok) {
    const err = data as ErrorBody
    const message = err.error?.message ?? response.statusText
    throw new Error(message)
  }
  return data as T
}

/** Fetch active configuration text from ``GET /api/config``. */
export async function getConfig(): Promise<ConfigDocument> {
  const response = await fetch('/api/config')
  return parseJsonResponse<ConfigDocument>(response)
}

/** Persist configuration via ``PUT /api/config``. */
export async function putConfig(body: ConfigDocument): Promise<ConfigSaveResponse> {
  const response = await fetch('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJsonResponse<ConfigSaveResponse>(response)
}

/** Run simulation against on-disk config via ``POST /api/simulation/run``. */
export async function postSimulationRun(): Promise<SimulationResult> {
  const response = await fetch('/api/simulation/run', { method: 'POST' })
  return parseJsonResponse<SimulationResult>(response)
}

/** ``PUT /api/config`` with ``content``, then ``POST /api/simulation/run`` (aborts if PUT fails). */
export async function saveAndRun(content: string): Promise<SimulationResult> {
  await putConfig({ content })
  return postSimulationRun()
}
