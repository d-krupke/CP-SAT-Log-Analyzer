import { Anchor, Card } from '../Card'
import { formatNumber, useSelection } from '../../state/selection'
import type { BlockRef, Explanations, ModelDescription } from '../../types'


export function ModelBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: ModelDescription; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const total = data.constraints.reduce((a, c) => a + c.count, 0)
  return (
    <Card
      kind={blockRef.kind}
      title={blockRef.title || (data.stage === 'initial' ? 'Initial model' : 'Presolved model')}
      span={blockRef.span}
      path={blockRef.path}
      explanation={explanations.blocks[blockRef.kind]}
    >
      <div className="kv">
        {data.problem_type && (
          <>
            <div>type</div>
            <div>{data.problem_type}</div>
          </>
        )}
        {data.num_variables && (
          <>
            <Anchor line={data.num_variables.line}>#Variables</Anchor>
            <Anchor line={data.num_variables.line}>
              {formatNumber(data.num_variables.value)}
              {data.num_bools_in_objective !== null && ` (${formatNumber(data.num_bools_in_objective.value)} Booleans in objective`}
              {data.num_ints_in_objective !== null && `, ${formatNumber(data.num_ints_in_objective.value)} integers in objective`}
              {data.num_bools_in_objective !== null && ')'}
              {data.num_primary_variables !== null && ` · ${formatNumber(data.num_primary_variables.value)} primary`}
            </Anchor>
          </>
        )}
        <div>constraints</div>
        <div>{formatNumber(total)}</div>
      </div>
      {data.domains.length > 0 && (
        <details open>
          <summary>Variable domains</summary>
          <div className="tbl-wrap">
            <table className="tbl">
              <tbody>
                {data.domains.map((d) => (
                  <tr key={d.line} className={selection.line === d.line ? 'selected' : ''} onClick={() => select(d.line, 'panel')}>
                    <td>
                      <Anchor line={d.line}>{formatNumber(d.count)}</Anchor>
                    </td>
                    <td style={{ textAlign: 'left', whiteSpace: 'normal' }}>
                      <Anchor line={d.line}>{d.description}</Anchor>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      {data.constraints.length > 0 && (
        <details open>
          <summary>Constraints</summary>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>kind</th>
                  <th>count</th>
                  <th style={{ textAlign: 'left' }}>details</th>
                </tr>
              </thead>
              <tbody>
                {data.constraints.map((c) => (
                  <tr key={c.line} className={selection.line === c.line ? 'selected' : ''} onClick={() => select(c.line, 'panel')} title={explanations.constraints[c.name] ?? ''}>
                    <td>
                      <Anchor line={c.line}>{c.name}</Anchor>
                    </td>
                    <td className="num">
                      <Anchor line={c.line}>{formatNumber(c.count)}</Anchor>
                    </td>
                    <td style={{ textAlign: 'left' }} className="muted">
                      {explanations.constraints[c.name] ?? ''}
                      {Object.entries(c.details).length > 0 && (
                        <> · {Object.entries(c.details).map(([k, v]) => `#${k}: ${formatNumber(v)}`).join(', ')}</>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      {data.search_strategies.length > 0 && (
        <details>
          <summary>Search strategies ({data.search_strategies.length})</summary>
          <pre className="raw">
            {data.search_strategies.map((l) => (
              <Anchor key={l.line} line={l.line}>
                <div>{l.value}</div>
              </Anchor>
            ))}
          </pre>
        </details>
      )}
      {data.other_lines.length > 0 && (
        <pre className="raw">
          {data.other_lines.map((l) => (
            <div key={l.line} className={selection.line === l.line ? 'selected' : ''} onClick={() => select(l.line, 'panel')}>
              <Anchor line={l.line}>{l.value}</Anchor>
            </div>
          ))}
        </pre>
      )}
    </Card>
  )
}
