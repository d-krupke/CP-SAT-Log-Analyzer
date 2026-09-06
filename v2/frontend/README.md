# Frontend

React + TypeScript + Vite + Plotly UI of the analyzer. Two panes: the analysis on the left, the
raw log on the right, linked in both directions - clicking a value scrolls the log to the line
it came from, clicking a log line highlights what was derived from it.

```bash
npm install
npm run dev     # http://localhost:5173, /api proxied to http://localhost:8000
npm run build   # tsc -b && vite build  ->  dist/
npm run lint    # oxlint

npm run screenshots:install   # once: the Chromium build Playwright drives
npm run screenshots           # regenerate ../../docs/screenshots/*.png
```

The dev server needs the backend running (`uv run uvicorn app.main:app --port 8000` in
`../backend`); point it elsewhere with `VITE_PROXY_TARGET`. `?example=915_01` in the URL
deep-links a bundled example.

## Layout

| Path | What |
| --- | --- |
| `src/api.ts`, `src/types.ts` | the backend contract: fetch helpers and the mirrored response types |
| `src/knowledge.ts` | loads `/api/explanations` once and looks texts up by key |
| `src/state/selection.ts` | the shared selection (which line, which block) that links the two panes |
| `src/components/AnalysisPanel.tsx` | left pane: overview, insights, plot, subsolvers, parameters, per-block cards |
| `src/components/blocks/` | one component per log section, plus `TableBlock` for the statistics tables |
| `src/components/LogView.tsx` | right pane: the raw log, one anchored element per line |
| `src/components/Landing.tsx` | paste / upload / pick an example |
| `e2e/screenshots.spec.ts`, `playwright.config.ts` | the README screenshot capture, which doubles as an end-to-end smoke test ([development.md](../../docs/development.md#screenshots-for-the-readme)) |

Nothing about CP-SAT is hard-coded here: all texts come from the backend's knowledge base
([`../knowledge/README.md`](../knowledge/README.md)), so wording changes need no frontend
change. See [`../../docs/architecture.md`](../../docs/architecture.md) for the whole picture.
