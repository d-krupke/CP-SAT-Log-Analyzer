/** Comments, messages and unparsed blocks: verbatim lines, each clickable. */
import { Anchor, Card } from '../Card'
import { useSelection } from '../../state/selection'
import type { BlockRef, Explanations, LinesBlock } from '../../types'


export function TextBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: LinesBlock; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const title = blockRef.kind === 'comment' ? 'Comment' : blockRef.kind === 'message' ? `Message: ${data.message_kind ?? ''}` : 'Unrecognised section'
  const explanation = (data.message_kind && explanations.messages[data.message_kind]) || explanations.blocks[blockRef.kind]
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

