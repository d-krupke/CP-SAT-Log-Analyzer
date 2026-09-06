/**
 * Shared selection state: the currently selected log line and where the
 * selection came from. The log view and the analysis panel both read it and
 * scroll to the counterpart, which gives the two-way "click a line <-> see the
 * explanation" navigation.
 */
import { createContext, useContext } from 'react'
import type { BlockRef, CpSatLog } from '../types'

export type Source = 'log' | 'panel'
export interface Selection {
  line: number | null
  source: Source
  nonce: number
}
export interface SelectionApi {
  selection: Selection
  block: BlockRef | null
  select: (line: number | null, source: Source) => void
}

export const SelectionContext = createContext<SelectionApi>({
  selection: { line: null, source: 'log', nonce: 0 },
  block: null,
  select: () => {},
})

export function useSelection(): SelectionApi {
  return useContext(SelectionContext)
}

export function blockForLine(log: CpSatLog, line: number | null): BlockRef | null {
  if (line === null) return null
  for (const b of log.blocks) {
    if (b.span.start <= line && line <= b.span.end) return b
  }
  return null
}

/**
 * Colour class for an indexed block. Unrecognised text wins over the original
 * kind: a duplicated header keeps `kind: 'solver'` but must not look parsed.
 */
export function blockClass(ref: BlockRef): string {
  return isUnparsed(ref) ? 'k-unparsed' : kindClass(ref.kind)
}

/** Did the parser keep this block verbatim because it could not use it? */
export function isUnparsed(ref: BlockRef): boolean {
  return ref.path.startsWith('/unparsed/')
}

/** Colour class per block kind, shared by the log gutter and the cards. */
export function kindClass(kind: string): string {
  switch (kind) {
    case 'solver':
      return 'k-solver'
    case 'initial_model':
    case 'presolved_model':
      return 'k-model'
    case 'presolve':
    case 'presolve_summary':
      return 'k-presolve'
    case 'search':
      return 'k-search'
    case 'table':
    case 'task_timing':
      return 'k-table'
    case 'response':
      return 'k-response'
    case 'comment':
      return 'k-comment'
    case 'message':
      return 'k-message'
    case 'unparsed':
      return 'k-unparsed'
    default:
      return 'k-unknown'
  }
}

export function formatNumber(x: number | string | null | undefined): string {
  if (x === null || x === undefined) return ''
  if (typeof x === 'string') return x
  if (Number.isInteger(x)) return x.toLocaleString('en-US')
  if (Math.abs(x) >= 1e6 || Math.abs(x) < 1e-3) return x.toExponential(3)
  return x.toLocaleString('en-US', { maximumFractionDigits: 4 })
}
