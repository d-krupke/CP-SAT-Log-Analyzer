import { Anchor, Card } from '../Card'
import type { BlockRef, Explanations, SolverInfo } from '../../types'

export function SolverBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: SolverInfo; explanations: Explanations }) {
  return (
    <Card kind="solver" title="Solver" span={blockRef.span} path={blockRef.path} explanation={explanations.blocks.solver}>
      <div className="kv">
        <Anchor line={data.version?.line}>version</Anchor>
        <Anchor line={data.version?.line}>{data.version?.value ?? '?'}</Anchor>
        {data.num_workers && (
          <>
            <Anchor line={data.num_workers.line}>workers</Anchor>
            <Anchor line={data.num_workers.line}>{data.num_workers.value} (chosen automatically)</Anchor>
          </>
        )}
        {data.parameters && (
          <>
            <Anchor line={data.parameters.line}>parameters</Anchor>
            <Anchor line={data.parameters.line}>
              <code>{data.parameters_raw || '(defaults)'}</code>
            </Anchor>
          </>
        )}
        {data.other_lines.map((l) => (
          <Anchor key={l.line} line={l.line} className="span2">
            {l.value}
          </Anchor>
        ))}
      </div>
    </Card>
  )
}
