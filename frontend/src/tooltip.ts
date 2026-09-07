/**
 * Text -> native `title` tooltip.
 *
 * The knowledge base is hand-edited TOML, so its longer texts are hard-wrapped
 * at ~90 columns for the editor. A browser tooltip honours those newlines and
 * then wraps again at its own width, which shreds the paragraph into a ragged
 * staircase. `tooltip()` undoes the editing wrap and keeps only the breaks that
 * mean something: blank lines between paragraphs and the start of a list item.
 *
 * Use it wherever a knowledge text reaches a `title=`; it is a no-op on the
 * one-liners and returns `undefined` when there is nothing to show, so the
 * attribute disappears instead of rendering an empty tooltip.
 */

/** A line that starts its own line for good: `- item`, `* item`, `1. item`. */
const LIST_ITEM = /^(?:[-*•]|\d+[.)])\s+/

function unwrap(paragraph: string): string {
  const lines: string[] = []
  for (const raw of paragraph.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    // A wrapped continuation joins its line; a new list item does not.
    if (lines.length === 0 || LIST_ITEM.test(line)) lines.push(line)
    else lines[lines.length - 1] += ' ' + line
  }
  return lines.join('\n')
}

/**
 * Join the given pieces into one tooltip, blank line between them, each
 * unwrapped. Empty pieces are dropped; an empty result becomes `undefined`.
 */
export function tooltip(...parts: (string | null | undefined)[]): string | undefined {
  const text = parts
    .filter((p): p is string => Boolean(p && p.trim()))
    .join('\n\n')
    .split(/\n[ \t]*\n/)
    .map(unwrap)
    .filter(Boolean)
    .join('\n\n')
  return text || undefined
}
