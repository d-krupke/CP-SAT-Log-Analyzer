/**
 * The deployment-specific links: "Report issue" in the top bar, and the footer
 * in the bottom right corner (`GET /api/site`, see v2/backend/app/site.py).
 *
 * Created 2026-09 for hosting the analyzer publicly. Two exports because the
 * two belong in different places: reporting a log the analyzer mishandles is
 * something we *want* people to do, so it sits with the other top-bar links;
 * the license and the operator's legal pages have to be reachable from every
 * page but are not part of reading a log, so they sit small and muted in the
 * corner.
 *
 * The license link is always there - it is a property of the software, not of
 * the deployment. The legal pages are the opposite: nothing is shown unless
 * this instance configured them. A page given as a URL links out; a page given
 * as a Markdown file (mounted per deployment) opens in the dialog below.
 */
import { useEffect, useState } from 'react'
import { Md } from './Md'
import type { SiteConfig, SitePage } from '../types'

const LICENSE_URL = 'https://github.com/d-krupke/CP-SAT-Log-Analyzer/blob/main/LICENSE'

export function IssueLink({ site }: { site: SiteConfig | null }) {
  if (!site) return null
  return (
    <a className="issue" href={site.issue_url} target="_blank" rel="noreferrer" title="Report a problem, or a log the analyzer gets wrong">
      Report issue
    </a>
  )
}

export function Footer({ site }: { site: SiteConfig | null }) {
  const [open, setOpen] = useState<SitePage | null>(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])
  return (
    <>
      <div className="sitelinks">
        <a href={LICENSE_URL} target="_blank" rel="noreferrer" title="Free and open source; see the repository">
          MIT License
        </a>
        {site?.pages.map((page) =>
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
