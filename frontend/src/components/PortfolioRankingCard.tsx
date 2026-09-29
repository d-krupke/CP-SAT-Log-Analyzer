/**
 * "Portfolio ranking": which full-problem strategies mattered for the objective in this
 * run, and which ones to keep when running with fewer workers.
 *
 * Added 2026-09-28 to show the result of the portfolio-importance study
 * (benchmarks/portfolio_study/REPORT.md); restyled the same day from a plain table into:
 * - a stacked bar "where the progress came from": one colored segment per strategy
 *   that scored, one grey segment for LNS and first-solution workers,
 * - the ranked list, each strategy with the color of its segment, its verdict and a bar,
 * - the "Give LNS more threads" hint when LNS carried the run (LnsHintBox.tsx),
 * - one compact box with the caveats for logs where the ranking is unreliable,
 * - the fewer-workers comparison (FewerWorkers.tsx) and a fold with the method.
 * The backend (app/importance.py) does the ranking; all texts come from
 * knowledge/importance.toml and the `portfolio_ranking` card text in blocks.toml.
 */
import { Card } from './Card'
import { FewerWorkers } from './FewerWorkers'
import { LnsHintBox } from './LnsHintBox'
import { Md } from './Md'
import { cardCollapsedByDefault } from '../state/expansion'
import { useSelection } from '../state/selection'
import { tooltip } from '../tooltip'
import type { Explanations, PortfolioRanking, RankedSubsolver } from '../types'

/** Segment colors, in rank order; strategies that scored nothing get no color. */
const PALETTE = ['var(--good)', 'var(--accent)', 'var(--alt)', 'var(--k-model)', 'var(--warn)', 'var(--k-response)']

const pct = (x: number) => (x > 0 && x < 0.01 ? '<1%' : `${Math.round(100 * x)}%`)

function colorOf(ranked: RankedSubsolver[], name: string): string | undefined {
  const i = ranked.filter((r) => r.score > 0).findIndex((r) => r.name === name)
  return i >= 0 ? PALETTE[i % PALETTE.length] : undefined
}

export function PortfolioRankingCard({ ranking, explanations }: { ranking: PortfolioRanking | null; explanations: Explanations }) {
  if (ranking === null) return null
  const top = ranking.ranked[0]
  const texts = explanations.importance_texts
  return (
    <Card
      kind="search"
      title="Portfolio ranking"
      summary={top.score > 0 ? `${top.name} carried ${pct(top.score)}` : 'LNS did the work'}
      path="/portfolio_ranking"
      explanation={explanations.cards.portfolio_ranking}
      collapsed={cardCollapsedByDefault('portfolio_ranking')}
    >
      <div className="pr">
        <ProgressSplit ranking={ranking} />
        {ranking.lns_hint && <LnsHintBox hint={ranking.lns_hint} texts={texts} />}
        {ranking.caveats.length > 0 && (
          <div className="pr-caveats">
            <div className="pr-caveats-title">Read with care</div>
            <ul>
              {ranking.caveats.map((c, i) => (
                <li key={i}>
                  <Md text={c} />
                </li>
              ))}
            </ul>
          </div>
        )}
        <RankedList ranking={ranking} explanations={explanations} />
        {ranking.choices.length > 0 && top.score > 0 && <FewerWorkers choices={ranking.choices} texts={texts} />}
        {texts.method && (
          <details className="pr-method">
            <summary>How is this computed?</summary>
            <Md text={texts.method} />
          </details>
        )}
      </div>
    </Card>
  )
}

/** One bar for 100% of the objective improvement, split by who delivered it. */
function ProgressSplit({ ranking }: { ranking: PortfolioRanking }) {
  const scored = ranking.ranked.filter((r) => r.score > 0)
  return (
    <div className="pr-split">
      <div className="pr-label">Where the objective progress came from</div>
      <div className="pr-bar">
        {scored.map((r) => (
          <span key={r.name} style={{ width: `${100 * r.score}%`, background: colorOf(ranking.ranked, r.name) }} title={`${r.name}: ${pct(r.score)}`}>
            {r.score >= 0.12 && `${r.name} ${pct(r.score)}`}
          </span>
        ))}
        {ranking.other_share > 0 && (
          <span className="other" style={{ width: `${100 * ranking.other_share}%` }} title={`LNS and heuristics: ${pct(ranking.other_share)}`}>
            {ranking.other_share >= 0.18 && `LNS & heuristics ${pct(ranking.other_share)}`}
          </span>
        )}
      </div>
      <div className="small">
        LNS, local search and first-solution workers are not ranked: CP-SAT fills the remaining threads with them anyway.
      </div>
    </div>
  )
}

function RankedList({ ranking, explanations }: { ranking: PortfolioRanking; explanations: Explanations }) {
  const { select } = useSelection()
  const best = Math.max(...ranking.ranked.map((r) => r.score), 1e-9)
  return (
    <ol className="pr-list">
      {ranking.ranked.map((r, i) => {
        const verdict = explanations.importance_verdicts[r.verdict]
        const color = colorOf(ranking.ranked, r.name)
        const meta = [
          r.improvements > 0 && `${r.improvements} improving`,
          r.bounds > 0 && `${r.bounds} bound${r.bounds === 1 ? '' : 's'}`,
        ].filter(Boolean)
        return (
          <li
            key={r.name}
            className={`${r.score > 0 ? '' : 'idle'}${r.line !== null ? ' clickable' : ''}`}
            onClick={() => r.line !== null && select(r.line, 'panel')}
            title={r.line !== null ? 'Show its last improving solution in the log' : undefined}
          >
            <span className="rank">{i + 1}</span>
            <span className="name">
              <i className="swatch" style={{ background: color ?? 'transparent', borderColor: color ?? 'var(--border)' }} />
              {r.name}
            </span>
            <span className={`tag ${verdict?.color ?? 'neutral'}`} title={tooltip(verdict?.text)}>
              {verdict?.label ?? r.verdict}
            </span>
            <span className="meter" title={r.score > 0 ? `${pct(r.share)} of the improvement without the time weighting` : undefined}>
              <span className="track">
                <i style={{ width: `${(100 * r.score) / best}%`, background: color }} />
              </span>
              <b>{r.score > 0 ? pct(r.score) : '–'}</b>
            </span>
            <span className="meta">{meta.join(' · ')}</span>
          </li>
        )
      })}
    </ol>
  )
}
