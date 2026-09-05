/**
 * Left panel: overview, progress plot, parameters, then one card per log
 * section in log order (resolved through the block index of the parsed log).
 */
import { Fragment } from 'react'
import { Card } from './Card'
import { Overview } from './Overview'
import { ParametersCard } from './ParametersCard'
import { ProgressPlot } from './ProgressPlot'
import { SubsolversCard } from './SubsolversCard'
import { BlockCard } from './blocks/BlockCard'
import type { Explanations, ParseResult } from '../types'

export function AnalysisPanel({ result, explanations }: { result: ParseResult; explanations: Explanations }) {
  const { log, analysis } = result
  const seen = new Set<string>()
  const hasProgress = analysis.progress.solutions.length > 0 || analysis.progress.bounds.length > 0
  return (
    <div className="panel">
      <Overview analysis={analysis} />
      {hasProgress && (
        <Card
          kind="search"
          title="Search progress"
          path="/progress"
          explanation="Incumbent objective (`best:`) and proven bound (`next:[lb,ub]`) over time. A flat objective with a rising bound means the solver is proving; a flat bound with improving solutions means the relaxation is weak. Click a point to jump to its log line."
        >
          <ProgressPlot progress={analysis.progress} />
        </Card>
      )}
      <ParametersCard params={analysis.parameters} solver={log.solver} />
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
        return (
          <Fragment key={ref.path}>
            <BlockCard blockRef={ref} log={log} explanations={explanations} />
            {ref.path === '/search' && <SubsolversCard items={analysis.subsolvers} />}
          </Fragment>
        )
      })}
    </div>
  )
}
