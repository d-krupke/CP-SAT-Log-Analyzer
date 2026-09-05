/** Who found what: per-subsolver solution and bound contributions. */
import { Card } from './Card'
import { useSelection } from '../state/selection'
import type { SubsolverContribution } from '../types'

export function SubsolversCard({ items }: { items: SubsolverContribution[] }) {
  const { select } = useSelection()
  if (items.length === 0) return null
  return (
    <Card
      kind="search"
      title="Subsolver contributions"
      path="/subsolvers"
      explanation="Which configuration of the portfolio produced the improving solutions and the bound improvements, combined from the search log and the final `Solutions`/`Objective bounds` tables. LNS workers typically dominate the solutions on large models; exact workers (`default_lp`, `max_lp`, `core`, ...) and the bound-focused workers dominate the bounds. Workers that contribute nothing are candidates for `ignore_subsolvers` only if you have many cores idle; otherwise they still share clauses and bounds."
      collapsed
    >
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Subsolver</th>
              <th>Solutions</th>
              <th>Bounds</th>
              <th>First solution</th>
              <th style={{ textAlign: 'left' }}>Role</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.name} onClick={() => s.best_solution_line && select(s.best_solution_line, 'panel')}>
                <td>{s.name}</td>
                <td className="num">{s.solutions}</td>
                <td className="num">{s.bounds}</td>
                <td className="num">{s.first_solution_time !== null ? `${s.first_solution_time.toFixed(2)} s` : ''}</td>
                <td style={{ textAlign: 'left', whiteSpace: 'normal' }} className="muted">
                  {s.description ?? ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
