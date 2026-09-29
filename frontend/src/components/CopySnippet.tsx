/**
 * A code block with a Copy button that briefly shows "Copied".
 *
 * Split out of FewerWorkers.tsx on 2026-09-28 when the LNS hint needed the same block.
 */
import { useState } from 'react'

export function CopySnippet({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    void navigator.clipboard?.writeText(code).then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <>
      <pre>{code}</pre>
      <button onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
    </>
  )
}
