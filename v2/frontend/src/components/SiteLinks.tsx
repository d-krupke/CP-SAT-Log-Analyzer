/**
 * The deployment-specific links: "Report issue" in the top bar, and whatever
 * legal pages the operator configured (`GET /api/site`, see
 * v2/backend/app/site.py).
 *
 * Created 2026-09 for hosting the analyzer publicly. Two exports because the
 * two belong in different places: reporting a log the analyzer mishandles is
 * something we *want* people to do, so it sits with the other top-bar links;
 * an imprint and a privacy statement have to be on every page but are not part
 * of reading a log, so they sit small and muted in the bottom right corner.
 *
 * A page given as a URL links out; a page given as a Markdown file (mounted per
 * deployment) opens in the dialog below.
 */
import { useEffect, useState } from 'react'
import { Md } from './Md'
import type { SiteConfig, SitePage } from '../types'

export function IssueLink({ site }: { site: SiteConfig | null }) {
  if (!site) return null
  return (
    <a className="issue" href={site.issue_url} target="_blank" rel="noreferrer" title="Report a problem, or a log the analyzer gets wrong">
      Report issue
    </a>
  )
}

export function LegalLinks({ site }: { site: SiteConfig | null }) {
  const [open, setOpen] = useState<SitePage | null>(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  if (!site || site.pages.length === 0) return null
  return (
    <>
      <div className="sitelinks">
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
      </div>
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
