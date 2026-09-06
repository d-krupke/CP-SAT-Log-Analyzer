/**
 * The deployment-specific links in the top bar: "Report issue" plus whatever
 * legal pages the operator configured (`GET /api/site`, see
 * v2/backend/app/site.py).
 *
 * Created 2026-09 for hosting the analyzer publicly: an imprint and a privacy
 * statement are required of the operator of a public site, but they are not
 * part of the project, so they are injected per deployment and simply absent
 * otherwise. A page given as a URL links out; a page given as a Markdown file
 * opens in a dialog here.
 */
import { useEffect, useState } from 'react'
import { Md } from './Md'
import type { SiteConfig, SitePage } from '../types'

export function SiteLinks({ site }: { site: SiteConfig | null }) {
  const [open, setOpen] = useState<SitePage | null>(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  if (!site) return null
  return (
    <>
      <a href={site.issue_url} target="_blank" rel="noreferrer" title="Report a problem or a log the parser mishandles">
        Report issue
      </a>
      {site.pages.map((page) =>
        page.url ? (
          <a key={page.key} href={page.url} target="_blank" rel="noreferrer">
            {page.label}
          </a>
        ) : (
          <button key={page.key} className="linky" onClick={() => setOpen(page)}>
            {page.label}
          </button>
        ),
      )}
      {open && (
        <div className="modal-backdrop" onClick={() => setOpen(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={open.label}>
            <header>
              <h2>{open.label}</h2>
              <button onClick={() => setOpen(null)} title="Close (Esc)">
                ✕
              </button>
            </header>
            <Md text={open.markdown ?? ''} />
          </div>
        </div>
      )}
    </>
  )
}
