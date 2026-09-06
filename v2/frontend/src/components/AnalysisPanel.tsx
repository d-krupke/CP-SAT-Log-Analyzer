/**
 * Left panel: overview, progress plot, parameters, then one card per log
 * section in log order (resolved through the block index of the parsed log).
 * The cards are grouped by phase of the solve (see `state/phases.ts`) with a
 * header in front of each group.
 */
import { Fragment } from 'react'
import { Card } from './Card'
import { HintCard } from './HintCard'
import { Overview } from './Overview'
import { ParametersCard } from './ParametersCard'
import { ProgressPlot } from './ProgressPlot'
import { SubsolversCard } from './SubsolversCard'
import { BlockCard } from './blocks/BlockCard'
import { PHASE_LABELS, phaseOf } from '../state/phases'
import type { Explanations, ParseResult } from '../types'

export function AnalysisPanel({ result, explanations }: { result: ParseResult; explanations: Explanations }) {
  const { log, analysis } = result
  const seen = new Set<string>()
  // Phases already introduced by a header. A section that turns up out of order
  // joins the group it appears in instead of repeating its header further down.
  const headed = new Set(['summary'])
  const hasProgress = analysis.progress.solutions.length > 0 || analysis.progress.bounds.length > 0
  return (
    <div className="panel">
      <h2 className="phase">{PHASE_LABELS.summary}</h2>
      <Overview analysis={analysis} />
      {hasProgress && (
        <Card
          kind="search"
          title="Progress over time"
          path="/progress"
          explanation={explanations.cards.progress}
        >
          <ProgressPlot progress={analysis.progress} />
        </Card>
      )}
      {/* Without a solver header there is no `Parameters:` line, so "no overrides" would be a lie. */}
      {log.solver && (
        <ParametersCard params={analysis.parameters} solver={log.solver} explanations={explanations} />
      )}
      <HintCard hint={analysis.hint} explanations={explanations} />
      {log.warnings.length > 0 && (
        <Card kind="message" title="Parser warnings" path="/warnings">
          <ul>
            {log.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Card>
      )}
      {log.blocks.map((ref) => {
        if (seen.has(ref.path)) return null
        seen.add(ref.path)
        const phase = phaseOf(ref)
        const header = phase !== null && !headed.has(phase) ? phase : null
        if (header !== null) headed.add(header)
        return (
          <Fragment key={ref.path}>
            {header !== null && <h2 className="phase">{PHASE_LABELS[header]}</h2>}
            <BlockCard blockRef={ref} log={log} explanations={explanations} />
            {ref.path === '/search' && <SubsolversCard items={analysis.subsolvers} explanations={explanations} />}
          </Fragment>
        )
      })}
    </div>
  )
}
