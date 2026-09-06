/**
 * "Solver portfolio" card: the `Starting search at ...s with N workers` line and
 * the worker lists that follow it. Split off from the search log in 2026-09 so
 * that *what CP-SAT started* and *what it then found* are two separate cards -
 * the portfolio is static configuration, the progress is a time series, and
 * mixing them made both harder to read.
 */
import { Anchor, Card } from '../Card'
import { Md } from '../Md'
import { subsolverDoc } from '../../knowledge'
import type { BlockRef, Explanations, LineSpan, SearchProgress } from '../../types'

export function PortfolioBlock({
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
  return (
    <Card
      kind="search"
      title="Solver portfolio"
      span={span}
      owns={owns}
      path={blockRef.path}
      explanation={explanations.cards.portfolio}
    >
      {data.start && (
        <div className="kv">
          <Anchor line={data.start.line}>search started</Anchor>
          <Anchor line={data.start.line}>
            {data.start.time.toFixed(2)} s
            {data.start.num_workers !== null ? ` · ${data.start.num_workers} workers` : ''}
            {data.start.deterministic ? ' · deterministic' : ''}
            {data.start.sequential ? ' · sequential' : ''}
          </Anchor>
        </div>
      )}
      {data.subsolvers.map((g) => (
        <div key={g.line} className="portfolio-group">
          <Anchor line={g.line}>
            <b>
              {g.count ?? g.subsolvers.length} {g.label}
            </b>
          </Anchor>{' '}
          <span className="small">{explanations.subsolver_categories[g.category] ?? ''}</span>
          <ul className="subsolvers">
            {g.subsolvers.map((s) => {
              const doc = subsolverDoc(explanations, s.name)
              return (
                <li key={s.name}>
                  {doc?.details ? (
                    <details>
                      <summary>
                        <code>{s.name}</code>
                        {s.count > 1 ? ` ×${s.count}` : ''}
                        <span className="muted"> {doc.summary}</span>
                      </summary>
                      <Md className="details" text={doc.details} />
                    </details>
                  ) : (
                    <>
                      <code>{s.name}</code>
                      {s.count > 1 ? ` ×${s.count}` : ''}
                      {doc && <span className="muted"> {doc.summary}</span>}
                    </>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </Card>
  )
}
