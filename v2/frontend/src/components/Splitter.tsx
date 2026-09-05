/** Draggable divider between the two panes; sets the --left grid column. */
import { useCallback } from 'react'

export function Splitter() {
  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const main = (e.currentTarget.parentElement as HTMLElement) ?? document.body
    const move = (ev: PointerEvent) => {
      const rect = main.getBoundingClientRect()
      const frac = Math.min(0.8, Math.max(0.2, (ev.clientX - rect.left) / rect.width))
      main.style.setProperty('--left', `${(frac * 100).toFixed(1)}%`)
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
