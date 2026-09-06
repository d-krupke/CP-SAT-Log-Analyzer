import { Anchor, Card } from '../Card'
import { cardCollapsedByDefault } from '../../state/expansion'
import { formatNumber, useSelection } from '../../state/selection'
import type { BlockRef, Explanations, PresolveLog, PresolveSummary } from '../../types'

export function PresolveBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: PresolveLog; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const total = data.steps.reduce((a, s) => a + (s.time_s ?? 0), 0)
  const byName = new Map<string, { time: number; n: number }>()
  for (const s of data.steps) {
    const e = byName.get(s.name) ?? { time: 0, n: 0 }
    e.time += s.time_s ?? 0
    e.n += 1
    byName.set(s.name, e)
  }
  const top = [...byName.entries()].sort((a, b) => b[1].time - a[1].time).slice(0, 5)
  return (
    <Card kind="presolve" title="Presolve" span={blockRef.span} path={blockRef.path} explanation={explanations.blocks.presolve} collapsed={cardCollapsedByDefault('presolve')}>
      <div className="kv">
        {data.start_time && (
          <>
            <Anchor line={data.start_time.line}>started at</Anchor>
            <Anchor line={data.start_time.line}>{data.start_time.value.toFixed(2)} s</Anchor>
          </>
        )}
        <div>steps</div>
        <div>
          {data.steps.length} (total {total.toFixed(2)} s)
        </div>
        {top.length > 0 && (
          <>
            <div>most expensive</div>
            <div>{top.map(([n, e]) => `${n} (${e.time.toFixed(2)} s, ×${e.n})`).join(', ')}</div>
          </>
        )}
      </div>
      {data.messages.length > 0 && (
        <pre className="raw" style={{ marginTop: 6 }}>
          {data.messages.map((l) => (
            <div key={l.line} className={selection.line === l.line ? 'selected' : ''} onClick={() => select(l.line, 'panel')}>
              <Anchor line={l.line}>{l.value}</Anchor>
            </div>
          ))}
        </pre>
      )}
      <details>
        <summary>All presolve steps ({data.steps.length})</summary>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th title="Wall time of this pass">time [s]</th>
                <th title="Deterministic time of this pass">dtime</th>
                <th title="Presolve rule">rule</th>
                <th style={{ textAlign: 'left' }}>counters</th>
              </tr>
            </thead>
            <tbody>
              {data.steps.map((s) => (
                <tr key={s.line} className={selection.line === s.line ? 'selected' : ''} onClick={() => select(s.line, 'panel')}>
                  <td className="num">
                    <Anchor line={s.line}>{s.time_s !== null ? s.time_s.toExponential(2) : ''}</Anchor>
                  </td>
                  <td className="num">
                    <Anchor line={s.line}>{s.dtime_s !== null ? s.dtime_s.toExponential(2) : ''}</Anchor>
                  </td>
                  <td>
                    <Anchor line={s.line}>{s.name}</Anchor>
                  </td>
                  <td style={{ textAlign: 'left', whiteSpace: 'normal' }} className="muted">
                    <Anchor line={s.line}>
                      {Object.keys(s.stats).length > 0
                        ? Object.entries(s.stats).map(([k, v]) => `${k}=${formatNumber(v)}`).join('  ')
                        : s.details}
                    </Anchor>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      {data.symmetry_lines.length + data.sat_presolve_lines.length > 0 && (
        <details>
          <summary>Symmetry and SAT presolve lines</summary>
          <pre className="raw">
            {[...data.symmetry_lines, ...data.sat_presolve_lines]
              .sort((a, b) => a.line - b.line)
              .map((l) => (
                <div key={l.line} className={selection.line === l.line ? 'selected' : ''} onClick={() => select(l.line, 'panel')}>
                  <Anchor line={l.line}>{l.value}</Anchor>
                </div>
              ))}
          </pre>
        </details>
      )}
    </Card>
  )
}

export function PresolveSummaryBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: PresolveSummary; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const rules = [...data.rules].sort((a, b) => b.count - a.count)
  return (
    <Card kind="presolve_summary" title="Presolve summary" span={blockRef.span} path={blockRef.path} explanation={explanations.blocks.presolve_summary} collapsed={cardCollapsedByDefault('presolve_summary')}>
      <div className="kv">
        {data.affine_relations && (
          <>
            <Anchor line={data.affine_relations.line}>affine relations</Anchor>
            <Anchor line={data.affine_relations.line}>{formatNumber(data.affine_relations.value)}</Anchor>
          </>
        )}
        {data.closed_by_presolve && (
          <>
            <Anchor line={data.closed_by_presolve.line}>closed by presolve</Anchor>
            <Anchor line={data.closed_by_presolve.line}>yes</Anchor>
          </>
        )}
      </div>
      <details>
        <summary>Rules applied ({rules.length})</summary>
        <div className="tbl-wrap">
          <table className="tbl">
            <tbody>
              {rules.map((r) => (
                <tr key={r.line} className={selection.line === r.line ? 'selected' : ''} onClick={() => select(r.line, 'panel')}>
                  <td>
                    <Anchor line={r.line}>{r.rule}</Anchor>
                  </td>
                  <td className="num">
                    <Anchor line={r.line}>{formatNumber(r.count)}</Anchor>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Card>
  )
}
