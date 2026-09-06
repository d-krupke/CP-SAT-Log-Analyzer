/** Input page: paste a log, upload a file, or pick a bundled example. */
import { useEffect, useState } from 'react'
import { listExamples } from '../api'
import type { ExampleInfo } from '../types'

interface Props {
  onAnalyze: (text: string) => void
  onExample: (name: string) => void
  busy: boolean
  initialText: string
}

export function Landing({ onAnalyze, onExample, busy, initialText }: Props) {
  const [text, setText] = useState(initialText)
  const [examples, setExamples] = useState<ExampleInfo[]>([])
  useEffect(() => {
    listExamples().then(setExamples).catch(() => setExamples([]))
  }, [])

  const onFile = (file: File | undefined) => {
    if (!file) return
    file.text().then((t) => {
      setText(t)
      onAnalyze(t)
    })
  }

  return (
    <div className="landing">
      <p>
        Paste the log of a CP-SAT run (enable it with <code>log_search_progress = True</code>) to
        get every section explained, linked line by line to the parsed data, plots and the
        relevant background from the <a href="https://d-krupke.github.io/cpsat-primer/">CP-SAT Primer</a>.
        Logs are parsed on the server but not stored.
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Starting CP-SAT solver v9.15.6755&#10;Parameters: max_time_in_seconds: 60 ..."
        spellCheck={false}
      />
      <div className="row">
        <button className="primary" disabled={busy || !text.trim()} onClick={() => onAnalyze(text)}>
          Analyze log
        </button>
        <label>
          <input type="file" accept=".txt,.log" style={{ display: 'none' }} onChange={(e) => onFile(e.target.files?.[0])} />
          <span className="tag" style={{ cursor: 'pointer', padding: '5px 10px' }}>
            Upload file…
          </span>
        </label>
        <span className="small">Your log stays private; nothing is persisted.</span>
      </div>
      {examples.length > 0 && (
        <>
          <h3>Or explore an example</h3>
          <div className="examples">
            {examples.map((ex) => (
              <button key={ex.name} onClick={() => onExample(ex.name)} disabled={busy}>
                <b>
                  {ex.name} <span>· OR-Tools {ex.version_hint}</span>
                </b>
                {ex.description && <span>{ex.description}</span>}
                <span className="small">{ex.summary}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
