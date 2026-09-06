/**
 * Right panel: the raw log with line numbers. Each line is coloured by the
 * block it belongs to, clicking selects it (the analysis panel then scrolls to
 * the matching card), and selections made in the analysis panel scroll here.
 * Lines the parser could not use are marked (`k-unparsed`) so a broken or
 * foreign log is visible as such at a glance.
 */
import { memo, useEffect, useMemo, useRef } from 'react'
import { blockClass, useSelection } from '../state/selection'
import type { CpSatLog } from '../types'

interface Props {
  lines: string[]
  log: CpSatLog
}

export function LogView({ lines, log }: Props) {
  const { selection, block, select } = useSelection()
  const ref = useRef<HTMLDivElement>(null)

  const kinds = useMemo(() => {
    const arr = new Array<string>(lines.length + 2).fill('')
    for (const b of log.blocks) {
      const cls = blockClass(b)
      for (let i = b.span.start; i <= b.span.end && i < arr.length; i++) arr[i] = cls
    }
    return arr
  }, [lines.length, log.blocks])

  useEffect(() => {
    if (selection.source !== 'panel' || selection.line === null) return
    const el = ref.current?.querySelector<HTMLElement>(`[data-line="${selection.line}"]`)
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [selection])

  return (
    <div className="logview" ref={ref}>
      {lines.map((text, i) => (
        <Line
          key={i + 1}
          no={i + 1}
          text={text}
          cls={kinds[i + 1]}
          selected={selection.line === i + 1}
          inBlock={block !== null && block.span.start <= i + 1 && i + 1 <= block.span.end}
          onClick={select}
        />
      ))}
    </div>
  )
}

interface LineProps {
  no: number
  text: string
  cls: string
  selected: boolean
  inBlock: boolean
  onClick: (line: number, source: 'log') => void
}

const Line = memo(function Line({ no, text, cls, selected, inBlock, onClick }: LineProps) {
  const className = `logline ${cls}${selected ? ' selected' : inBlock ? ' in-block' : ''}${text === '' ? ' blank' : ''}`
  return (
    <div className={className} data-line={no} onClick={() => text !== '' && onClick(no, 'log')}>
      <span className="no">{no}</span>
      <span className="txt">{text || ' '}</span>
    </div>
  )
})
