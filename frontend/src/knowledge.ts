/**
 * Lookup helpers over the explanations served from knowledge/*.toml.
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

/** Domain-size level of a domain line (levels and thresholds from model.toml); undefined if the size is unknown. */
export function domainLevel(explanations: Explanations, d: Pick<DomainLine, 'kind' | 'size'>): DomainSizeLevel | undefined {
  if ((d.kind !== 'bool' && d.kind !== 'int') || d.size === null) return undefined
  const size = d.size
  return explanations.domains.levels.find((l) => l.max_size === null || size <= l.max_size)
}
