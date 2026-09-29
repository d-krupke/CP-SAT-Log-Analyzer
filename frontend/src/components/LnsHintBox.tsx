/**
 * "Give LNS more threads": shown in the Portfolio ranking card when LNS and local search
 * delivered at least half of the objective progress (backend: app/lns_hint.py).
 *
 * Added 2026-09-28 from Phases G and H of the portfolio-importance study. The text with the
 * run's numbers comes from the backend; title and method from `[lns]` in
 * knowledge/importance.toml (served as `lns_title` / `lns_method`).
 */
import { CopySnippet } from './CopySnippet'
import { Md } from './Md'
import type { LnsHint } from '../types'

export function LnsHintBox({ hint, texts }: { hint: LnsHint; texts: Record<string, string> }) {
  return (
    <div className="pr-lns">
      <div className="pr-lns-title">{texts.lns_title ?? 'Give LNS more threads'}</div>
      <Md text={hint.text} />
      <div className="pr-snippet">
        <CopySnippet code={hint.snippet} />
      </div>
      {texts.lns_method && (
        <details className="pr-method">
          <summary>How sure is this?</summary>
          <Md text={texts.lns_method} />
        </details>
      )}
    </div>
  )
}
