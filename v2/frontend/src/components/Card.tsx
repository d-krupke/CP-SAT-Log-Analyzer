/**
 * Section card of the analysis panel. Anchors to a block of the log: clicking
 * the title bar collapses or expands the card (expanding also scrolls the log
 * to the section), the `L12-34` badge jumps to the section without collapsing,
 * and when a log line inside the block is selected the card is highlighted and
 * scrolled into view.
 *
 * `owns` exists for the two cards that share one log block (portfolio and
 * search progress): it says which part of the block this card is responsible
 * for, so only one of them lights up for a given line.
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
  owns?: LineSpan
}

export function Card({ kind, title, span, path, explanation, children, collapsed = false, owns }: Props) {
  const { selection, block, select } = useSelection()
  const [open, setOpen] = useState(!collapsed)
  const ref = useRef<HTMLElement>(null)
  const line = selection.line
  const mine = owns === undefined || (line !== null && owns.start <= line && line <= owns.end)
  const active = path !== undefined && block !== null && block.path === path && mine

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
        title={open ? 'Click to collapse' : 'Click to expand'}
        onClick={() => {
          // Expanding is also a "show me this" gesture; collapsing must not move the log.
          if (!open && span) select(span.start, 'panel')
          setOpen(!open)
        }}
      >
        <h2>{title}</h2>
        {span && (
          <span
            className="lines"
            title="Click to show this section in the log"
            onClick={(e) => {
              e.stopPropagation()
              select(span.start, 'panel')
            }}
          >
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
