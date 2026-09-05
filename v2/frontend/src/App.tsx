/**
 * Root of the CP-SAT Log Analyzer UI: top bar with input controls, a landing
 * page to paste/upload/select a log, and the two-panel view (analysis left,
 * raw log right) once a log is parsed.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadExplanations, parseLog, readExample } from './api'
import { AnalysisPanel } from './components/AnalysisPanel'
import { Landing } from './components/Landing'
import { LogView } from './components/LogView'
import { Splitter } from './components/Splitter'
import { blockForLine, SelectionContext, type Selection, type Source } from './state/selection'
import type { Explanations, ParseResult } from './types'

const EMPTY_EXPLANATIONS: Explanations = { blocks: {}, tables: {}, response_fields: {}, subsolvers: {} }

function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState<string>(() => {
    try {
      const stored = localStorage.getItem('theme')
      if (stored) return stored
    } catch {
      /* ignore */
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('theme', theme)
    } catch {
      /* ignore */
    }
  }, [theme])
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))]
}

export default function App() {
  const [theme, toggleTheme] = useTheme()
  const [text, setText] = useState('')
  const [result, setResult] = useState<ParseResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [explanations, setExplanations] = useState<Explanations>(EMPTY_EXPLANATIONS)
  const [selection, setSelection] = useState<Selection>({ line: null, source: 'log', nonce: 0 })

  useEffect(() => {
    loadExplanations().then(setExplanations).catch(() => {})
  }, [])

  const analyze = useCallback(async (logText: string) => {
    setBusy(true)
    setError(null)
    try {
      const res = await parseLog(logText)
      setText(logText)
      setResult(res)
      setSelection({ line: null, source: 'log', nonce: 0 })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }, [])

  const loadExample = useCallback(
    (name: string) => {
      setBusy(true)
      readExample(name)
        .then(analyze)
        .catch((e: Error) => {
          setError(e.message)
          setBusy(false)
        })
    },
    [analyze],
  )

  // ?example=98_02 deep link
  useEffect(() => {
    const name = new URLSearchParams(window.location.search).get('example')
    if (name) loadExample(name)
  }, [loadExample])

  const select = useCallback((line: number | null, source: Source) => {
    setSelection((s) => ({ line, source, nonce: s.nonce + 1 }))
  }, [])
  const block = useMemo(
    () => (result ? blockForLine(result.log, selection.line) : null),
    [result, selection.line],
  )
  const lines = useMemo(() => text.replace(/\r\n?/g, '\n').split('\n'), [text])

  return (
    <SelectionContext.Provider value={{ selection, block, select }}>
      <div className="app">
        <div className="topbar">
          <h1>CP-SAT Log Analyzer</h1>
          {result && (
            <button onClick={() => setResult(null)} title="Back to the input page">
              ← New log
            </button>
          )}
          <span className="status">{busy ? 'Parsing…' : result ? `${result.log.num_lines} lines` : ''}</span>
          {error && <span className="error">{error}</span>}
          <span className="spacer" />
          <a href="https://github.com/d-krupke/CP-SAT-Log-Analyzer" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a href="https://d-krupke.github.io/cpsat-primer/" target="_blank" rel="noreferrer">
            CP-SAT Primer
          </a>
          <button onClick={toggleTheme} title="Toggle dark/light theme">
            {theme === 'dark' ? '☀︎' : '☾'}
          </button>
        </div>
        {result ? (
          <div className="main">
            <div className="pane">
              <AnalysisPanel result={result} explanations={explanations} />
            </div>
            <Splitter />
            <div className="pane">
              <LogView lines={lines} log={result.log} />
            </div>
          </div>
        ) : (
          <Landing onAnalyze={analyze} onExample={loadExample} busy={busy} initialText={text} />
        )}
      </div>
    </SelectionContext.Provider>
  )
}
