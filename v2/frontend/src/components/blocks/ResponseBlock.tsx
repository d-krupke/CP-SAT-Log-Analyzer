import { Anchor, Card } from '../Card'
import { formatNumber, useSelection } from '../../state/selection'
import type { BlockRef, Explanations, Loc, ResponseSummary } from '../../types'

const FIELDS: (keyof ResponseSummary)[] = [
  'status', 'objective', 'best_bound', 'integers', 'booleans', 'conflicts', 'branches', 'propagations',
  'integer_propagations', 'restarts', 'lp_iterations', 'walltime', 'usertime', 'deterministic_time',
  'gap_integral', 'solution_fingerprint', 'lrat_status',
]

export function ResponseBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: ResponseSummary; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const rows: { key: string; loc: Loc<string | number> }[] = []
  for (const f of FIELDS) {
    const loc = data[f] as Loc<string | number> | null
    if (loc) rows.push({ key: f, loc })
  }
  for (const [k, loc] of Object.entries(data.extra)) rows.push({ key: k, loc })
  return (
    <Card kind="response" title="Response summary" span={blockRef.span} path={blockRef.path} explanation={explanations.blocks.response}>
      <div className="tbl-wrap">
        <table className="tbl">
          <tbody>
            {rows.map(({ key, loc }) => (
              <tr key={key} className={selection.line === loc.line ? 'selected' : ''} onClick={() => select(loc.line, 'panel')}>
                <td>
                  <Anchor line={loc.line}>{key}</Anchor>
                </td>
                <td className="num">
                  <Anchor line={loc.line}>{formatNumber(loc.value)}</Anchor>
                </td>
                <td style={{ textAlign: 'left', whiteSpace: 'normal' }} className="muted">
                  {explanations.response_fields[key] ?? ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
