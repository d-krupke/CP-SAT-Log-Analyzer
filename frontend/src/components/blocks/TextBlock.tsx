/** Comments, messages and unparsed blocks: verbatim lines, each clickable. */
import { Anchor, Card } from '../Card'
import { cardCollapsedByDefault } from '../../state/expansion'
import { isUnparsed, useSelection } from '../../state/selection'
import type { BlockRef, Explanations, LinesBlock } from '../../types'


export function TextBlock({ blockRef, data, explanations }: { blockRef: BlockRef; data: LinesBlock; explanations: Explanations }) {
  const { selection, select } = useSelection()
  const unparsed = isUnparsed(blockRef)
  const title = unparsed
    ? `Unrecognized section (${data.lines.length} line${data.lines.length === 1 ? '' : 's'})`
    : blockRef.kind === 'comment'
      ? 'Comment'
      : `Message: ${(data.message_kind ?? '').replace(/_/g, ' ')}`
  const explanation = unparsed
    ? explanations.blocks.unknown
    : (data.message_kind && explanations.messages[data.message_kind]) || explanations.blocks[blockRef.kind]
  return (
    <Card kind={unparsed ? 'unparsed' : blockRef.kind} title={title} span={blockRef.span} path={blockRef.path} explanation={explanation} collapsed={cardCollapsedByDefault(blockRef.kind)}>
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
