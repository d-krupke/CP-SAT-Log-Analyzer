/** Generic renderer for the final statistics tables and the task timing table. */
import { Anchor, Card } from '../Card'
import { Section } from '../Section'
import { subsolverDoc } from '../../knowledge'
import { tableCollapsedByDefault } from '../../state/expansion'
import { formatNumber, useSelection } from '../../state/selection'
import { tooltip } from '../../tooltip'
import type { BlockRef, Explanations, Table, TaskTimingTable } from '../../types'

export function TableBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: Table; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const doc = explanations.tables[data.table_id]
  const columns = data.columns.length > 0 ? data.columns : Object.keys(data.rows[0]?.values ?? {})
  return (
    <Card
      kind="table"
      // `title` is the header line verbatim and already carries the count, e.g. 'Solutions (219)'.
      title={data.title}
      span={blockRef.span}
      path={blockRef.path}
      explanation={doc?.summary ?? `**${data.title}.** Statistics table (no explanation available yet).`}
      collapsed={tableCollapsedByDefault(data.table_id)}
    >
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>{data.title.split(' (')[0]}</th>
              {columns.map((c) => (
                <th key={c} title={tooltip(doc?.columns[c])}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r, i) => (
              <tr key={`${r.line}-${i}`} className={selection.line === r.line ? 'selected' : ''} onClick={() => select(r.line, 'panel')} title={tooltip(subsolverDoc(explanations, r.name)?.summary)}>
                <td>
                  <Anchor line={r.line}>{r.name}</Anchor>
                </td>
                {columns.map((c) => (
                  <td key={c} className={r.values[c] === null || r.values[c] === undefined ? 'muted' : 'num'}>
                    <Anchor line={r.line}>{r.values[c] === undefined ? '' : r.values[c] === null ? '–' : formatNumber(r.values[c])}</Anchor>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {doc && Object.keys(doc.columns).length > 0 && (
        <Section title="Column reference">
          <ul className="coldocs">
            {columns.filter((c) => doc.columns[c]).map((c) => (
              <li key={c}>
                <code>{c}</code> {doc.columns[c]}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </Card>
  )
}

export function TaskTimingBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: TaskTimingTable; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const doc = explanations.tables.task_timing
  const cols = ['n', 'min', 'max', 'avg', 'dev', 'total'] as const
  return (
    <Card
      kind="task_timing"
      title="Task timing"
      summary={`${data.rows.length} tasks`}
      span={blockRef.span}
      path={blockRef.path}
      explanation={doc?.summary}
      collapsed={tableCollapsedByDefault('task_timing')}
    >
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Task</th>
              {cols.map((c) => (
                <th key={`w${c}`} title={tooltip(doc?.columns[c === 'total' ? 'time' : c])}>
                  {c === 'total' ? 'wall time' : c}
                </th>
              ))}
              {data.rows[0]?.deterministic && (
                <>
                  <th title="Number of runs (deterministic time half)">n</th>
                  <th title="Total deterministic time">dtime</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.line} className={selection.line === r.line ? 'selected' : ''} onClick={() => select(r.line, 'panel')} title={tooltip(subsolverDoc(explanations, r.name)?.summary)}>
                <td>
                  <Anchor line={r.line}>{r.name}</Anchor>
                </td>
                {cols.map((c) => (
                  <td key={c} className="num">
                    <Anchor line={r.line}>{c === 'n' ? r.wall.n : r.wall[c].toPrecision(4)}</Anchor>
                  </td>
                ))}
                {r.deterministic && (
                  <>
                    <td className="num">{r.deterministic.n}</td>
                    <td className="num">{r.deterministic.total.toPrecision(4)}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
