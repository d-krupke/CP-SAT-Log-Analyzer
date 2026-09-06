import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev server proxies /api to the FastAPI backend (uv run uvicorn app.main:app --port 8000).
// `vite preview` serves the production build and needs the same proxy, because the
// screenshot pipeline (playwright.config.ts) photographs that build, not the dev server.
const backend = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': backend,
    },
  },
  preview: {
    proxy: {
      '/api': backend,
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
