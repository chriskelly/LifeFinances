import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { getConfig, putConfig, saveAndRun } from './services/api'

type StatusVariant = 'idle' | 'loading' | 'success' | 'error'

export default function App() {
  const [editorText, setEditorText] = useState('')
  const [loadStatus, setLoadStatus] = useState<StatusVariant>('idle')
  const [loadMessage, setLoadMessage] = useState('')
  const [saveStatus, setSaveStatus] = useState<StatusVariant>('idle')
  const [saveMessage, setSaveMessage] = useState('')
  const [runBusy, setRunBusy] = useState(false)
  const [successRate, setSuccessRate] = useState<string | null>(null)
  const [tableColumns, setTableColumns] = useState<string[] | null>(null)
  const [tableData, setTableData] = useState<
    Array<Array<string | number | boolean | null>> | null
  >(null)

  const loadConfig = useCallback(async () => {
    setLoadStatus('loading')
    setLoadMessage('Loading configuration…')
    try {
      const doc = await getConfig()
      setEditorText(doc.content)
      setLoadStatus('success')
      setLoadMessage('Configuration loaded.')
    } catch (error) {
      setLoadStatus('error')
      setLoadMessage(
        error instanceof Error ? error.message : 'Failed to load configuration.',
      )
    }
  }, [])

  useEffect(() => {
    void loadConfig()
  }, [loadConfig])

  const handleSave = async () => {
    setSaveStatus('loading')
    setSaveMessage('Saving…')
    try {
      await putConfig({ content: editorText })
      setSaveStatus('success')
      setSaveMessage('Configuration saved.')
    } catch (error) {
      setSaveStatus('error')
      setSaveMessage(
        error instanceof Error ? error.message : 'Save failed.',
      )
    }
  }

  const handleSaveAndRun = async () => {
    setSaveStatus('loading')
    setSaveMessage('Saving and running simulation…')
    setRunBusy(true)
    try {
      const result = await saveAndRun(editorText)
      setSaveStatus('success')
      setSaveMessage('Configuration saved and simulation finished.')
      setSuccessRate(result.success_percentage)
      setTableColumns(result.first_result.columns)
      setTableData(result.first_result.data)
    } catch (error) {
      setSaveStatus('error')
      setSaveMessage(
        error instanceof Error ? error.message : 'Save and run failed.',
      )
    } finally {
      setRunBusy(false)
    }
  }

  return (
    <div className="app-layout">
      <section className="panel panel-editor" aria-labelledby="editor-heading">
        <h1 id="editor-heading">Edit config</h1>
        <div className="actions">
          <button type="button" onClick={() => void handleSave()}>
            Save
          </button>
          <button
            type="button"
            onClick={() => void handleSaveAndRun()}
            disabled={runBusy}
          >
            Save &amp; run
          </button>
        </div>
        <label className="editor-label" htmlFor="config-yaml">
          Configuration (YAML)
        </label>
        <textarea
          id="config-yaml"
          className="config-input"
          rows={20}
          spellCheck={false}
          value={editorText}
          onChange={(event) => setEditorText(event.target.value)}
          aria-describedby="load-status save-status"
        />
        <p
          id="load-status"
          role="status"
          className={`status status-${loadStatus}`}
        >
          {loadMessage}
        </p>
        <p
          id="save-status"
          role="status"
          className={`status status-${saveStatus}`}
        >
          {saveMessage}
        </p>
      </section>
      <section
        className="panel panel-results"
        aria-labelledby="results-heading"
      >
        <h1 id="results-heading">Results</h1>
        {successRate === null ? (
          <p className="placeholder">Run a simulation to see results.</p>
        ) : (
          <>
            <h2 className="success-heading">
              Chance of success: {successRate}%
            </h2>
            <h2>First result</h2>
            <div
              className="table-container"
              role="region"
              aria-label="First trial table"
            >
              {tableColumns && tableData ? (
                <table>
                  <thead>
                    <tr>
                      {tableColumns.map((col) => (
                        <th key={col} scope="col">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.map((row, rowIndex) => (
                      <tr key={`row-${rowIndex}`}>
                        {row.map((cell, cellIndex) => (
                          <td key={`cell-${rowIndex}-${cellIndex}`}>
                            {String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
            </div>
          </>
        )}
      </section>
    </div>
  )
}
