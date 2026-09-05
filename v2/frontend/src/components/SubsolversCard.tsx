/** Who found what: per-subsolver solution and bound contributions, with the worker's role. */
import { Fragment, useState } from 'react'
import { Card } from './Card'
import { Md } from './Md'
import { subsolverDoc } from '../knowledge'
import { useSelection } from '../state/selection'
import type { Explanations, SubsolverContribution } from '../types'

export function SubsolversCard({ items, explanations }: { items: SubsolverContribution[]; explanations: Explanations }) {
  const { select } = useSelection()
  const [open, setOpen] = useState<string | null>(null)
  if (items.length === 0) return null
  return (
    <Card kind="search" title="Subsolver contributions" path="/subsolvers" explanation={explanations.cards.subsolvers} collapsed>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Subsolver</th>
              <th>Role</th>
              <th>Solutions</th>
              <th>Bounds</th>
              <th>First solution</th>
              <th style={{ textAlign: 'left' }}>What it does</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => {
              const doc = subsolverDoc(explanations, s.name)
              const details = doc?.details ?? ''
              const expanded = open === s.name
              return (
                <Fragment key={s.name}>
                  <tr onClick={() => setOpen(expanded ? null : s.name)} style={{ cursor: details ? 'pointer' : undefined }}>
                    <td>{s.name}</td>
                    <td>
                      {s.role && (
                        <span className="tag" title={explanations.subsolver_roles[s.role] ?? ''}>
                          {s.role.replace('_', ' ')}
                        </span>
                      )}
                    </td>
                    <td className="num">{s.solutions}</td>
                    <td className="num">{s.bounds}</td>
                    <td className="num">{s.first_solution_time !== null ? `${s.first_solution_time.toFixed(2)} s` : ''}</td>
                    <td style={{ textAlign: 'left', whiteSpace: 'normal' }} className="muted">
                      {s.description ?? ''}
                      {details && <span className="small"> {expanded ? '▾' : '▸'}</span>}
                    </td>
                  </tr>
                  {expanded && details && (
                    <tr className="details-row">
                      <td colSpan={6} style={{ textAlign: 'left', whiteSpace: 'normal' }}>
                        <Md text={details} />
                        {s.best_solution_line && (
                          <button className="link" onClick={() => select(s.best_solution_line!, 'panel')}>
                            Show its best solution in the log
                          </button>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
