/**
 * Plotly chart of the search progress: incumbent objective and proven bound
 * over time. Clicking a point selects the log line of that event.
 */
import { useMemo, useState } from 'react'
import Plotly from 'plotly.js-basic-dist-min'
import createPlotlyComponent from 'react-plotly.js/factory'
import type { ProgressSeries, SeriesPoint } from '../types'
import { useSelection } from '../state/selection'

const Plot = createPlotlyComponent(Plotly)

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function ProgressPlot({ progress }: { progress: ProgressSeries }) {
  const { select } = useSelection()
  const [logY, setLogY] = useState(false)
  const [focus, setFocus] = useState(true)
  const { data, layout } = useMemo(() => {
    const text = cssVar('--text')
    const muted = cssVar('--muted')
    const border = cssVar('--border')
    // Extend both step curves to the end of the search so the flat tail is visible.
    const end = progress.done_time ?? Math.max(...progress.solutions.map((p) => p.time), ...progress.bounds.map((p) => p.time))
    const extend = (pts: SeriesPoint[]): SeriesPoint[] =>
      pts.length > 0 && pts[pts.length - 1].time < end ? [...pts, { ...pts[pts.length - 1], time: end }] : pts
    const sols = extend(progress.solutions)
    const bounds = extend(progress.bounds)
    const boundName = progress.objective_sense === 'maximize' ? 'Upper bound' : 'Lower bound'
    const data: Plotly.Data[] = [
      {
        x: sols.map((p) => p.time),
        y: sols.map((p) => p.value),
        customdata: sols.map((p) => p.line),
        text: sols.map((p) => p.subsolver ?? ''),
        hovertemplate: 'objective %{y}<br>%{x:.2f}s · %{text}<br>line %{customdata}<extra></extra>',
        mode: 'lines+markers',
        line: { shape: 'hv', color: cssVar('--k-search') },
        marker: { size: 6 },
        name: 'Best solution',
        type: 'scatter',
      },
      {
        x: bounds.map((p) => p.time),
        y: bounds.map((p) => p.value),
        customdata: bounds.map((p) => p.line),
        text: bounds.map((p) => p.subsolver ?? ''),
        hovertemplate: 'bound %{y}<br>%{x:.2f}s · %{text}<br>line %{customdata}<extra></extra>',
        mode: 'lines+markers',
        line: { shape: 'hv', color: cssVar('--k-response'), dash: 'dot' },
        marker: { size: 5 },
        name: boundName,
        type: 'scatter',
      },
    ]
    const layout: Partial<Plotly.Layout> = {
      height: 300,
      margin: { l: 60, r: 10, t: 10, b: 40 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: text, size: 12 },
      xaxis: { title: { text: 'time [s]' }, gridcolor: border, zerolinecolor: border, color: muted },
      yaxis: {
        title: { text: 'objective' },
        gridcolor: border,
        zerolinecolor: border,
        color: muted,
        type: logY ? 'log' : 'linear',
        range: focusRange(sols.map((p) => p.value), bounds.map((p) => p.value), focus, logY),
      },
      legend: { orientation: 'h', y: 1.1 },
      hovermode: 'closest',
      shapes: progress.done_time
        ? [{ type: 'line', x0: progress.done_time, x1: progress.done_time, y0: 0, y1: 1, yref: 'paper', line: { color: muted, dash: 'dash', width: 1 } }]
        : [],
    }
    return { data, layout }
  }, [progress, logY, focus])

  return (
    <>
      <div className="legend" style={{ marginBottom: 4 }}>
        <label>
          <input type="checkbox" checked={focus} onChange={(e) => setFocus(e.target.checked)} /> hide early outliers
        </label>
        <label>
          <input type="checkbox" checked={logY} onChange={(e) => setLogY(e.target.checked)} /> log scale
        </label>
      </div>
    <Plot
      data={data}
      layout={layout}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
      useResizeHandler
      onClick={(ev: Plotly.PlotMouseEvent) => {
        const line = ev.points[0]?.customdata
        if (typeof line === 'number') select(line, 'panel')
      }}
    />
    </>
  )
}

/**
 * Early solutions are often orders of magnitude worse than the final one and
 * would squash the interesting part of the plot. "Focus" clips the y-range to
 * the values seen after the objective got within 10x of its final value.
 */
function focusRange(sols: number[], bounds: number[], focus: boolean, logY: boolean): [number, number] | undefined {
  if (!focus || sols.length === 0) return undefined
  const final = sols[sols.length - 1]
  const keep = sols.filter((v) => Math.abs(v) <= 10 * Math.max(1, Math.abs(final)))
  const vals = [...keep, ...bounds].filter((v) => Number.isFinite(v) && (!logY || v > 0))
  if (vals.length < 2) return undefined
  let lo = Math.min(...vals)
  let hi = Math.max(...vals)
  if (logY) {
    lo = Math.log10(lo)
    hi = Math.log10(hi)
  }
  const pad = (hi - lo) * 0.08 || 1
  return [lo - pad, hi + pad]
}
