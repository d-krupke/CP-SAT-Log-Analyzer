import { useState } from 'react'
import { Anchor, Card } from '../Card'
import { formatNumber, useSelection } from '../../state/selection'
import type { BlockRef, Explanations, SearchEvent, SearchProgress } from '../../types'

const CATEGORY_DOC: Record<string, string> = {
  full: 'Full-problem workers: complete searches that can prove optimality/infeasibility.',
  first_solution: 'First-solution heuristics run until an incumbent exists, then hand their threads to the improvement heuristics.',
  interleaved: 'Incomplete/interleaved workers: LNS and local search rounds sharing the remaining threads.',
  helper: 'Helper tasks (synchronisation, neighbourhood generation); not searches.',
  ignored: 'Configurations excluded via parameters or not applicable to this model.',
  unknown: '',
}

function eventText(ev: SearchEvent, sense: string | null): string {
  if (ev.kind === 'solution') {
    const obj = ev.objective !== null ? formatNumber(ev.objective) : ev.objective_infinite ?? ''
    const range = ev.next_lb !== null && ev.next_ub !== null ? ` · next:[${formatNumber(ev.next_lb)},${formatNumber(ev.next_ub)}]` : ''
    return `best ${obj}${range}`
  }
  if (ev.kind === 'bound') {
    const b = sense === 'maximize' ? ev.next_ub : ev.next_lb
    return `bound ${b !== null ? formatNumber(b) : ''} · next:[${formatNumber(ev.next_lb)},${formatNumber(ev.next_ub)}]`
  }
  if (ev.kind === 'model') {
    return `${formatNumber(ev.model_vars)}/${formatNumber(ev.model_vars_total)} vars, ${formatNumber(ev.model_constraints)}/${formatNumber(ev.model_constraints_total)} constraints`
  }
  return ev.message
}

export function SearchBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: SearchProgress; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const [filter, setFilter] = useState<string>('all')
  const events = data.events.filter((e) => filter === 'all' || e.kind === filter)
  const counts = { solution: 0, bound: 0, model: 0, done: 0, other: 0 }
  for (const e of data.events) counts[e.kind]++
  return (
    <Card kind="search" title="Search log" span={blockRef.span} path={blockRef.path} explanation={explanations.blocks.search}>
      {data.start && (
        <div className="kv">
          <Anchor line={data.start.line}>started at</Anchor>
          <Anchor line={data.start.line}>
            {data.start.time.toFixed(2)} s
            {data.start.num_workers !== null ? ` · ${data.start.num_workers} workers` : ''}
            {data.start.deterministic ? ' · deterministic' : ''}
            {data.start.sequential ? ' · sequential' : ''}
          </Anchor>
          <div>objective</div>
          <div>{data.objective_sense ?? 'none (satisfaction problem)'}</div>
        </div>
      )}
      {data.subsolvers.length > 0 && (
        <details>
          <summary>Portfolio ({data.subsolvers.map((g) => `${g.count ?? g.subsolvers.length} ${g.label}`).join(', ')})</summary>
          {data.subsolvers.map((g) => (
            <div key={g.line} style={{ margin: '6px 0' }}>
              <Anchor line={g.line}>
                <b>{g.label}</b>
              </Anchor>{' '}
              <span className="small">{CATEGORY_DOC[g.category] ?? ''}</span>
              <div>
                {g.subsolvers.map((s) => (
                  <span key={s.name} className="tag" title={explanations.subsolvers[s.name] ?? ''}>
                    {s.name}
                    {s.count > 1 ? ` ×${s.count}` : ''}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </details>
      )}
      <div className="legend" style={{ margin: '8px 0' }}>
        <span>Events:</span>
        {(['all', 'solution', 'bound', 'model', 'done', 'other'] as const).map((k) => (
          <button key={k} style={{ padding: '1px 8px', fontSize: 12, borderColor: filter === k ? 'var(--accent)' : undefined }} onClick={() => setFilter(k)}>
            {k}
            {k !== 'all' ? ` (${counts[k]})` : ''}
          </button>
        ))}
      </div>
      <div className="tbl-wrap" style={{ maxHeight: 420, overflowY: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr>
              <th title="#N = N-th improving solution; #Bound/#Model/#Done">event</th>
              <th title="Seconds since the solver started">time</th>
              <th title="Worker that produced the event">subsolver</th>
              <th style={{ textAlign: 'left' }}>details</th>
            </tr>
          </thead>
          <tbody>
            {events.map((ev) => (
              <tr key={ev.line} className={selection.line === ev.line ? 'selected' : ''} onClick={() => select(ev.line, 'panel')}>
                <td>
                  <Anchor line={ev.line}>{ev.label}</Anchor>
                </td>
                <td className="num">
                  <Anchor line={ev.line}>{ev.time.toFixed(2)}</Anchor>
                </td>
                <td style={{ textAlign: 'left' }} title={ev.subsolver ? explanations.subsolvers[ev.subsolver] ?? '' : ''}>
                  <Anchor line={ev.line}>{ev.subsolver ?? ''}</Anchor>
                </td>
                <td style={{ textAlign: 'left', whiteSpace: 'normal' }}>
                  <Anchor line={ev.line}>
                    {eventText(ev, data.objective_sense)}
                    {ev.tags.map((t) => (
                      <span key={t} className="tag" style={{ marginLeft: 6 }}>
                        {t}
                      </span>
                    ))}
                    {ev.skipped_logs !== null && <span className="tag warn" style={{ marginLeft: 6 }}>{ev.skipped_logs} skipped</span>}
                  </Anchor>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
