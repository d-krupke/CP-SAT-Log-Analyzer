/**
 * Counts constraints by complexity level and variables by domain-size level for
 * the mix bars of the model cards (levels from knowledge/constraints.toml and
 * model.toml via the explanations). Pure functions, no React.
 */
import { domainLevel } from './knowledge'
import type { Explanations, LevelDoc, ModelDescription } from './types'

export interface MixSegment extends LevelDoc {
  key: string
  count: number
}

const OTHER: LevelDoc = { label: 'other', color: 'info', text: 'Not classified.' }

export function constraintMix(data: ModelDescription, ex: Explanations): MixSegment[] {
  const counts = new Map<string, number>()
  for (const c of data.constraints) {
    const key = ex.constraints[c.name]?.complexity ?? 'other'
    counts.set(key, (counts.get(key) ?? 0) + c.count)
  }
  const keys = [...Object.keys(ex.constraint_complexity), 'other']
  return keys.map((key) => ({ key, count: counts.get(key) ?? 0, ...(ex.constraint_complexity[key] ?? OTHER) }))
}

export function domainMix(data: ModelDescription, ex: Explanations): MixSegment[] {
  const counts = new Map<string, number>()
  for (const d of data.domains) {
    if (d.kind === 'summary') continue // counts distinct domains, not variables
    const key = d.kind === 'constant' ? 'constant' : (domainLevel(ex, d)?.level.id ?? 'other')
    counts.set(key, (counts.get(key) ?? 0) + d.count)
  }
  const levels: MixSegment[] = ex.domains.levels.map((l) => ({ key: l.id, count: counts.get(l.id) ?? 0, ...l }))
  levels.push({ key: 'constant', count: counts.get('constant') ?? 0, label: 'constant', color: 'info', text: ex.domains.constant })
  levels.push({ key: 'other', count: counts.get('other') ?? 0, ...OTHER })
  return levels
}
