/**
 * Which cards open expanded, in one place.
 *
 * The rule, added 2026-09 after the panel had grown too noisy to skim: a card
 * is expanded when it is part of the *story of the solve* - what was solved,
 * what the solver did, what came out - and collapsed when it holds *details you
 * go looking for*: per-worker statistics, presolve passes, cut counters.
 *
 * Expanded: overview, progress plot, parameters, solver header, initial and
 * presolved model, solver portfolio, search progress, response summary,
 * unrecognized sections (a warning, so never hidden), and the `Search stats`
 * table the response summary explicitly points at.
 * Collapsed: presolve log and summary, subsolver contributions, comments and
 * every other statistics table.
 *
 * Change the set below rather than sprinkling `collapsed` over the components.
 */

/** Statistics tables shown expanded; every other table starts collapsed. */
const EXPANDED_TABLES = new Set(['search_stats'])

/** Cards that are not log sections, or sections whose card starts collapsed. */
const COLLAPSED_CARDS = new Set(['presolve', 'presolve_summary', 'subsolvers', 'comment'])

export function tableCollapsedByDefault(tableId: string): boolean {
  return !EXPANDED_TABLES.has(tableId)
}

/** For everything that is not a statistics table: keyed by block kind or card name. */
export function cardCollapsedByDefault(key: string): boolean {
  return COLLAPSED_CARDS.has(key)
}
