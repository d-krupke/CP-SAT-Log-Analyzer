/** Overview card: key metrics as clickable tiles plus derived insights. */
import { Card } from './Card'
import { Md } from './Md'
import { useSelection } from '../state/selection'
import type { Analysis } from '../types'

export function Overview({ analysis }: { analysis: Analysis }) {
  const { select } = useSelection()
  return (
    <Card kind="overview" title="Overview" path="/overview">
      <div className="metrics">
        {analysis.metrics.map((m) => (
          <div
            key={m.key}
            className={`metric ${m.level}`}
            title={m.hint ?? (m.line ? `Log line ${m.line}` : undefined)}
            onClick={() => m.line && select(m.line, 'panel')}
          >
            <div className="label">{m.label}</div>
            <div className="value">{m.value}</div>
            {m.hint && m.level !== 'info' && <div className="hint">{m.hint}</div>}
          </div>
        ))}
      </div>
      {analysis.insights.length > 0 && (
        <div style={{ marginTop: 12 }}>
          {analysis.insights.map((ins, i) => (
            <div key={i} className={`insight ${ins.level}`} onClick={() => ins.lines[0] && select(ins.lines[0], 'panel')}>
              <b>{ins.title}</b>
              <Md text={ins.text} />
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
