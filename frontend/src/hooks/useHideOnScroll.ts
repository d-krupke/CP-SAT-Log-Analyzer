/**
 * Slide the top bar out of the way while the reader scrolls down, and bring it
 * back as soon as they scroll up.
 *
 * Created 2026-09 for the phone layout. There the bar wraps onto two rows and
 * held about a sixth of the screen at all times, with nothing below it but two
 * small panes. On a desktop the bar costs one row of a large window and should
 * stay put, so the hook only toggles a class: whether that class does anything
 * is decided in `index.css`, inside the same media query that stacks the panes.
 *
 * Nothing here goes through React state - a scroll must not re-render the log
 * view or the Plotly chart - so the class and the measured bar height are
 * written straight onto the elements.
 */
import { useEffect, type RefObject } from 'react'

/** Scrolling this far (CSS px) in one direction flips the bar. */
const THRESHOLD = 24
/** Below this scroll position the bar always stays: a short pane never hides it. */
const KEEP_UNTIL = 48

type Ref = RefObject<HTMLElement | null>

export function useHideOnScroll(root: Ref, bar: Ref, className = 'bar-hidden'): void {
  useEffect(() => {
    const rootEl = root.current
    const barEl = bar.current
    if (!rootEl || !barEl) return

    // How far up the bar has to move to disappear; the CSS reads it as --bar-h.
    const observer = new ResizeObserver(() => {
      rootEl.style.setProperty('--bar-h', `${Math.ceil(barEl.offsetHeight)}px`)
    })
    observer.observe(barEl)

    // Per scroll container: the analysis and the log pane scroll independently,
    // and a pane that has not moved must not cancel the other's direction.
    const seen = new WeakMap<EventTarget, { top: number; acc: number }>()
    const onScroll = (e: Event) => {
      const el = e.target
      if (!(el instanceof HTMLElement)) return
      const prev = seen.get(el) ?? { top: el.scrollTop, acc: 0 }
      const delta = el.scrollTop - prev.top
      // Reverse direction resets the run, so a small correction does not have to
      // undo a long scroll before the bar reacts.
      const acc = delta * prev.acc < 0 ? delta : prev.acc + delta
      seen.set(el, { top: el.scrollTop, acc })
      if (acc > THRESHOLD && el.scrollTop > KEEP_UNTIL) {
        rootEl.classList.add(className)
        seen.set(el, { top: el.scrollTop, acc: 0 })
      } else if (acc < -THRESHOLD || el.scrollTop <= 0) {
        rootEl.classList.remove(className)
        seen.set(el, { top: el.scrollTop, acc: 0 })
      }
    }
    // Capture phase: scroll events do not bubble, so a listener on the root only
    // sees the panes' scrolling on the way down.
    rootEl.addEventListener('scroll', onScroll, true)

    return () => {
      observer.disconnect()
      rootEl.removeEventListener('scroll', onScroll, true)
      rootEl.classList.remove(className)
    }
  }, [root, bar, className])
}
