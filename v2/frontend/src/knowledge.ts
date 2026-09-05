/**
 * Lookup helpers over the explanations served from v2/knowledge/*.toml.
 * Mirrors app/explanations.py: exact name, then the longest key the name starts
 * with (followed by "_", e.g. rins_lns_default -> rins), then glob patterns.
 */
import type { Explanations, SubsolverDoc } from './types'

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
