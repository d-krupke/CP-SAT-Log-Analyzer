/**
 * Visual indicators for the model cards: a stacked "mix" bar of constraints by
 * complexity and of variables by domain size, plus the per-row level tags.
 * Levels, colors and texts come from knowledge/constraints.toml and model.toml
 * via the explanations; the counting lives in src/modelMix.ts, this file draws.
 */
import { formatNumber } from '../../state/selection'
import { domainLevel } from '../../knowledge'
import type { MixSegment } from '../../modelMix'
import type { DomainLine, Explanations, LevelDoc } from '../../types'

export function LevelTag({ level, title }: { level: LevelDoc | undefined; title?: string }) {
  if (!level) return null
  return (
    <span className={`tag ${level.color}`} title={title ?? level.text}>
      {level.label}
    </span>
  )
}

/**
 * `2,001 -> 1,001  -50%`: what presolve did to a count.
 *
 * Shrinking is the good case, growth the one worth noticing (a global constraint
 * unrolled into thousands of Booleans), so the sign is colored rather than just
 * printed.
 */
export function Delta({ from, to }: { from: number; to: number }) {
  if (from === 0 || from === to) return <span className="delta info">unchanged</span>
  const change = (100 * (to - from)) / from
  const level = change > 20 ? 'warn' : change < 0 ? 'good' : 'info'
  // A presolve blow-up reaches +240392%, which nobody reads: say ×2,405 instead.
  const text =
    to >= 3 * from
      ? `×${formatNumber(Math.round((10 * to) / from) / 10)}`
      : `${change > 0 ? '+' : ''}${Math.abs(change) < 1 ? change.toFixed(1) : Math.round(change)}%`
  return (
    <span className={`delta ${level}`} title={`${formatNumber(from)} → ${formatNumber(to)}`}>
      {text}
    </span>
  )
}

function pct(count: number, total: number): string {
  const p = (100 * count) / total
  return p < 1 ? '<1%' : `${Math.round(p)}%`
}

export function MixBar({ title, segments }: { title: string; segments: MixSegment[] }) {
  const total = segments.reduce((a, s) => a + s.count, 0)
  if (total === 0) return null
  const shown = segments.filter((s) => s.count > 0)
  return (
    <div className="mix">
      <div className="mix-title">{title}</div>
      <div className="mix-bar" role="img" aria-label={shown.map((s) => `${s.label} ${pct(s.count, total)}`).join(', ')}>
        {shown.map((s) => (
          <span key={s.key} className={`seg ${s.color}`} style={{ width: `${(100 * s.count) / total}%` }} title={`${s.label}: ${formatNumber(s.count)} (${pct(s.count, total)})\n${s.text}`} />
        ))}
      </div>
      <div className="mix-legend">
        {shown.map((s) => (
          <span key={s.key} title={s.text}>
            <i className={`dot ${s.color}`} />
            {s.label} {formatNumber(s.count)} ({pct(s.count, total)})
          </span>
        ))}
      </div>
    </div>
  )
}

/** Size cell of a domain row: value, level tag and holes/truncation hints. */
export function DomainSize({ d, ex }: { d: DomainLine; ex: Explanations }) {
  if (d.kind === 'summary') return <span className="muted" title={ex.domains.summary}>{d.intervals !== null ? `≤ ${d.intervals} intervals` : ''}</span>
  if (d.kind === 'constant') return <span className="tag info" title={ex.domains.constant}>constant</span>
  const level = domainLevel(ex, d)
  if (!level || d.size === null) {
    return (
      <span className="domain-size">
        {d.lo !== null && d.hi !== null && <span className="muted">span {formatNumber(d.lo)} … {formatNumber(d.hi)}</span>}
        {d.truncated && (
          <span className="tag" title={ex.domains.truncated}>
            truncated
          </span>
        )}
      </span>
    )
  }
  const width = Math.max(4, Math.min(100, (100 * Math.log10(d.size)) / 9))
  return (
    <span className="domain-size">
      <span className="sizebar" title={`${formatNumber(d.size)} values`}>
        <i className={level.color} style={{ width: `${width}%` }} />
      </span>
      <span className="num">{formatNumber(d.size)}</span>
      <LevelTag level={level} />
      {d.intervals !== null && d.intervals > 1 && (
        <span className="tag warn" title={ex.domains.holes}>
          {d.intervals} intervals
        </span>
      )}
    </span>
  )
}
