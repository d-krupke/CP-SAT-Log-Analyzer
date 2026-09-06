/**
 * Which phase of the solve a card belongs to, so the analysis panel can put a
 * header in front of each group instead of one flat stack of cards.
 *
 * Added 2026-09: the panel shows one card per log section in log order, which
 * follows CP-SAT's own structure (header, model, presolve, search, final
 * tables, response). Naming those groups makes the panel skimmable and tells
 * the reader where in the solve they are.
 *
 * `phaseOf` returns `null` for sections that can appear anywhere - free-form
 * messages, `//` comments, text the parser could not read. Those inherit the
 * phase they appear in, so a comment in the middle of presolve does not start a
 * new group and push everything after it under the wrong header.
 */
import { isUnparsed } from './selection'
import type { BlockRef } from '../types'

export type Phase = 'summary' | 'setup' | 'presolve' | 'search' | 'stats' | 'result'

export const PHASE_LABELS: Record<Phase, string> = {
  summary: 'Summary',
  setup: 'Setup',
  presolve: 'Presolve',
  search: 'Search',
  stats: 'Final statistics',
  result: 'Result',
}

/** The phase of an indexed log section, or `null` when it belongs to no phase. */
export function phaseOf(ref: BlockRef): Phase | null {
  // A section kept verbatim keeps its original kind but is not part of the story.
  if (isUnparsed(ref)) return null
  switch (ref.kind) {
    case 'solver':
    case 'initial_model':
      return 'setup'
    case 'presolve':
    case 'presolve_summary':
    case 'presolved_model':
      return 'presolve'
    case 'search':
      return 'search'
    case 'table':
    case 'task_timing':
      return 'stats'
    case 'response':
      return 'result'
    default:
      return null
  }
}
