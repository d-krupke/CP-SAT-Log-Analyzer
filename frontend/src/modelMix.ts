/**
 * Counts constraints by complexity level and variables by domain-size level for
 * the mix bars of the model cards (levels from knowledge/constraints.toml and
 * model.toml via the explanations). Pure functions, no React.
 *
 * A constraint line is not necessarily one level: `#kLinear1: 210 (#enforced:
 * 210)` are indicator constraints, not plain bounds, and the knowledge base
 * classifies that share separately (`enforced_complexity`). `constraintParts`
 * does that split once, for both the mix bar and the per-row tags.
 */
import { domainLevel } from './knowledge'
import type { ConstraintLine, Explanations, LevelDoc, ModelDescription } from './types'

export interface MixSegment extends LevelDoc {
  key: string
  count: number
}

/** One share of a constraint line: how many, at which level, and why. */
export interface ConstraintPart {
  key: string
  count: number
  enforced: boolean
  /** What this share is, for the tag tooltip: the enforced note or the kind's details. */
  note: string
}

const OTHER: LevelDoc = { label: 'other', color: 'info', text: 'Not classified.' }
const UNKNOWN: LevelDoc = { label: 'unknown size', color: 'info', text: 'Truncated domain line; the number of values is unknown.' }

/**
 * Split a constraint line into its plain and its enforced share.
 *
 * The enforced share is only broken out where the knowledge base says
 * enforcement changes the level (the linear kinds: enforced clauses stay
 * clauses). `#enforced` can exceed the count on a malformed line, so it is
 * clamped rather than trusted.
 */
export function constraintParts(c: ConstraintLine, ex: Explanations): ConstraintPart[] {
  const doc = ex.constraints[c.name]
  const level = doc?.complexity ?? 'other'
  const note = doc?.details || doc?.summary || ''
  const enforcedLevel = doc?.enforced_complexity
  const enforced = Math.max(0, Math.min(c.count, c.details.enforced ?? 0))
  if (!enforcedLevel || enforced === 0) {
    // No split, but an enforced share can still be worth a word (optional intervals).
    const extra = enforced > 0 ? doc?.enforced_summary : ''
    return [{ key: level, count: c.count, enforced: false, note: [note, extra].filter(Boolean).join('\n\n') }]
  }
  const parts: ConstraintPart[] = [{ key: enforcedLevel, count: enforced, enforced: true, note: doc?.enforced_summary || note }]
  if (enforced < c.count) parts.unshift({ key: level, count: c.count - enforced, enforced: false, note })
  return parts
}

export function constraintMix(data: ModelDescription, ex: Explanations): MixSegment[] {
  const counts = new Map<string, number>()
  for (const c of data.constraints) {
    for (const part of constraintParts(c, ex)) {
      counts.set(part.key, (counts.get(part.key) ?? 0) + part.count)
    }
  }
  const keys = [...Object.keys(ex.constraint_complexity), 'other']
  return keys.map((key) => ({ key, count: counts.get(key) ?? 0, ...(ex.constraint_complexity[key] ?? OTHER) }))
}

export function domainMix(data: ModelDescription, ex: Explanations): MixSegment[] {
  const counts = new Map<string, number>()
  for (const d of data.domains) {
    if (d.kind === 'summary') continue // counts distinct domains, not variables
    const key = d.kind === 'constant' ? 'constant' : (domainLevel(ex, d)?.id ?? 'unknown')
    counts.set(key, (counts.get(key) ?? 0) + d.count)
  }
  const levels: MixSegment[] = ex.domains.levels.map((l) => ({ key: l.id, count: counts.get(l.id) ?? 0, ...l }))
  levels.push({ key: 'constant', count: counts.get('constant') ?? 0, label: 'constant', color: 'info', text: ex.domains.constant })
  levels.push({ key: 'unknown', count: counts.get('unknown') ?? 0, ...UNKNOWN })
  return levels
}
