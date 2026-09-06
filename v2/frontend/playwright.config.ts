/*
  Playwright config for the README screenshot pipeline.

  Created 2026-09-06: the README described the UI in prose while the UI kept
  moving, so the pictures are generated instead of pasted. Booting the whole
  stack and tearing it down again is the point - a screenshot that cannot be
  produced from a clean checkout is a screenshot that has gone stale.

    1. backend  - `uv run uvicorn app.main:app` on :8010, straight out of
                  v2/backend with its bundled knowledge base and example logs.
                  No database, no seeding: the input is a committed log file, so
                  every run analyzes byte-identical data.
    2. frontend - a production `vite build` served by `vite preview` on :4173,
                  proxying /api to the backend (see vite.config.ts `preview`).

  `e2e/screenshots.spec.ts` drives the real UI and writes PNGs into
  ../../docs/screenshots/. Because it clicks real controls against real output,
  a broken view or a renamed card fails the run - it doubles as a smoke test.

  Run: `npx playwright install chromium` once, then `npm run screenshots`.
  The ports are above 8000/8080 on purpose so a running `docker compose up`
  does not collide with a capture.
*/

import { defineConfig, devices } from '@playwright/test'

const BACKEND_PORT = Number(process.env.SCREENSHOT_BACKEND_PORT ?? 8010)
const FRONTEND_PORT = Number(process.env.SCREENSHOT_FRONTEND_PORT ?? 4173)

// Which theme the screenshots show. The UI stores this in localStorage, so the
// spec writes it before the app boots; `light` reads better on GitHub's default.
process.env.SCREENSHOT_THEME = process.env.SCREENSHOT_THEME ?? 'light'

export default defineConfig({
  testDir: './e2e',
  // The output is compared by eye, not asserted pixel-wise: no retries and one
  // worker keep the images stable and the log readable.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
  },
  projects: [
    {
      name: 'chromium',
      // Spread the device first, THEN override - it carries its own 1280x720 @1x
      // viewport, so size and scale settings are dropped if they come before it.
      use: {
        ...devices['Desktop Chrome'],
        // 1600 wide at 1x: still well above the ~900 px GitHub renders a README
        // image at, and a quarter of the bytes of a retina capture - these PNGs
        // are committed and regenerated on every visible UI change.
        viewport: { width: 1600, height: 1000 },
        deviceScaleFactor: 1,
      },
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT} --log-level warning`,
      cwd: '../backend',
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health`,
      reuseExistingServer: false,
      // A cold `uv run` may still have to build the environment.
      timeout: 180_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      // `--host 127.0.0.1`: vite preview otherwise binds IPv6 localhost only, so
      // the 127.0.0.1 readiness probe (and baseURL) would be refused.
      command: `npm run build && npx vite preview --host 127.0.0.1 --port ${FRONTEND_PORT} --strictPort`,
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 180_000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: { VITE_PROXY_TARGET: `http://127.0.0.1:${BACKEND_PORT}` },
    },
  ],
})
