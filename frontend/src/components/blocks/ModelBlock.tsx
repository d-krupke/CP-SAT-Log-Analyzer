import { Anchor, Card } from '../Card'
import { Section } from '../Section'
import { formatNumber, useSelection } from '../../state/selection'
import type { BlockRef, Explanations, ModelDescription } from '../../types'
import { constraintMix, domainMix } from '../../modelMix'
import { Delta, DomainSize, LevelTag, MixBar } from './ModelIndicators'


export function ModelBlock({ blockRef, data, initial, explanations }: { blockRef: BlockRef; data: ModelDescription; initial?: ModelDescription | null; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const total = data.constraints.reduce((a, c) => a + c.count, 0)
  // The presolved model is only interesting next to the one that was handed in, so
  // its counts are shown as `before -> after` instead of on their own.
  const before = data.stage === 'presolved' && initial ? initial : null
  const beforeConstraints = before ? before.constraints.reduce((a, c) => a + c.count, 0) : 0
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
              {before?.num_variables && <span className="was">{formatNumber(before.num_variables.value)} → </span>}
              {formatNumber(data.num_variables.value)}
              {data.num_bools_in_objective !== null && ` (${formatNumber(data.num_bools_in_objective.value)} Booleans in objective`}
              {data.num_ints_in_objective !== null && `, ${formatNumber(data.num_ints_in_objective.value)} integers in objective`}
              {data.num_bools_in_objective !== null && ')'}
              {data.num_primary_variables !== null && ` · ${formatNumber(data.num_primary_variables.value)} primary`}
              {before?.num_variables && <Delta from={before.num_variables.value} to={data.num_variables.value} />}
            </Anchor>
          </>
        )}
        <div>constraints</div>
        <div>
          {before && <span className="was">{formatNumber(beforeConstraints)} → </span>}
          {formatNumber(total)}
          {before && <Delta from={beforeConstraints} to={total} />}
        </div>
      </div>
      <MixBar title="Variables by domain size" segments={domainMix(data, explanations)} />
      <MixBar title="Constraints by complexity" segments={constraintMix(data, explanations)} />
      {data.domains.length > 0 && (
        <Section title="Variable domains" count={data.domains.length}>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>count</th>
                  <th style={{ textAlign: 'left' }}>size</th>
                  <th style={{ textAlign: 'left' }}>domain</th>
                </tr>
              </thead>
              <tbody>
                {data.domains.map((d) => (
                  <tr key={d.line} className={selection.line === d.line ? 'selected' : ''} onClick={() => select(d.line, 'panel')}>
                    <td>
                      <Anchor line={d.line}>{formatNumber(d.count)}</Anchor>
                    </td>
                    <td style={{ textAlign: 'left' }}>
                      <DomainSize d={d} ex={explanations} />
                    </td>
                    <td style={{ textAlign: 'left', whiteSpace: 'normal' }}>
                      <Anchor line={d.line}>{d.description}</Anchor>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
      {data.constraints.length > 0 && (
        <Section title="Constraints" count={data.constraints.length}>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>kind</th>
                  <th>count</th>
                  <th style={{ textAlign: 'left' }}>complexity</th>
                  <th style={{ textAlign: 'left' }}>details</th>
                </tr>
              </thead>
              <tbody>
                {data.constraints.map((c) => (
                  <tr key={c.line} className={selection.line === c.line ? 'selected' : ''} onClick={() => select(c.line, 'panel')} title={explanations.constraints[c.name]?.summary ?? ''}>
                    <td>
                      <Anchor line={c.line}>{c.name}</Anchor>
                    </td>
                    <td className="num">
                      <Anchor line={c.line}>{formatNumber(c.count)}</Anchor>
                    </td>
                    <td style={{ textAlign: 'left' }}>
                      <LevelTag level={explanations.constraint_complexity[explanations.constraints[c.name]?.complexity ?? '']} />
                    </td>
                    <td style={{ textAlign: 'left' }} className="muted">
                      {explanations.constraints[c.name]?.summary ?? ''}
                      {Object.entries(c.details).length > 0 && (
                        <> · {Object.entries(c.details).map(([k, v]) => `#${k}: ${formatNumber(v)}`).join(', ')}</>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}
      {data.search_strategies.length > 0 && (
        <Section title="Search strategies" count={data.search_strategies.length}>
          <pre className="raw raw-wrap">
            {data.search_strategies.map((l) => (
              <Anchor key={l.line} line={l.line}>
                <div>{l.value}</div>
              </Anchor>
            ))}
          </pre>
        </Section>
      )}
      {data.other_lines.length > 0 && (
        <Section title="Other lines" count={data.other_lines.length}>
          <pre className="raw raw-wrap">
            {data.other_lines.map((l) => (
              <div key={l.line} className={selection.line === l.line ? 'selected' : ''} onClick={() => select(l.line, 'panel')}>
                <Anchor line={l.line}>{l.value}</Anchor>
              </div>
            ))}
          </pre>
        </Section>
      )}
    </Card>
  )
}
