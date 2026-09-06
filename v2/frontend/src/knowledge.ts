/**
 * Lookup helpers over the explanations served from v2/knowledge/*.toml.
 * Mirrors app/explanations.py: exact name, then the longest key the name starts
 * with (followed by "_", e.g. rins_lns_default -> rins), then glob patterns.
 */
import type { DomainLine, DomainSizeLevel, Explanations, SubsolverDoc } from './types'

function globToRegExp(glob: string): RegExp {
  return new RegExp('^' + glob.split('*').map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*') + '$')
}

export function subsolverDoc(explanations: Explanations, name: string | null | undefined): SubsolverDoc | undefined {
  if (!name) return undefined
  const docs = explanations.subsolvers
  if (docs[name]) return docs[name]
  let best: string | undefined
  for (const key of Object.keys(docs)) {
    if (name.startsWith(key + '_') && (best === undefined || key.length > best.length)) best = key
  }
  if (best !== undefined) return docs[best]
  return explanations.subsolver_patterns.find((p) => globToRegExp(p.pattern).test(name))
}

/**
 * Domain-size level of a domain line (levels and thresholds from model.toml).
 * Returns the level and the size it was judged by; `estimate` is true when the
 * exact size is unknown (truncated line) and the span hi-lo+1 was used instead.
 */
export function domainLevel(
  explanations: Explanations,
  d: Pick<DomainLine, 'kind' | 'lo' | 'hi' | 'size'>,
): { level: DomainSizeLevel; size: number; estimate: boolean } | undefined {
  if (d.kind !== 'bool' && d.kind !== 'int') return undefined
  let size = d.size
  let estimate = false
  if (size === null) {
    if (d.lo === null || d.hi === null) return undefined
    size = d.hi - d.lo + 1
    estimate = true
  }
  const level = explanations.domains.levels.find((l) => l.max_size === null || size <= l.max_size)
  return level ? { level, size, estimate } : undefined
}
