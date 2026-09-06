/**
 * Draggable divider between the two panes. Horizontal on a wide screen (it sets
 * the --left grid column), vertical once the layout stacks (--top grid row); the
 * CSS decides which, through the --axis custom property on this element, so the
 * breakpoint lives in one place.
 */
import { useCallback } from 'react'

export function Splitter() {
  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const main = (el.parentElement as HTMLElement) ?? document.body
    const vertical = getComputedStyle(el).getPropertyValue('--axis').trim() === 'y'
    // Without capture a finger that slips off the 10px strip loses the drag.
    el.setPointerCapture(e.pointerId)
    const move = (ev: PointerEvent) => {
      const rect = main.getBoundingClientRect()
      const frac = vertical
        ? (ev.clientY - rect.top) / rect.height
        : (ev.clientX - rect.left) / rect.width
      const clamped = Math.min(0.8, Math.max(0.2, frac))
      main.style.setProperty(vertical ? '--top' : '--left', `${(clamped * 100).toFixed(1)}%`)
    }
    const up = () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }, [])
  return <div className="splitter" onPointerDown={onPointerDown} />
}
