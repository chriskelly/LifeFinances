/** Types aligned with `specs/001-react-flask-migration/contracts/openapi.yaml`. */

export interface ConfigDocument {
  content: string
}

export interface ConfigSaveResponse {
  ok: boolean
  message?: string
}

export interface FirstResultTable {
  columns: string[]
  data: Array<Array<string | number | boolean | null>>
}

export interface SimulationResult {
  success_percentage: string
  first_result: FirstResultTable
}

export interface ErrorBody {
  error: {
    message: string
    code?: string
    details?: string
  }
}
