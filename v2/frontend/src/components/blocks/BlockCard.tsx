/** Dispatches a block reference (JSON pointer into the log) to its renderer. */
import { isUnparsed } from '../../state/selection'
import type { BlockRef, CpSatLog, Explanations } from '../../types'
import { ModelBlock } from './ModelBlock'
import { PresolveBlock, PresolveSummaryBlock } from './PresolveBlock'
import { ResponseBlock } from './ResponseBlock'
import { SearchCards } from './SearchBlock'
import { SolverBlock } from './SolverBlock'
import { TableBlock, TaskTimingBlock } from './TableBlock'
import { TextBlock } from './TextBlock'

function resolve(log: CpSatLog, path: string): unknown {
  let cur: unknown = log
  for (const part of path.split('/').slice(1)) {
    if (cur === null || typeof cur !== 'object') return undefined
    cur = (cur as Record<string, unknown>)[part]
  }
  return cur
}

export function BlockCard({ blockRef, log, explanations }: { blockRef: BlockRef; log: CpSatLog; explanations: Explanations }) {
  const data = resolve(log, blockRef.path)
  if (data === undefined || data === null) return null
  const common = { blockRef, explanations }
  // A block kept verbatim (duplicate section, unknown text) must be shown as raw
  // lines even when its kind says 'solver' or 'response'.
  if (isUnparsed(blockRef)) return <TextBlock {...common} data={data as never} />
  switch (blockRef.kind) {
    case 'solver':
      return <SolverBlock {...common} data={log.solver!} />
    case 'initial_model':
      return <ModelBlock {...common} data={data as never} />
    case 'presolved_model':
      // The presolved model is shown against the model as it was handed in.
      return <ModelBlock {...common} data={data as never} initial={log.initial_model} />
    case 'presolve':
      return <PresolveBlock {...common} data={log.presolve!} />
    case 'presolve_summary':
      return <PresolveSummaryBlock {...common} data={log.presolve_summary!} />
    case 'search':
      // Two cards: the portfolio CP-SAT started and the progress it then made.
      return <SearchCards {...common} data={log.search!} />
    case 'task_timing':
      return <TaskTimingBlock {...common} data={log.stats.task_timing!} />
    case 'table':
      return <TableBlock {...common} data={data as never} />
    case 'response':
      return <ResponseBlock {...common} data={log.response!} />
    default:
      return <TextBlock {...common} data={data as never} />
  }
}
