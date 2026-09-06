/*
  README screenshot capture + smoke test. Created 2026-09-06.

  Photographs the analyzer at work into ../../docs/screenshots/ so that the
  README shows the current UI rather than one somebody remembered to update.
  It drives the real frontend against the real backend, so a view that throws,
  a card that got renamed or an example that stopped parsing fails the run.

  Determinism comes for free here: the input is a committed example log, the
  backend holds no state, and the theme is pinned before the app boots. There
  is no clock to freeze - every number in the picture comes out of the log file.

  To add a shot, add a test: `analyze()` opens an example through its deep link,
  `open()` expands a card by title, and either the page or a card locator is
  photographed. Keep the set small - every image is a promise that the UI still
  looks like that.
*/

import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test, type Locator, type Page } from '@playwright/test'

const SHOTS_DIR = fileURLToPath(new URL('../../docs/screenshots/', import.meta.url))
const THEME = process.env.SCREENSHOT_THEME ?? 'light'

const shot = (file: string) => path.join(SHOTS_DIR, file)

/** The card with this title, as a whole `<section>` - the unit the README shows. */
function card(page: Page, title: string): Locator {
  return page
    .locator('section.card')
    .filter({ has: page.locator('header h2', { hasText: title }) })
    .first()
}

/** Open a card by clicking its title bar, unless it is expanded already. */
async function open(page: Page, title: string): Promise<Locator> {
  const target = card(page, title)
  await expect(target).toBeVisible()
  if ((await target.locator('.body, .content').count()) === 0) {
    await target.locator('header').click()
  }
  await settle(page)
  return target
}

/** Wait for the data and for layout/animation to come to rest. */
async function settle(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(400)
}

/** Load an example through its deep link and wait until the analysis is on screen. */
async function analyze(page: Page, example: string): Promise<void> {
  await page.goto(`/?example=${example}`)
  await expect(card(page, 'Overview')).toBeVisible({ timeout: 30_000 })
  await settle(page)
}

test.beforeEach(async ({ page }) => {
  // The app reads the theme from localStorage on its first render; setting it
  // afterwards would photograph a flash of the other one.
  await page.addInitScript((theme) => {
    try {
      window.localStorage.setItem('theme', theme as string)
    } catch {
      /* ignore */
    }
  }, THEME)
})

test('landing page', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Or explore an example' })).toBeVisible()
  // The footer is `position: fixed`, which a full-page capture renders at the
  // *viewport* bottom - i.e. floating in the middle of a tall page. Hide it here;
  // the viewport-sized shots below show it where it really sits.
  await page.addStyleTag({ content: '.sitelinks { display: none !important; }' })
  await settle(page)
  await page.screenshot({ path: shot('01-landing.png'), fullPage: true, animations: 'disabled', caret: 'hide' })
})

test('overview and insights', async ({ page }) => {
  // A 60 s job-shop run with 219 solutions: tiles, a gap, and insights that fire.
  await analyze(page, '915_jobshop_8workers')
  await page.screenshot({ path: shot('02-overview.png'), animations: 'disabled', caret: 'hide' })
  await card(page, 'Overview').screenshot({ path: shot('03-insights.png'), animations: 'disabled' })
})

test('progress plot', async ({ page }) => {
  await analyze(page, '915_jobshop_8workers')
  const plot = await open(page, 'Progress over time')
  // Plotly draws asynchronously; the SVG is the proof that it finished.
  await expect(plot.locator('svg.main-svg').first()).toBeVisible({ timeout: 30_000 })
  await page.waitForTimeout(800)
  await plot.screenshot({ path: shot('04-progress.png'), animations: 'disabled' })
})

test('the analysis linked line by line to the log', async ({ page }) => {
  await analyze(page, '915_jobshop_8workers')
  const search = await open(page, 'Search')
  // The `L90-317` badge jumps the log pane to this section: the whole point of
  // the two-pane layout, and invisible in a screenshot that does not use it.
  await search.locator('.lines').click()
  await search.scrollIntoViewIfNeeded()
  await settle(page)
  await page.screenshot({ path: shot('05-search.png'), animations: 'disabled', caret: 'hide' })
})

test('overridden parameters', async ({ page }) => {
  // `use_lns_only` is an override worth a warning, so the card shows both halves.
  await analyze(page, '915_setcover_lns_only')
  const params = await open(page, 'Overridden parameters')
  await params.scrollIntoViewIfNeeded()
  await settle(page)
  await params.screenshot({ path: shot('06-parameters.png'), animations: 'disabled' })
})

test('solution hint', async ({ page }) => {
  // The hinted job-shop: CP-SAT started from the hint, which the card explains.
  await analyze(page, '915_jobshop_hinted')
  const hint = await open(page, 'Solution hint')
  await hint.scrollIntoViewIfNeeded()
  await settle(page)
  await hint.screenshot({ path: shot('07-hint.png'), animations: 'disabled' })
})
