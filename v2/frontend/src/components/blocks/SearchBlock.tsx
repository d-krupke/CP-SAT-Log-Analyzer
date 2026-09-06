/**
 * The search section of the log, shown as two cards: the portfolio CP-SAT
 * started (see PortfolioBlock) and the stream of progress events below. Both
 * anchor to the same block of the log, so each declares which part of it it
 * owns (`owns`) to keep the highlighting unambiguous.
 */
import { useState } from 'react'
import { Anchor, Card } from '../Card'
import { subsolverDoc } from '../../knowledge'
import { formatNumber, useSelection } from '../../state/selection'
import { PortfolioBlock } from './PortfolioBlock'
import type { BlockRef, Explanations, LineSpan, SearchEvent, SearchProgress } from '../../types'


function eventText(ev: SearchEvent, sense: string | null): string {
  if (ev.kind === 'solution') {
    if (ev.objective === null && ev.objective_infinite === null) return `solution found${ev.message ? ` · ${ev.message}` : ''}`
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

/** Splits the parsed search block into the portfolio card and the progress card. */
export function SearchCards({ blockRef, data, explanations }: { blockRef: BlockRef; data: SearchProgress; explanations: Explanations }) {
  const portfolioLines = [data.start?.line, ...data.subsolvers.map((g) => g.line)].filter(
    (l): l is number => l !== undefined,
  )
  const eventLines = data.events.map((e) => e.line)
  const both = portfolioLines.length > 0 && eventLines.length > 0
  // Everything up to the last portfolio line belongs to the portfolio card, the
  // rest to the progress card. Only needed while both are on screen.
  const cut = portfolioLines.length > 0 ? Math.max(...portfolioLines) : blockRef.span.start - 1
  const portfolioSpan: LineSpan = portfolioLines.length
    ? { start: Math.min(...portfolioLines), end: both ? cut : blockRef.span.end }
    : blockRef.span
  const progressSpan: LineSpan = eventLines.length
    ? { start: Math.min(...eventLines), end: Math.max(blockRef.span.end, ...eventLines) }
    : blockRef.span
  return (
    <>
      {portfolioLines.length > 0 && (
        <PortfolioBlock
          blockRef={blockRef}
          data={data}
          explanations={explanations}
          span={portfolioSpan}
          owns={both ? { start: 0, end: cut } : undefined}
        />
      )}
      {(eventLines.length > 0 || portfolioLines.length === 0) && (
        <SearchProgressBlock
          blockRef={blockRef}
          data={data}
          explanations={explanations}
          span={progressSpan}
          owns={both ? { start: cut + 1, end: Number.MAX_SAFE_INTEGER } : undefined}
        />
      )}
    </>
  )
}

export function SearchProgressBlock({
  blockRef,
  data,
  explanations,
  span,
  owns,
}: {
  blockRef: BlockRef
  data: SearchProgress
  explanations: Explanations
  span: LineSpan
  owns?: LineSpan
}) {
  const { selection, select } = useSelection()
  const [filter, setFilter] = useState<string>('all')
  const events = data.events.filter((e) => filter === 'all' || e.kind === filter)
  const counts = { solution: 0, bound: 0, model: 0, done: 0, other: 0 }
  for (const e of data.events) counts[e.kind]++
  return (
    <Card kind="search" title="Search progress" span={span} owns={owns} path={blockRef.path} explanation={explanations.blocks.search}>
      <div className="kv">
        <div>objective</div>
        <div>{data.objective_sense ?? 'none (satisfaction problem)'}</div>
      </div>
      <div className="legend" style={{ margin: '8px 0' }}>
        <span>Events:</span>
        {(['all', 'solution', 'bound', 'model', 'done', 'other'] as const).filter((k) => k === 'all' || counts[k] > 0).map((k) => (
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
                <td style={{ textAlign: 'left' }} title={subsolverDoc(explanations, ev.subsolver)?.summary ?? ''}>
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
