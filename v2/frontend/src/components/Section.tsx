/**
 * A titled section inside a card.
 *
 * Added 2026-09: the parts of a card used to be `<details>` elements, which put a
 * second disclosure triangle inside an already collapsible card and shrank their
 * title to 12.5px muted text - a table announced more quietly than its own column
 * headers. A card is opened as a whole, so its parts only need a heading.
 *
 * Use it for the sections of one card (`Variable domains`, `All presolve steps`).
 * Keep `<details>` for per-item disclosure, where one row of many can be unfolded
 * (a parameter's proto documentation, a worker's description).
 */
import type { ReactNode } from 'react'

export function Section({ title, count, children }: { title: string; count?: number; children: ReactNode }) {
  return (
    <section className="sec">
      <h3 className="sec-title">
        {title}
        {count !== undefined && <span className="count">{count.toLocaleString('en-US')}</span>}
      </h3>
      {children}
    </section>
  )
}
