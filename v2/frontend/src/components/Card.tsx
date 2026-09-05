/**
 * Section card of the analysis panel. Anchors to a block of the log:
 * clicking the header selects the block's first line (the log scrolls there),
 * and when a log line inside the block is selected the card is highlighted and
 * scrolled into view.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { kindClass, useSelection } from '../state/selection'
import { Md } from './Md'
import type { LineSpan } from '../types'

interface Props {
  kind: string
  title: string
  span?: LineSpan
  path?: string
  explanation?: string
  children: ReactNode
  collapsed?: boolean
}

export function Card({ kind, title, span, path, explanation, children, collapsed = false }: Props) {
  const { selection, block, select } = useSelection()
  const [manualOpen, setOpen] = useState(!collapsed)
  const ref = useRef<HTMLElement>(null)
  const active = path !== undefined && block !== null && block.path === path
  const open = manualOpen

  useEffect(() => {
    if (active && selection.source === 'log') {
      setOpen(true)
      // Scroll to the exact row/value if one is highlighted, else to the card itself.
      const target = ref.current?.querySelector<HTMLElement>('.selected') ?? ref.current
      target?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [active, selection])

  return (
    <section className={`card ${kindClass(kind)}${active ? ' active' : ''}`} ref={ref}>
      <header
        title={span ? 'Click to show this section in the log' : undefined}
        onClick={() => {
          if (span) select(span.start, 'panel')
          if (!open) setOpen(true)
        }}
      >
        <h2>{title}</h2>
        {span && (
          <span className="lines" title="Log lines">
            {span.start === span.end ? `L${span.start}` : `L${span.start}–${span.end}`}
          </span>
        )}
        <button
          className="toggle"
          title={open ? 'Collapse' : 'Expand'}
          onClick={(e) => {
            e.stopPropagation()
            setOpen(!open)
          }}
        >
          {open ? '▾' : '▸'}
        </button>
      </header>
      {open && (
        <div className="body">
          {explanation && <Md className="explain" text={explanation} />}
          {children}
        </div>
      )}
    </section>
  )
}

/** A clickable value that selects its log line. */
export function Anchor({ line, children, className }: { line: number | null | undefined; children: ReactNode; className?: string }) {
  const { selection, select } = useSelection()
  const selected = line !== null && line !== undefined && selection.line === line
  return (
    <span
      className={`${className ?? ''}${selected ? ' selected' : ''}`}
      style={{ cursor: line ? 'pointer' : undefined }}
      onClick={() => line && select(line, 'panel')}
      title={line ? `Log line ${line}` : undefined}
    >
      {children}
    </span>
  )
}
