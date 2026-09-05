/** Explains every parameter the user overrode (the Parameters: line). */
import { Card } from './Card'
import { Md } from './Md'
import type { ParameterInfo, SolverInfo } from '../types'

function fmtValue(v: unknown): string {
  if (typeof v === 'string') return v
  return JSON.stringify(v)
}

export function ParametersCard({ params, solver }: { params: ParameterInfo[]; solver: SolverInfo | null }) {
  const line = solver?.parameters?.line
  return (
    <Card
      kind="solver"
      title={`Overridden parameters (${params.length})`}
      span={line ? { start: line, end: line } : undefined}
      path="/parameters"
      explanation={
        params.length === 0
          ? 'No parameter differs from its default. Usually a good sign: the default portfolio is hard to beat.'
          : 'CP-SAT prints only parameters that differ from their defaults. Each one is documented below (from `sat_parameters.proto`) with advice on typical pitfalls. Parameters that change the behaviour of *all* workers reduce the diversity of the portfolio and are the usual cause of unexpectedly slow solves.'
      }
    >
      {params.map((p) => (
        <div className="param" key={p.name}>
          <div className="head">
            <code>{p.name}</code>
            <span>= {fmtValue(p.value)}</span>
            {p.default !== null && <span className="small">(default {p.default})</span>}
            {p.section && <span className="tag">{p.section}</span>}
            {!p.known && <span className="tag warn">unknown</span>}
            {p.warning && <span className="tag warn">check</span>}
          </div>
          {p.advice && <Md className="advice" text={p.advice} />}
          {p.warning && <div className="warning">⚠ {p.warning}</div>}
          {p.doc && (
            <details>
              <summary>Documentation from sat_parameters.proto</summary>
              <div className="doc">{p.doc}</div>
              {Object.keys(p.enum_values).length > 0 && (
                <ul className="coldocs">
                  {Object.entries(p.enum_values).map(([k, d]) => (
                    <li key={k}>
                      <code>{k}</code> {d}
                    </li>
                  ))}
                </ul>
              )}
            </details>
          )}
        </div>
      ))}
    </Card>
  )
}
