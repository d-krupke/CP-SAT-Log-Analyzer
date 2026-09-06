/**
 * "Solution hint" card: what the log says about the hint the caller passed in.
 *
 * Added 2026-09. The hint is the one piece of the solve that comes from the user,
 * and its fate is easy to miss: CP-SAT states it in a single line somewhere in the
 * presolve output, and when the hint is actually taken it says nothing at all and
 * instead lists a solution found by the worker `complete_hint`. The card is only
 * rendered when the log carries hint evidence (`analysis.hint.notes` or that
 * solution), including the vacuous case where the hint line appears without a hint.
 */
import { Anchor, Card } from './Card'
import { useSelection } from '../state/selection'
import type { Explanations, HintReport } from '../types'

const STATUS: Record<string, { label: string; level: string }> = {
  accepted: { label: 'complete and feasible', level: 'good' },
  infeasible: { label: 'complete but infeasible', level: 'warn' },
  incomplete: { label: 'incomplete', level: 'info' },
  outside_domain: { label: 'outside the variable domains', level: 'warn' },
  breaks_assumptions: { label: 'breaks the assumptions', level: 'warn' },
  ignored: { label: 'ignored', level: 'info' },
  debug_only: { label: 'used as debug solution only', level: 'info' },
  other: { label: 'unrecognized message', level: 'info' },
  vacuous: { label: 'no hint was given', level: 'info' },
  none: { label: 'no hint', level: 'info' },
}

export function HintCard({ hint, explanations }: { hint: HintReport; explanations: Explanations }) {
  const { select } = useSelection()
  if (hint.notes.length === 0 && !hint.used_as_first_solution) return null
  const status = STATUS[hint.status] ?? STATUS.none
  return (
    <Card kind="message" title="Solution hint" path="/hint" explanation={explanations.cards.hint}>
      <div className="kv">
        <div>hint</div>
        <div>
          <span className={`tag ${status.level}`}>{status.label}</span>
        </div>
        {hint.hinted !== null && hint.active !== null && (
          <>
            <div>hinted</div>
            <div>
              {hint.hinted} of {hint.active} non-fixed variables
            </div>
          </>
        )}
        {hint.objective !== null && (
          <>
            <div>objective</div>
            <div>{hint.objective}</div>
          </>
        )}
        {hint.fixed_variables !== null && (
          <>
            <div>fixed to hint</div>
            <div>
              {hint.fixed_variables} variables (<code>fix_variables_to_their_hinted_value</code>)
            </div>
          </>
        )}
        <div>used as solution</div>
        <div>
          {hint.first_solution_line !== null ? (
            <Anchor line={hint.first_solution_line}>yes, as the first solution (complete_hint)</Anchor>
          ) : (
            'no'
          )}
        </div>
      </div>
      <pre className="raw">
        {hint.notes.map((n) => (
          <div key={n.line} onClick={() => select(n.line, 'panel')}>
            <Anchor line={n.line}>{n.text}</Anchor>
          </div>
        ))}
      </pre>
    </Card>
  )
}
