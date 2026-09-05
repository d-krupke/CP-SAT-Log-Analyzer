/** Comments, messages and unparsed blocks: verbatim lines, each clickable. */
import { Anchor, Card } from '../Card'
import { useSelection } from '../../state/selection'
import type { BlockRef, Explanations, LinesBlock } from '../../types'

const MESSAGE_DOCS: Record<string, string> = {
  closed_by_presolve: 'Presolve proved optimality or infeasibility, so no search ran.',
  gap_limit_reached: 'The solver stopped because the objective/bound gap fell below `relative_gap_limit` / `absolute_gap_limit`; the status is still FEASIBLE.',
  loading_model: 'The presolved model is being loaded into the workers.',
  hint: 'Information about the solution hint (whether it was complete/feasible and which objective it had).',
  infeasible: 'The model was proven infeasible.',
  legacy_subsolver_stats: 'Per-worker statistics dump of an old OR-Tools version (newer versions print tables instead).',
}

export function TextBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: LinesBlock; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const title = blockRef.kind === 'comment' ? 'Comment' : blockRef.kind === 'message' ? `Message: ${data.message_kind ?? ''}` : 'Unrecognised section'
  const explanation = (data.message_kind && MESSAGE_DOCS[data.message_kind]) || explanations.blocks[blockRef.kind]
  return (
    <Card kind={blockRef.kind} title={title} span={blockRef.span} path={blockRef.path} explanation={explanation} collapsed={blockRef.kind === 'comment'}>
      <pre className="raw">
        {data.lines.map((l) => (
          <div key={l.line} className={selection.line === l.line ? 'selected' : ''} onClick={() => select(l.line, 'panel')}>
            <Anchor line={l.line}>{l.value}</Anchor>
          </div>
        ))}
      </pre>
    </Card>
  )
}

